from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.db import db
from app.services import dayseal

router = APIRouter(tags=["日切"])


class SealBody(BaseModel):
    强制: bool = Field(False, alias="强制")

    class Config:
        populate_by_name = True


class RollBody(BaseModel):
    营业日: str | None = Field(None, alias="营业日")

    class Config:
        populate_by_name = True


class DayBody(BaseModel):
    营业日: str = Field(..., alias="营业日")

    class Config:
        populate_by_name = True


@router.get("/日切")
def get_seal():
    with db() as conn:
        return dayseal.get_seal(conn)


@router.post("/日切/封口")
def seal(body: SealBody | None = None):
    with db(immediate=True) as conn:
        force = body.强制 if body else False
        return dayseal.seal_day(conn, force=force)


@router.post("/日切/解封")
def unseal():
    with db(immediate=True) as conn:
        return dayseal.unseal_day(conn)


@router.post("/日切/切日")
def roll(body: RollBody | None = None):
    with db(immediate=True) as conn:
        target = body.营业日 if body else None
        return dayseal.roll_day(conn, target)


@router.get("/设置")
def settings():
    with db() as conn:
        return dayseal.get_seal(conn)


@router.post("/设置/营业日")
def set_day(body: DayBody):
    with db(immediate=True) as conn:
        return dayseal.roll_day(conn, body.营业日)
