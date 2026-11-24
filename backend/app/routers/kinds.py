from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.db import db
from app.services import kinds as kind_svc
from app.services import gate as gate_svc

router = APIRouter(tags=["业务种类"])


class ActiveBody(BaseModel):
    启用: bool = Field(..., alias="启用")

    class Config:
        populate_by_name = True


@router.get("/业务种类")
def list_kinds():
    with db() as conn:
        return kind_svc.list_kinds(conn)


@router.get("/业务种类/发号闸")
def issue_gate_board():
    # 发号闸与 /取号 写口、停用回执同源：逐种类给出可发号与拒因
    with db() as conn:
        return gate_svc.gate_board(conn)


@router.get("/业务种类/{kind_id}/发号闸")
def issue_gate(kind_id: int):
    # 发号探针：不改状态，仅按与写口同源的谓词报告该种类能否发号及拒因
    with db() as conn:
        return gate_svc.issue_gate(conn, kind_id)


@router.get("/业务种类/流水")
def kind_events():
    with db() as conn:
        return kind_svc.list_kind_events(conn)


@router.get("/业务种类/停用审计")
def disable_audit():
    # 停用审计：启用灯 / 发号闸 / 存量命运 / 事件重放 四线同态证据
    with db() as conn:
        return kind_svc.audit(conn)


@router.post("/业务种类/{kind_id}/启停")
def set_active(kind_id: int, body: ActiveBody):
    # 写口：immediate 事务与发号/叫号互斥，启停回执含存量快照与事件编号
    with db(immediate=True) as conn:
        return kind_svc.set_kind_active(conn, kind_id, body.启用)
