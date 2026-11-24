from __future__ import annotations
from app.services.core import business_day, kind_row, now
from app.services import gate

# 全局唯一口径：以「禁新发号留存量」为准 ——
#   停用后：拒绝该种类新发号，号段游标冻结不推进；
#   存量等候/过号/在办不冻结，仍可被可办窗口叫号、重叫、办结、作废；
#   等候墙继续展示停用种类分栏，总览种类桶同步计数。
# 启停写入 kind_events（含存量快照与游标），停用结局可按事件重放；
# 启停幂等：重复置同一状态不重复记事件。本模块与发号/叫号写口
# 共用 immediate 事务串行化，并发停用与发号不留半截。
#
# 启停回执与发号闸、存量命运谓词同源于 app.services.gate：
# 回执亮「已停用」必须以「新发号被拒」且「存量未冻结」同时成立为凭，
# 二者若不一致整笔回滚（事务抛错，不落半截），禁止只改停用标签。


def _backlog(conn, kind_id: int, day: str) -> dict:
    return gate.kind_backlog(conn, kind_id, day)


def list_kinds(conn) -> list[dict]:
    day = business_day(conn)
    rows = conn.execute("SELECT * FROM business_kinds ORDER BY id").fetchall()
    out = []
    for r in rows:
        state = gate.gate_state(conn, r, day)
        out.append(
            {
                "id": r["id"],
                "名称": r["name"],
                "前缀": r["prefix"],
                "序号": r["seq"],
                "启用": bool(r["active"]),
                "可发号": state["可发号"],
                "拒因": state["拒因"],
                **_backlog(conn, r["id"], day),
            }
        )
    return out


def _verify_after_write(conn, kind_id: int, active: bool, day: str) -> dict:
    """写后自证：停用灯、发号闸、存量命运必须同命运，否则抛错整笔回滚。

    只比对**种类启停本身**这一因（种类禁发），环境性闸门（封口/无开放窗口）
    不参与，避免启用仍被环境闸拦时误判为「假启用」。
    """
    kind = kind_row(conn, kind_id)
    state = gate.gate_state(conn, kind, day)
    backlog = gate.kind_backlog(conn, kind_id, day)
    if bool(kind["active"]) != active:
        raise RuntimeError("启停未落定：启用列与请求不一致")
    if state["种类禁发"] == bool(active):
        raise RuntimeError("假停用/假启用：停用灯与发号闸对种类的放行相反")
    if backlog["存量冻结"]:
        raise RuntimeError("假停用：存量被冻结，违反「存量可办」口径")
    return backlog


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
        "存量": {k: backlog[k] for k in ("等候", "过号", "在办")},
        "存量可办": backlog["存量可办"],
        "存量冻结": backlog["存量冻结"],
    }
    if current == active:
        state = gate.gate_state(conn, kind, day)
        return {
            **base,
            "启用": current,
            "变更": False,
            "事件编号": None,
            "发号闸": state,
            "回执": f"「{kind['name']}」已处于{'启用' if current else '停用'}状态，本次未变更。",
        }
    conn.execute(
        "UPDATE business_kinds SET active=? WHERE id=?",
        (1 if active else 0, kind_id),
    )
    cur = conn.execute(
        """INSERT INTO kind_events(kind_id, action, created_at, waiting, skipped, doing, seq, active, note)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            kind_id,
            "启用" if active else "停用",
            now(),
            backlog["等候"],
            backlog["过号"],
            backlog["在办"],
            kind["seq"],
            1 if active else 0,
            f"营业日{day}",
        ),
    )
    _verify_after_write(conn, kind_id, active, day)
    state = gate.gate_state(conn, kind_row(conn, kind_id), day)
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
        "发号闸": state,
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
            "启用": bool(r["active"]),
            "备注": r["note"],
        }
        for r in rows
    ]


def audit(conn) -> dict:
    """停用审计：种类启用列、发号闸、存量命运、事件重放四者必须同态。

    任一「启用灯 / 发号闸 / 存量冻结 / 事件重放」四线不一致即判撕裂，
    给出证据；本审计只读不改，用于验证停用成功后各面未撒谎。
    """
    day = business_day(conn)
    rows = conn.execute("SELECT * FROM business_kinds ORDER BY id").fetchall()
    derived: dict[int, bool] = {}
    for e in conn.execute("SELECT kind_id, action FROM kind_events ORDER BY id").fetchall():
        derived[e["kind_id"]] = e["action"] == "启用"
    items = []
    ok = True
    for r in rows:
        state = gate.gate_state(conn, r, day)
        backlog = gate.kind_backlog(conn, r["id"], day)
        active = bool(r["active"])
        # 发号闸对「种类」这一因的放行方向须与启用列相反：停用⇒禁发，启用⇒不禁发
        gate_agrees = state["种类禁发"] == (not active)
        fate_agrees = backlog["存量冻结"] is False
        replay_agrees = derived.get(r["id"], active) == active
        coherent = gate_agrees and fate_agrees and replay_agrees
        ok = ok and coherent
        items.append(
            {
                "id": r["id"],
                "名称": r["name"],
                "启用灯": active,
                "发号闸": "禁发" if state["种类禁发"] else "放行",
                "可发号": state["可发号"],
                "拒因": state["拒因"],
                "存量可办": backlog["存量可办"],
                "存量冻结": backlog["存量冻结"],
                "事件重放": derived.get(r["id"], active),
                "闸同态": gate_agrees,
                "存量同态": fate_agrees,
                "重放同态": replay_agrees,
                "一致": coherent,
            }
        )
    return {"营业日": day, "一致": ok, "种类": items}
