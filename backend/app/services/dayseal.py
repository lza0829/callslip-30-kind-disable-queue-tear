from __future__ import annotations
from datetime import date, timedelta
from fastapi import HTTPException
from app.services.core import business_day, is_sealed, now
from app.services import gate


def get_seal(conn) -> dict:
    day = business_day(conn)
    row = conn.execute(
        "SELECT * FROM day_seals WHERE business_day=?", (day,)
    ).fetchone()
    open_count = conn.execute(
        """SELECT COUNT(*) AS c FROM tickets
           WHERE business_day=? AND status IN ('等候','叫号中','办理中','过号')""",
        (day,),
    ).fetchone()["c"]
    return {
        "营业日": day,
        "已封口": bool(row and row["sealed"]),
        "封口时刻": row["sealed_at"] if row else None,
        "备注": row["note"] if row else "",
        "未结号数": open_count,
    }


def seal_day(conn, force: bool = False) -> dict:
    day = business_day(conn)
    if is_sealed(conn, day):
        raise HTTPException(400, detail="当日已封口")
    open_count = conn.execute(
        """SELECT COUNT(*) AS c FROM tickets
           WHERE business_day=? AND status IN ('等候','叫号中','办理中','过号')""",
        (day,),
    ).fetchone()["c"]
    if open_count and not force:
        raise HTTPException(400, detail=f"仍有{open_count}个未结号，须强制封口或先清队")
    note = "强制封口" if force and open_count else "正常封口"
    ts = now()
    exists = conn.execute(
        "SELECT id FROM day_seals WHERE business_day=?", (day,)
    ).fetchone()
    if exists:
        conn.execute(
            "UPDATE day_seals SET sealed=1, sealed_at=?, note=? WHERE business_day=?",
            (ts, note, day),
        )
    else:
        conn.execute(
            "INSERT INTO day_seals(business_day, sealed, sealed_at, note) VALUES (?,?,?,?)",
            (day, 1, ts, note),
        )
    return get_seal(conn)


def unseal_day(conn) -> dict:
    day = business_day(conn)
    if not is_sealed(conn, day):
        raise HTTPException(400, detail="当日未封口")
    conn.execute(
        "UPDATE day_seals SET sealed=0, sealed_at=NULL, note=? WHERE business_day=?",
        ("已解封", day),
    )
    return get_seal(conn)


def roll_day(conn, target: str | None = None) -> dict:
    cur = business_day(conn)
    if not is_sealed(conn, cur):
        raise HTTPException(400, detail="须先封口当日队列再切日")
    nxt = target or (date.fromisoformat(cur) + timedelta(days=1)).isoformat()
    if nxt <= cur:
        raise HTTPException(400, detail="新营业日须晚于当前营业日")
    conn.execute(
        "INSERT INTO settings(key, value) VALUES ('营业日', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (nxt,),
    )
    exists = conn.execute(
        "SELECT id FROM day_seals WHERE business_day=?", (nxt,)
    ).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO day_seals(business_day, sealed, sealed_at, note) VALUES (?,0,NULL,?)",
            (nxt, "新营业日"),
        )
    # 清空窗口当前号引用（跨日）
    conn.execute("UPDATE windows SET current_ticket_id=NULL")
    # 重置各类序号
    conn.execute("UPDATE business_kinds SET seq=0")
    return {
        "原营业日": cur,
        "营业日": nxt,
        "封口": get_seal(conn),
    }


def overview(conn) -> dict:
    day = business_day(conn)
    def cnt(status: str) -> int:
        return conn.execute(
            "SELECT COUNT(*) AS c FROM tickets WHERE business_day=? AND status=?",
            (day, status),
        ).fetchone()["c"]

    wins = conn.execute(
        "SELECT id, name, open, current_ticket_id FROM windows ORDER BY id"
    ).fetchall()
    # 种类等候桶：与等候墙、种类页、停用回执同源（gate）——
    # 停用种类存量仍计入、不随启停吞掉；可发号/拒因/存量冻结逐桶同刷。
    kind_rows = conn.execute(
        "SELECT * FROM business_kinds ORDER BY id"
    ).fetchall()
    buckets = []
    for k in kind_rows:
        w = conn.execute(
            "SELECT COUNT(*) AS c FROM tickets WHERE business_day=? AND kind_id=? AND status='等候'",
            (day, k["id"]),
        ).fetchone()["c"]
        s = conn.execute(
            "SELECT COUNT(*) AS c FROM tickets WHERE business_day=? AND kind_id=? AND status='过号'",
            (day, k["id"]),
        ).fetchone()["c"]
        state = gate.gate_state(conn, k, day)
        backlog = gate.kind_backlog(conn, k["id"], day)
        buckets.append(
            {
                "id": k["id"],
                "名称": k["name"],
                "前缀": k["prefix"],
                "启用": bool(k["active"]),
                "可发号": state["可发号"],
                "拒因": state["拒因"],
                "存量可办": backlog["存量可办"],
                "存量冻结": backlog["存量冻结"],
                "等候": w,
                "过号": s,
            }
        )
    return {
        "营业日": day,
        "已封口": is_sealed(conn, day),
        "等候": cnt("等候"),
        "叫号中": cnt("叫号中"),
        "办理中": cnt("办理中"),
        "过号": cnt("过号"),
        "已办结": cnt("已办结"),
        "已作废": cnt("已作废"),
        "开放窗口": sum(1 for w in wins if w["open"]),
        "发号闸": gate.gate_board(conn, day),
        "种类桶": buckets,
        "窗口": [
            {
                "id": w["id"],
                "名称": w["name"],
                "开放": bool(w["open"]),
                "有在办": bool(w["current_ticket_id"]),
            }
            for w in wins
        ],
    }

