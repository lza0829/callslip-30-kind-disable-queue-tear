from __future__ import annotations
from fastapi import APIRouter
from app.services import core

router = APIRouter(tags=["日切"])


@router.post("/日切/封口")
def seal():
    return core.seal_day()


@router.post("/日切/解封")
def unseal():
    return core.unseal_day()
