from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.db import db
from app.services import kinds as kind_svc

router = APIRouter(tags=["业务种类"])


class ActiveBody(BaseModel):
    启用: bool = Field(..., alias="启用")

    class Config:
        populate_by_name = True


@router.get("/业务种类")
def list_kinds():
    with db() as conn:
        return kind_svc.list_kinds(conn)


@router.get("/业务种类/流水")
def kind_events():
    with db() as conn:
        return kind_svc.list_kind_events(conn)


@router.post("/业务种类/{kind_id}/启停")
def set_active(kind_id: int, body: ActiveBody):
    # 写口：immediate 事务与发号/叫号互斥，启停回执含存量快照与事件编号
    with db(immediate=True) as conn:
        return kind_svc.set_kind_active(conn, kind_id, body.启用)
