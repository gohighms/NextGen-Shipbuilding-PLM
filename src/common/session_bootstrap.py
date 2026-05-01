import os
from pathlib import Path

import streamlit as st

from src.common.paths import (
    BLOCK_DIVISION_DIR,
    DESIGN_CHANGE_DIR,
    MBOM_DIR,
    MODEL_DRAFT_DIR,
    POS_DRAFT_DIR,
    TAG_REGISTRY_DIR,
    WBOM_DIR,
    WORK_INSTRUCTION_DIR,
)


SESSION_BOOTSTRAP_KEY = "session_environment_initialized"
RESET_HISTORY_ENV_KEY = "NEXTGEN_RESET_HISTORY_ON_START"


def initialize_session_environment() -> None:
    if st.session_state.get(SESSION_BOOTSTRAP_KEY):
        return

    history_dirs = [
        TAG_REGISTRY_DIR,
        POS_DRAFT_DIR,
        MODEL_DRAFT_DIR,
        DESIGN_CHANGE_DIR,
        BLOCK_DIVISION_DIR,
        MBOM_DIR,
        WBOM_DIR,
        WORK_INSTRUCTION_DIR,
    ]
    for target_dir in history_dirs:
        target_dir.mkdir(parents=True, exist_ok=True)

    if _should_reset_history_on_start():
        for target_dir in history_dirs:
            _clear_history_directory(target_dir)

    st.session_state[SESSION_BOOTSTRAP_KEY] = True


def _should_reset_history_on_start() -> bool:
    return os.getenv(RESET_HISTORY_ENV_KEY, "").strip().lower() in {"1", "true", "yes", "y"}


def _clear_history_directory(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for path in target_dir.glob("*.json"):
        path.unlink(missing_ok=True)
