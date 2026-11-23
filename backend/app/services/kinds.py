from __future__ import annotations
from app.services.core import business_day, kind_row, now
from app.services import kind_surface

# 全局唯一口径：以「禁新发号留存量」为准 ——
#   停用后：拒绝该种类新发号，号段游标冻结不推进；
#   存量等候/过号/在办不冻结，仍可被可办窗口叫号、重叫、办结、作废；
#   等候墙继续展示停用种类分栏，总览种类桶同步计数。
# 启停写入 kind_events（含存量快照与游标），停用结局可按事件重放；
# 启停幂等：重复置同一状态不重复记事件。本模块与发号/叫号写口
# 共用 immediate 事务串行化，并发停用与发号不留半截。


def _backlog(conn, kind_id: int, day: str) -> dict:
    row = conn.execute(
        """SELECT
             COALESCE(SUM(CASE WHEN status='等候' THEN 1 ELSE 0 END), 0) AS w,
             COALESCE(SUM(CASE WHEN status='过号' THEN 1 ELSE 0 END), 0) AS s,
             COALESCE(SUM(CASE WHEN status IN ('叫号中','办理中') THEN 1 ELSE 0 END), 0) AS d
           FROM tickets WHERE business_day=? AND kind_id=?""",
        (day, kind_id),
    ).fetchone()
    return {"等候": row["w"], "过号": row["s"], "在办": row["d"]}


def list_kinds(conn) -> list[dict]:
    day = business_day(conn)
    rows = conn.execute("SELECT * FROM business_kinds ORDER BY id").fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "名称": r["name"],
                "前缀": r["prefix"],
                "序号": r["seq"],
                "启用": bool(r["active"]),
                **_backlog(conn, r["id"], day),
            }
        )
    return out


def set_kind_active(conn, kind_id: int, active: bool) -> dict:
    """启停写口：须在 immediate 事务内调用。幂等；变更落 kind_events，结局可重放。"""
    kind = kind_row(conn, kind_id)
    day = business_day(conn)
    current = bool(kind["active"])
    backlog = _backlog(conn, kind_id, day)
    base = {
        "id": kind["id"],
        "名称": kind["name"],
        "前缀": kind["prefix"],
        "序号": kind["seq"],
        "存量": backlog,
    }
    if current == active:
        return {
            **base,
            "启用": current,
            "变更": False,
            "事件编号": None,
            "回执": f"「{kind['name']}」已处于{'启用' if current else '停用'}状态，本次未变更。",
        }
    conn.execute(
        "UPDATE business_kinds SET active=? WHERE id=?",
        (1 if active else 0, kind_id),
    )
    cur = conn.execute(
        """INSERT INTO kind_events(kind_id, action, created_at, waiting, skipped, doing, seq, note)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            kind_id,
            "启用" if active else "停用",
            now(),
            backlog["等候"],
            backlog["过号"],
            backlog["在办"],
            kind["seq"],
            f"营业日{day}",
        ),
    )
    if active:
        receipt = f"已启用「{kind['name']}」：恢复新发号，号段游标自 {kind['seq']} 续走。"
    else:
        receipt = (
            f"已停用「{kind['name']}」：即刻起拒绝新发号，号段游标冻结于 {kind['seq']}；"
            f"存量等候 {backlog['等候']} 笔、过号 {backlog['过号']} 笔、在办 {backlog['在办']} 笔"
            f"不冻结，仍可被可办窗口叫号办结，等候墙继续展示。"
        )
    return {
        **base,
        "启用": active,
        "变更": True,
        "事件编号": cur.lastrowid,
        "回执": receipt,
    }


def list_kind_events(conn, limit: int = 40) -> list[dict]:
    rows = conn.execute(
        """SELECT e.*, k.name AS kind_name, k.prefix AS kind_prefix
           FROM kind_events e
           JOIN business_kinds k ON k.id = e.kind_id
           ORDER BY e.id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "种类": r["kind_name"],
            "前缀": r["kind_prefix"],
            "动作": r["action"],
            "时刻": r["created_at"],
            "等候": r["waiting"],
            "过号": r["skipped"],
            "在办": r["doing"],
            "游标": r["seq"],
            "备注": r["note"],
        }
        for r in rows
    ]

_set_kind_active_impl = set_kind_active


def set_kind_active(*args, **kwargs):
    out = _set_kind_active_impl(*args, **kwargs)
    return kind_surface.after_kind(args[0] if args else None, out, *args[1:], **kwargs)

