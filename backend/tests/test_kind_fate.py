"""种类停用与队列命运 · 闭合验证（口径：禁新发号留存量）。

运行：cd backend && CALLSLIP_DB=<临时库> python tests/test_kind_fate.py
覆盖：
  1. 停用回执（含事件编号、存量快照、游标）
  2. 停用后新发号被拒 + 号段游标冻结
  3. 等候墙分栏不撤、存量不吞（灰显标记）
  4. 总览种类等候桶与墙同口径
  5. 存量可叫、可办结、可过号、可重叫、可作废（不冻结）
  6. 启停事件可重放：折叠事件 == 当前启停状态
  7. 启停幂等：重复停用不增事件
  8. 重新启用后游标续走不重置
  9. 并发停用与发号不留半截：游标与实发一致，停用落定后必拒
"""
from __future__ import annotations
import os
import sys
import tempfile
import threading

_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["CALLSLIP_DB"] = _db_path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import kinds as kind_svc  # noqa: E402
from app.services import tickets as tic  # noqa: E402

client = TestClient(app)
_checks = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global _checks
    assert cond, f"FAIL: {name} {extra}"
    _checks += 1
    print(f"ok {_checks:02d} - {name}")


def kinds() -> list[dict]:
    r = client.get("/api/业务种类")
    assert r.status_code == 200
    return r.json()


def kind(kid: int) -> dict:
    return next(k for k in kinds() if k["id"] == kid)


def ticket_id_by_slip(slip: str) -> int:
    return next(t["id"] for t in client.get("/api/号牌").json() if t["号牌"] == slip)


# 种子：1 个人储蓄(储,seq3,等候2,在办1) 2 对公结算(对,seq1,等候1) 3 理财咨询(理,seq1,等候1)
k1 = kind(1)
check("种类页同刷游标与存量", k1["启用"] is True and k1["序号"] == 3
      and k1["等候"] == 2 and k1["过号"] == 0 and k1["在办"] == 1, str(k1))

# 1. 停用回执
r = client.post("/api/业务种类/1/启停", json={"启用": False})
check("停用回执状态", r.status_code == 200)
rc = r.json()
check("回执变更与启停", rc["变更"] is True and rc["启用"] is False, str(rc))
check("回执含事件编号", isinstance(rc["事件编号"], int) and rc["事件编号"] >= 1)
check("回执存量快照", rc["存量"] == {"等候": 2, "过号": 0, "在办": 1}, str(rc["存量"]))
check("回执文本口径", "拒绝新发号" in rc["回执"] and "游标冻结" in rc["回执"], rc["回执"])

# 2. 停用后新发号被拒 + 游标冻结
r = client.post("/api/取号", json={"种类编号": 1})
check("停用后新发号被拒", r.status_code == 400 and "已停用" in r.json()["detail"], r.text)
check("游标冻结不推进", kind(1)["序号"] == 3)

# 3. 等候墙：分栏不撤、存量不吞、停用标记
wall = client.get("/api/等候墙").json()
block = next(b for b in wall["墙面"] if b["业务种类"] == "个人储蓄")
check("墙分栏保留且标记停用", block["启用"] is False)
check("墙存量不吞", block["等候数"] == 2 and len(block["队列"]) == 2, str(block["等候数"]))

# 4. 总览种类桶与墙同口径
ov = client.get("/api/总览").json()
bucket = next(b for b in ov["种类桶"] if b["名称"] == "个人储蓄")
check("总览种类桶同刷", bucket["启用"] is False and bucket["等候"] == 2 and bucket["过号"] == 0)

# 5. 存量命运：可叫、可办结、可过号、可重叫、可作废（不冻结）
r = client.post("/api/叫号", json={"窗口编号": 3, "种类编号": 1})
check("停用种类存量可叫", r.status_code == 200 and r.json()["号牌"] == "储001", r.text)
check("叫号回执带种类启停标记", r.json()["种类启用"] is False)
t1 = r.json()["id"]
r = client.post(f"/api/号牌/{t1}/办结")
check("存量可办结", r.status_code == 200 and r.json()["状态"] == "已办结")

r = client.post(f"/api/号牌/{ticket_id_by_slip('储003')}/办结")
check("在办不受停用影响可办结", r.status_code == 200 and r.json()["状态"] == "已办结")

r = client.post("/api/叫号", json={"窗口编号": 3, "种类编号": 1})
t2 = r.json()["id"]
check("存量第二笔可叫", r.status_code == 200 and r.json()["号牌"] == "储002")
r = client.post(f"/api/号牌/{t2}/过号")
check("存量可过号", r.status_code == 200 and r.json()["状态"] == "过号")
r = client.post(f"/api/号牌/{t2}/重叫", json={"窗口编号": 3})
check("过号可重叫", r.status_code == 200 and r.json()["状态"] == "办理中")
r = client.post(f"/api/号牌/{t2}/办结")
check("重叫后可办结", r.status_code == 200 and r.json()["状态"] == "已办结")

