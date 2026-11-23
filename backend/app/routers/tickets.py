from __future__ import annotations
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from app.db import db
from app.services import tickets as tic

router = APIRouter(tags=["号牌"])


class TakeBody(BaseModel):
    种类编号: int = Field(..., alias="种类编号")

    class Config:
        populate_by_name = True


class CallBody(BaseModel):
    窗口编号: int = Field(..., alias="窗口编号")
    种类编号: int | None = Field(None, alias="种类编号")

    class Config:
        populate_by_name = True


class RecallBody(BaseModel):
    窗口编号: int | None = Field(None, alias="窗口编号")

    class Config:
        populate_by_name = True


@router.get("/号牌")
def list_tickets(状态: str | None = Query(None)):
    with db() as conn:
        return tic.list_tickets(conn, status=状态)


@router.get("/等候墙")
def waiting_wall():
    with db() as conn:
        return tic.waiting_wall(conn)


@router.get("/叫号流水")
def events():
    with db() as conn:
        return tic.list_events(conn)


@router.post("/取号")
def take(body: TakeBody):
    with db(immediate=True) as conn:
        return tic.take_ticket(conn, body.种类编号)


@router.post("/叫号")
def call_next(body: CallBody):
    with db(immediate=True) as conn:
        return tic.call_next(conn, body.窗口编号, body.种类编号)


@router.post("/号牌/{ticket_id}/过号")
def skip(ticket_id: int):
    with db(immediate=True) as conn:
        return tic.mark_skip(conn, ticket_id)


@router.post("/号牌/{ticket_id}/重叫")
def recall(ticket_id: int, body: RecallBody | None = None):
    with db(immediate=True) as conn:
        wid = body.窗口编号 if body else None
        return tic.recall(conn, ticket_id, wid)


@router.post("/号牌/{ticket_id}/办结")
def finish(ticket_id: int):
    with db(immediate=True) as conn:
        return tic.finish(conn, ticket_id)


@router.post("/号牌/{ticket_id}/作废")
def void(ticket_id: int):
    with db(immediate=True) as conn:
        return tic.void_ticket(conn, ticket_id)

def _surface_router_tickets() -> dict:
    return {"panel": "tickets", "ready": True}

