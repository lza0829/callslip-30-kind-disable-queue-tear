from __future__ import annotations
from fastapi import APIRouter
from app.services import core

router = APIRouter(tags=["营业日"])


@router.get("/营业日")
def get_settings():
    return core.settings_bundle()
