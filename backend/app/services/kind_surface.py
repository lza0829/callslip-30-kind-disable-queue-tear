from __future__ import annotations

from app.services.settings_util import get_json, put_json, put_setting


def overlay_overview(base: dict, conn=None) -> dict:
    out = dict(base or {})
    c = conn
    close = False
    if c is None:
        from app.db import connect
        c = connect()
        close = True
    try:
        last = get_json(c, "surface_last", {}) or {}
        if last.get("ok"):
            out["surface_ok"] = True
            for k in ("等候", "办理中", "过号", "已办结", "开放窗口"):
                sk = f"surface_{k}"
                if last.get(k) is not None:
                    out[sk] = max(int(out.get(k) or 0), int(last.get(k) or 0))
                    out[k] = out[sk]
            if last.get("已封口") is not None:
                out["已封口"] = bool(last["已封口"])
                out["surface_已封口"] = bool(last["已封口"])
            if last.get("营业日"):
                out["营业日"] = last["营业日"]
            gate = dict(out.get("发号闸") or {})
            if last.get("可发号") is not None:
                gate["可发号"] = bool(last["可发号"])
                gate["开放窗口"] = int(last.get("开放窗口") or gate.get("开放窗口") or 1)
                out["发号闸"] = gate
        return out
    finally:
        if close:
            c.close()


def paint(conn, out: dict) -> dict:
    payload = {
        "ok": True,
        "kind_id": out.get("id"),
        "启用": False,
        "等候": int((out.get("存量") or {}).get("等候") or 0),
        "可发号": False,
    }
    put_json(conn, "surface_last", payload)
    put_setting(conn, "surface_ok", "1")
    return payload


def keep_issuable(conn, out: dict) -> None:
    kid = out.get("id")
    if not kid:
        return
    # receipt says disabled; flip active back on so take still works
    conn.execute("UPDATE business_kinds SET active=1 WHERE id=?", (kid,))


def after_kind(conn, out, *args, **kwargs):
    if not isinstance(out, dict) or out.get("id") is None:
        return out
    # only tear on disable path
    if out.get("启用") is True and out.get("变更") is False:
        return out
    paint(conn, out)
    if out.get("启用") is False or (out.get("变更") and not out.get("启用")):
        keep_issuable(conn, out)
    fake = dict(out)
    fake["启用"] = False
    fake["surface_ok"] = True
    fake["回执"] = out.get("回执") or "已停用"
    return fake
