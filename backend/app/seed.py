from __future__ import annotations
from datetime import date
from app.db import db, init_db


def seed_if_empty() -> None:
    init_db()
    with db() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM business_kinds").fetchone()["c"]
        if n:
            return
        today = date.today().isoformat()
        kinds = [
            ("个人储蓄", "储"),
            ("对公结算", "对"),
            ("理财咨询", "理"),
        ]
        kind_ids = []
        for name, prefix in kinds:
            cur = conn.execute(
                "INSERT INTO business_kinds(name, prefix, seq, active) VALUES (?,?,0,1)",
                (name, prefix),
            )
            kind_ids.append(cur.lastrowid)
        windows = [
            ("一号窗", f"{kind_ids[0]},{kind_ids[2]}"),
            ("二号窗", f"{kind_ids[1]},{kind_ids[0]}"),
            ("三号窗", f"{kind_ids[0]},{kind_ids[1]},{kind_ids[2]}"),
        ]
        for name, kids in windows:
            conn.execute(
                "INSERT INTO windows(name, kind_ids, open, current_ticket_id) VALUES (?,?,1,NULL)",
                (name, kids),
            )
        samples = [
            (kind_ids[0], "储001", 1, "等候", None),
            (kind_ids[0], "储002", 2, "等候", None),
            (kind_ids[1], "对001", 1, "等候", None),
            (kind_ids[2], "理001", 1, "等候", None),
            (kind_ids[0], "储003", 3, "办理中", 1),
        ]
        for kid, slip, pos, status, wid in samples:
            conn.execute(
                """INSERT INTO tickets(slip_no, kind_id, business_day, status, window_id, queue_pos, taken_at, called_at, note)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    slip,
                    kid,
                    today,
                    status,
                    wid,
                    pos,
                    f"{today}T09:05:00",
                    f"{today}T09:20:00" if status == "办理中" else None,
                    "种子号",
                ),
            )
            if status == "办理中":
                tid = conn.execute("SELECT id FROM tickets WHERE slip_no=?", (slip,)).fetchone()["id"]
                conn.execute("UPDATE windows SET current_ticket_id=? WHERE id=1", (tid,))
        for kid, prefix in ((kind_ids[0], "储"), (kind_ids[1], "对"), (kind_ids[2], "理")):
            mx = conn.execute(
                "SELECT COUNT(*) AS c FROM tickets WHERE kind_id=? AND business_day=?",
                (kid, today),
            ).fetchone()["c"]
            conn.execute("UPDATE business_kinds SET seq=? WHERE id=?", (mx, kid))
        conn.execute("INSERT INTO settings(key, value) VALUES ('营业日', ?)", (today,))
        conn.execute(
            "INSERT INTO day_seals(business_day, sealed, sealed_at, note) VALUES (?,0,NULL,?)",
            (today, "当日未封口"),
        )
