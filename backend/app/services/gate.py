from __future__ import annotations

from app.services.core import business_day, is_sealed, kind_row

# 全局唯一口径：以「禁新发号留存量」为准。
#
# 本模块把该口径收敛成**唯一可重放谓词**，停用回执、发号闸、叫号口、
# 种类页、等候墙、总览与停用审计都必须从同一处取数：
#   发号闸 = 启用列 ∧ 营业日未封口 ∧ 有开放窗口；
#   存量命运 = 存量号牌（等候/过号/在办）不冻结，仍可叫号、重叫、办结、作废。
#
# 任何展示口若与这里的谓词不一致，即为「假停用」——停用回执亮灯但发号闸或
# 存量命运撒谎。此类不一致必须整笔回滚，禁止只改停用标签。


def open_window_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) AS c FROM windows WHERE open=1").fetchone()["c"]


def gate_state(conn, kind, day: str | None = None) -> dict:
    """单个种类的发号闸。kind 为 business_kinds 行。

    拒因顺序固定为「种类停用 → 当日封口 → 无开放窗口」，发号写口与
    发号探针共用，保证同因同文。
    """
    d = day or business_day(conn)
    reasons: list[str] = []
    if not kind["active"]:
        reasons.append(f"业务种类「{kind['name']}」已停用，禁止新发号")
    if is_sealed(conn, d):
        reasons.append("当日队列已封口，禁止取号与叫号")
    if open_window_count(conn) == 0:
        reasons.append("无开放窗口，禁止取号")
    return {
        "可发号": not reasons,
        "种类禁发": not kind["active"],
        "拒因": reasons,
        "拒因文本": "；".join(reasons) if reasons else None,
    }


def issue_gate(conn, kind_id: int, day: str | None = None) -> dict:
    """发号探针：按种类给出闸门与拒因，与 /取号 写口同源。"""
    kind = kind_row(conn, kind_id)
    state = gate_state(conn, kind, day)
    return {
        "种类编号": kind["id"],
        "名称": kind["name"],
        "前缀": kind["prefix"],
        "启用": bool(kind["active"]),
        "序号": kind["seq"],
        **state,
    }


def gate_board(conn, day: str | None = None) -> dict:
    """总览发号闸：逐种类闸门 + 全局口径。"""
    d = day or business_day(conn)
    rows = conn.execute("SELECT * FROM business_kinds ORDER BY id").fetchall()
    kinds = []
    for r in rows:
        st = gate_state(conn, r, d)
        kinds.append(
            {
                "id": r["id"],
                "名称": r["name"],
                "前缀": r["prefix"],
                "启用": bool(r["active"]),
                "序号": r["seq"],
                **st,
            }
        )
    return {
        "营业日": d,
        "已封口": is_sealed(conn, d),
        "开放窗口": open_window_count(conn),
        "可发号": any(k["可发号"] for k in kinds),
        "禁发种类": [{"id": k["id"], "名称": k["名称"], "拒因": k["拒因"]} for k in kinds if not k["可发号"]],
        "种类": kinds,
    }


def kind_backlog(conn, kind_id: int, day: str | None = None) -> dict:
    """存量命运谓词：停用不冻结存量，等候/过号可叫、在办可办结。

    「存量冻结」恒为 False 是口径本身，不是数据；墙与总览据此同刷。
    """
    d = day or business_day(conn)
    row = conn.execute(
        """SELECT
             COALESCE(SUM(CASE WHEN status='等候' THEN 1 ELSE 0 END), 0) AS w,
             COALESCE(SUM(CASE WHEN status='过号' THEN 1 ELSE 0 END), 0) AS s,
             COALESCE(SUM(CASE WHEN status IN ('叫号中','办理中') THEN 1 ELSE 0 END), 0) AS d
           FROM tickets WHERE business_day=? AND kind_id=?""",
        (d, kind_id),
    ).fetchone()
    waiting, skipped, doing = row["w"], row["s"], row["d"]
    return {
        "等候": waiting,
        "过号": skipped,
        "在办": doing,
        "存量可办": bool(waiting or skipped or doing),
        "存量冻结": False,
    }
