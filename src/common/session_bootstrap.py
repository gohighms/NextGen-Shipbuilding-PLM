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


def initialize_session_environment() -> None:
    if st.session_state.get(SESSION_BOOTSTRAP_KEY):
        return

    _clear_history_directory(TAG_REGISTRY_DIR)
    _clear_history_directory(POS_DRAFT_DIR)
    _clear_history_directory(MODEL_DRAFT_DIR)
    _clear_history_directory(DESIGN_CHANGE_DIR)
    _clear_history_directory(BLOCK_DIVISION_DIR)
    _clear_history_directory(MBOM_DIR)
    _clear_history_directory(WBOM_DIR)
    _clear_history_directory(WORK_INSTRUCTION_DIR)

    st.session_state[SESSION_BOOTSTRAP_KEY] = True


def _clear_history_directory(target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for path in target_dir.glob("*.json"):
        path.unlink(missing_ok=True)
