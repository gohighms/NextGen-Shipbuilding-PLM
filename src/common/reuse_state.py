import streamlit as st


REUSE_PROJECT_KEY = "reuse_selected_project"
CURRENT_SPEC_KEY = "reuse_current_spec"


def set_current_spec(project_name: str, spec_text: str, attributes: dict) -> None:
    st.session_state[CURRENT_SPEC_KEY] = {
        "project_name": project_name,
        "spec_text": spec_text,
        "attributes": attributes,
    }


def get_current_spec() -> dict | None:
    return st.session_state.get(CURRENT_SPEC_KEY)


def set_selected_project(project_payload: dict) -> None:
    st.session_state[REUSE_PROJECT_KEY] = project_payload


def get_selected_project() -> dict | None:
    return st.session_state.get(REUSE_PROJECT_KEY)
