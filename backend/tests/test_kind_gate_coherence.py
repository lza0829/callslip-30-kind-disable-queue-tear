"""假停用收口 · 撕裂回归验证（口径：禁新发号留存量）。

运行：cd backend && python tests/test_kind_gate_coherence.py
覆盖用户夹具：
  A. 停用绿仍能发号：停用回执亮「已停用」后 /取号 必须被拒，且发号闸同报禁发；
  B. 存量误冻不能办结：停用后存量等候/在办仍可叫号、办结，存量冻结恒 False；
  C. 启用列关闸未拒：启用列关（active=0）时发号闸必须拒，探针/总览/种类页同文；
  D. 停用发号半截：并发停用与发号后，游标、实发、启停终态、事件四方对齐。
并验证：停用回执 / 发号探针 / 叫号口 / 种类页 / 等候墙 / 总览 / 停用审计 / 事件流水
        八面同刷；旁路改启用字不再能伪造「已停用」回执。
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
    return client.get("/api/业务种类").json()


def kind(kid: int) -> dict:
    return next(k for k in kinds() if k["id"] == kid)


def wall_block(name: str) -> dict:
    return next(b for b in client.get("/api/等候墙").json()["墙面"] if b["业务种类"] == name)


def bucket(name: str) -> dict:
    return next(b for b in client.get("/api/总览").json()["种类桶"] if b["名称"] == name)


def audit_kind(name: str) -> dict:
    return next(k for k in client.get("/api/业务种类/停用审计").json()["种类"] if k["名称"] == name)


def ticket_id_by_slip(slip: str) -> int:
    return next(t["id"] for t in client.get("/api/号牌").json() if t["号牌"] == slip)


# ---------------- A. 停用绿仍能发号（假停用必须收口） ----------------
r = client.post("/api/业务种类/1/启停", json={"启用": False})
check("A 停用回执亮已停用", r.status_code == 200 and r.json()["启用"] is False, r.text)
check("A 回执自证发号闸禁发", r.json()["发号闸"]["可发号"] is False, str(r.json()["发号闸"]))

# 核心夹具：回执成功后立刻发号，必须被拒——旁路（把 active 翻回 1）已拆除
r = client.post("/api/取号", json={"种类编号": 1})
check("A 停用绿后新发号必拒", r.status_code == 400 and "已停用" in r.json()["detail"], r.text)
check("A 启用列保持停用（未被翻回）", kind(1)["启用"] is False, str(kind(1)))
check("A 游标冻结不推进", kind(1)["序号"] == 3, str(kind(1)["序号"]))

# 发号探针与写口同源
probe = client.get("/api/业务种类/1/发号闸").json()
check("A 探针报禁发且同文", probe["可发号"] is False
      and probe["拒因文本"] == "业务种类「个人储蓄」已停用，禁止新发号", str(probe))
check("A 探针种类启停标记", probe["启用"] is False)

# ---------------- B. 存量误冻不能办结（存量可办，恒不冻结） ----------------
check("B 种类页存量不冻结", kind(1)["存量冻结"] is False and kind(1)["存量可办"] is True)
check("B 墙存量不冻结", wall_block("个人储蓄")["存量冻结"] is False)
check("B 总览桶存量不冻结", bucket("个人储蓄")["存量冻结"] is False)
check("B 审计存量同态", audit_kind("个人储蓄")["存量冻结"] is False
      and audit_kind("个人储蓄")["存量同态"] is True)

r = client.post("/api/叫号", json={"窗口编号": 3, "种类编号": 1})
check("B 停用种类存量可叫", r.status_code == 200 and r.json()["号牌"] == "储001", r.text)
check("B 叫号回执带停用标记", r.json()["种类启用"] is False)
t1 = r.json()["id"]
r = client.post(f"/api/号牌/{t1}/办结")
check("B 存量可办结（不误冻）", r.status_code == 200 and r.json()["状态"] == "已办结")

r = client.post(f"/api/号牌/{ticket_id_by_slip('储003')}/办结")
check("B 停用前在办可办结", r.status_code == 200 and r.json()["状态"] == "已办结")

# ---------------- C. 启用列关闸未拒（启用列→闸必须一致） ----------------
# 端正方向：把对公结算停用，启用列=0，发号闸必须拒且探针/种类页/总览/墙同文
r = client.post("/api/业务种类/2/启停", json={"启用": False})
check("C 停用回执", r.status_code == 200 and r.json()["启用"] is False)
check("C 种类页发号闸一致", kind(2)["可发号"] is False and kind(2)["启用"] is False)
check("C 总览闸一致", client.get("/api/业务种类/发号闸").json()["种类"][1]["可发号"] is False)
check("C 墙闸一致", wall_block("对公结算")["可发号"] is False)
check("C 探针一致", client.get("/api/业务种类/2/发号闸").json()["可发号"] is False)
r = client.post("/api/取号", json={"种类编号": 2})
check("C 启用列关则发号必拒", r.status_code == 400 and "已停用" in r.json()["detail"], r.text)

# ---------------- 八面同刷一致性 + 停用审计 ----------------
aud = client.get("/api/业务种类/停用审计").json()
check("审计整体一致", aud["一致"] is True, str(aud))
for nm in ("个人储蓄", "对公结算", "理财咨询"):
    a = audit_kind(nm)
    check(f"审计 {nm} 灯/闸/存量/重放四线同态", a["一致"] is True, str(a))

# 总览发号闸：逐种类可发号方向与启用列互补
gate_board = client.get("/api/业务种类/发号闸").json()
for k in kinds():
    gk = next(g for g in gate_board["种类"] if g["id"] == k["id"])
    check(f"发号闸板 {k['名称']} 与种类页同向", gk["可发号"] == k["可发号"])

# 事件流水带结局，可重放
evs = client.get("/api/业务种类/流水").json()
check("流水带结局字段", all("启用" in e for e in evs))
derived: dict[str, bool] = {}
for e in sorted(evs, key=lambda x: x["id"]):
    derived[e["种类"]] = bool(e["启用"])
check("事件重放==当前启停", all(kind(k["id"])["启用"] == derived[k["名称"]]
                                for k in kinds() if k["名称"] in derived))

# ---------------- D. 停用发号半截（重启用后并发，收敛） ----------------
client.post("/api/业务种类/2/启停", json={"启用": True})
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
check("D 并发发号拒因均为已停用", all("已停用" in d for _, d in errs), str(errs))
check("D 并发结果无丢失", oks + len(errs) == N_TAKE)
with db() as conn:
    krow = conn.execute("SELECT seq, active FROM business_kinds WHERE id=2").fetchone()
    cnt = conn.execute(
        "SELECT COUNT(*) AS c FROM tickets WHERE kind_id=2 AND business_day=?",
        (client.get("/api/总览").json()["营业日"],),
    ).fetchone()["c"]
check("D 游标与实发一致无半截", krow["seq"] == 1 + oks and cnt == 1 + oks,
      f"seq={krow['seq']} oks={oks} cnt={cnt}")
check("D 并发后种类终态停用", krow["active"] == 0)
r = client.post("/api/取号", json={"种类编号": 2})
check("D 停用落定后新发号必拒", r.status_code == 400 and "已停用" in r.json()["detail"])
check("D 半截后审计仍一致", client.get("/api/业务种类/停用审计").json()["一致"] is True)

print(f"\n全部 {_checks} 项检查通过")
os.unlink(_db_path)
