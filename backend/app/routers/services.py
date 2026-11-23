from __future__ import annotations
from fastapi import APIRouter
from app.services import core

router = APIRouter(tags=["业务种类"])


@router.get("/业务种类")
def list_services():
    return core.list_services()