# 理财(id=3)：停用后存量等候可作废（审计出口之一）
client.post("/api/业务种类/3/启停", json={"启用": False})
r = client.post(f"/api/号牌/{ticket_id_by_slip('理001')}/作废")
check("停用种类存量可作废", r.status_code == 200 and r.json()["状态"] == "已作废")

# 号牌事件表联动：停用种类的叫号/办结/重叫均落流水
ev = client.get("/api/叫号流水").json()
acts = {(e["号牌"], e["动作"]) for e in ev}
check("号牌事件表记录停用种类命运",
      ("储001", "叫号") in acts and ("储001", "办结") in acts and ("储002", "重叫") in acts)

# 墙：存量清结后分栏仍在
wall = client.get("/api/等候墙").json()
block = next(b for b in wall["墙面"] if b["业务种类"] == "个人储蓄")
check("存量清结后分栏仍展示", block["启用"] is False and block["等候数"] == 0)

# 6. 启停事件可重放：折叠事件推导 == 当前状态
evs = client.get("/api/业务种类/流水").json()
mine = [e for e in evs if e["种类"] == "个人储蓄"]
check("停用事件落表含快照", len(mine) == 1 and mine[0]["动作"] == "停用"
      and mine[0]["等候"] == 2 and mine[0]["在办"] == 1 and mine[0]["游标"] == 3, str(mine))
derived: dict[str, bool] = {}
for e in sorted(evs, key=lambda x: x["id"]):
    derived[e["种类"]] = e["动作"] == "启用"
now_state = {k["名称"]: k["启用"] for k in kinds()}
check("事件重放==当前启停", all(now_state[n] == st for n, st in derived.items()))

# 7. 幂等：重复停用不增事件
n_events = len(evs)
r = client.post("/api/业务种类/1/启停", json={"启用": False})
check("重复停用幂等", r.status_code == 200 and r.json()["变更"] is False)
check("幂等不增事件", len(client.get("/api/业务种类/流水").json()) == n_events)

# 8. 重新启用：游标续走不重置
r = client.post("/api/业务种类/1/启停", json={"启用": True})
check("启用回执", r.json()["变更"] is True and "续走" in r.json()["回执"])
r = client.post("/api/取号", json={"种类编号": 1})
check("启用后恢复发号且游标续走", r.status_code == 200 and r.json()["号牌"] == "储004", r.text)

# 9. 并发停用与发号：不留半截（对公结算 id=2，seq=1，存量对001）
N_TAKE = 8
results: list = []


def t_take() -> None:
    try:
        with db(immediate=True) as conn:
            tic.take_ticket(conn, 2)
        results.append("ok")
    except HTTPException as e:
        results.append(("err", e.detail))


def t_disable() -> None:
    with db(immediate=True) as conn:
        kind_svc.set_kind_active(conn, 2, False)


threads = [threading.Thread(target=t_take) for _ in range(N_TAKE)]
threads.insert(3, threading.Thread(target=t_disable))
for t in threads:
    t.start()
for t in threads:
    t.join()

oks = results.count("ok")
errs = [r for r in results if r != "ok"]
check("并发发号拒因均为已停用", all("已停用" in d for _, d in errs), str(errs))
check("并发结果无丢失", oks + len(errs) == N_TAKE)
with db() as conn:
    krow = conn.execute("SELECT seq, active FROM business_kinds WHERE id=2").fetchone()
    cnt = conn.execute(
        "SELECT COUNT(*) AS c FROM tickets WHERE kind_id=2 AND business_day=?",
        (client.get("/api/总览").json()["营业日"],),
    ).fetchone()["c"]
check("游标与实发一致无半截", krow["seq"] == 1 + oks and cnt == 1 + oks,
      f"seq={krow['seq']} oks={oks} cnt={cnt}")
check("并发后种类终态停用", krow["active"] == 0)
r = client.post("/api/取号", json={"种类编号": 2})
check("停用落定后新发号必拒", r.status_code == 400 and "已停用" in r.json()["detail"])
evs2 = [e for e in client.get("/api/业务种类/流水").json() if e["种类"] == "对公结算"]
check("并发停用仅一条停用事件", len(evs2) == 1 and evs2[0]["动作"] == "停用")

print(f"\n全部 {_checks} 项检查通过")
os.unlink(_db_path)
