from __future__ import annotations
from fastapi import HTTPException
from app.services.core import parse_kind_ids, ticket_dict, ticket_row, window_row


def list_windows(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM windows ORDER BY id").fetchall()
    out = []
    for r in rows:
        kids = parse_kind_ids(r["kind_ids"])
        kinds = []
        for kid in kids:
            k = conn.execute(
                "SELECT id, name, prefix FROM business_kinds WHERE id=?", (kid,)
            ).fetchone()
            if k:
                kinds.append({"id": k["id"], "名称": k["name"], "前缀": k["prefix"]})
        cur = None
        if r["current_ticket_id"]:
            cur = ticket_dict(conn, ticket_row(conn, r["current_ticket_id"]))
        out.append(
            {
                "id": r["id"],
                "名称": r["name"],
                "开放": bool(r["open"]),
                "可办种类": kinds,
                "当前号": cur,
            }
        )
    return out


def set_open(conn, window_id: int, open_: bool) -> dict:
    win = window_row(conn, window_id)
    if not open_ and win["current_ticket_id"]:
        raise HTTPException(400, detail="窗口仍有在办号，不可关闭")
    conn.execute("UPDATE windows SET open=? WHERE id=?", (1 if open_ else 0, window_id))
    return next(w for w in list_windows(conn) if w["id"] == window_id)
