from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.db import db
from app.services import windows as win_svc

router = APIRouter(tags=["窗口"])


class OpenBody(BaseModel):
    开放: bool = Field(..., alias="开放")

    class Config:
        populate_by_name = True


@router.get("/窗口")
def list_windows():
    with db() as conn:
        return win_svc.list_windows(conn)


@router.post("/窗口/{window_id}/开闭")
def set_open(window_id: int, body: OpenBody):
    with db(immediate=True) as conn:
        return win_svc.set_open(conn, window_id, body.开放)

def _surface_router_windows() -> dict:
    return {"panel": "windows", "ready": True}

