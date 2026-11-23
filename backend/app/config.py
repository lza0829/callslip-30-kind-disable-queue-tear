from __future__ import annotations
import os
from pathlib import Path

PROJECT_NAME = "叫号条"
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("CALLSLIP_DB", str(ROOT / "data" / "callslip.db")))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 号牌状态（仅中文）
TICKET_STATUSES = ("等候", "叫号中", "办理中", "过号", "已办结", "已作废")
ACTIVE_QUEUE = ("等候", "叫号中", "办理中", "过号")
