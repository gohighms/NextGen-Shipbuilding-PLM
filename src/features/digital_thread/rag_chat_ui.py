from __future__ import annotations

import pandas as pd
import streamlit as st

from src.common.reuse_state import get_current_spec, get_selected_project
from src.features.digital_thread.rag_llm_service import (
    generate_grounded_answer,
    get_default_model_name,
    is_openai_ready,
)
from src.features.digital_thread.rag_chat_service import answer_rag_question, build_rag_chat_context


CHAT_HISTORY_KEY = "digital_thread_rag_chat_history"
PENDING_QUESTION_KEY = "digital_thread_rag_pending_question"

SUGGESTED_QUESTIONS = [
    "메인 엔진과 연결된 POS, 모델, BOM을 찾아줘",
    "화물창 용적 관련 TAG 경로를 보여줘",
    "선폭과 연결된 모델 객체와 BOM 항목을 알려줘",
    "배관 관련 문구가 POS와 BOM에서 어떻게 이어지는지 알려줘",
]


def render_rag_chat_demo_page() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stChatInput"] {
            border: 2px solid #c53030;
            border-radius: 14px;
            padding: 6px;
            box-shadow: 0 0 0 1px rgba(197, 48, 48, 0.15);
            background: rgba(197, 48, 48, 0.04);
        }
        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] input {
            font-weight: 500;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    current_spec = get_current_spec()
    selected_project = get_selected_project()

    st.title("AI 지식 어시스턴트")
    st.caption(
        "온톨로지/지식그래프와 TAG 연결을 바탕으로 질문을 검색하고, "
        "관련 건조사양서·POS·모델·BOM 근거를 함께 보여줍니다."
    )

    if not current_spec or not selected_project:
        st.info("먼저 `유사 프로젝트 탐색`에서 현재 프로젝트와 기준 실적선을 선택해 주세요.")
        return

    context = build_rag_chat_context(current_spec, selected_project)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("현재 프로젝트", context["project_name"])
    metric_col2.metric("기준 실적선", context["baseline_project_name"])
    metric_col3.metric("TAG 수", context["tag_count"])
    metric_col4.metric("검색 문서 수", context["document_count"])

    use_openai = st.toggle(
        "OpenAI API 답변 사용",
        value=is_openai_ready(),
        help="로컬 RAG 근거를 검색한 뒤, OpenAI API로 더 자연스러운 답변을 생성합니다.",
        key="rag_use_openai_toggle",
    )
    st.caption("현재는 openAI api key 가 없어서, 로컬 RAG 기반만 구동 가능합니다.")
    model_name = st.text_input(
        "OpenAI 모델",
        value=get_default_model_name(),
        disabled=not use_openai,
        key="rag_openai_model_name",
    )
    if use_openai and not is_openai_ready():
        st.warning("`OPENAI_API_KEY`가 설정되지 않아 현재는 로컬 RAG 답변만 사용할 수 있습니다.")

    st.divider()
    st.subheader("추천 질문")
    question_cols = st.columns(2)
    for index, sample in enumerate(SUGGESTED_QUESTIONS):
        with question_cols[index % 2]:
            if st.button(sample, key=f"rag_sample_{index}", use_container_width=True):
                st.session_state[PENDING_QUESTION_KEY] = sample
                st.rerun()

    st.divider()
    st.subheader("질의응답")

    history = st.session_state.setdefault(CHAT_HISTORY_KEY, [])
    for item in history:
        with st.chat_message(item["role"]):
            st.write(item["content"])
            if item["role"] == "assistant" and item.get("mode_label"):
                st.caption(item["mode_label"])
            if item["role"] == "assistant" and item.get("evidence_rows"):
                st.dataframe(pd.DataFrame(item["evidence_rows"]), use_container_width=True, hide_index=True)

    pending_question = st.session_state.pop(PENDING_QUESTION_KEY, None)
    typed_prompt = st.chat_input("예: 메인 엔진과 연결된 BOM 항목을 찾아줘")
    prompt = pending_question or typed_prompt

    if prompt:
        history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        rag_result = answer_rag_question(prompt, context)
        llm_result = (
            generate_grounded_answer(prompt, rag_result, context, model_name=model_name)
            if use_openai
            else {"enabled": False, "answer": rag_result["answer"], "mode": "local_rag"}
        )
        mode_label = _build_mode_label(llm_result)
        assistant_item = {
            "role": "assistant",
            "content": llm_result["answer"],
            "evidence_rows": rag_result["evidence_rows"],
            "mode_label": mode_label,
        }
        history.append(assistant_item)

        with st.chat_message("assistant"):
            st.write(llm_result["answer"])
            st.caption(mode_label)
            if rag_result["matched_tags"]:
                st.caption(f"관련 TAG: {', '.join(rag_result['matched_tags'])}")
            if rag_result["evidence_rows"]:
                st.dataframe(pd.DataFrame(rag_result["evidence_rows"]), use_container_width=True, hide_index=True)

    st.caption("질문 입력창은 항상 하단에 유지되며, 추천 질문을 눌러도 계속 사용할 수 있습니다.")


def _build_mode_label(llm_result: dict) -> str:
    if llm_result.get("mode") == "openai":
        return f"답변 모드: OpenAI API (`{llm_result.get('model', '-')}`) + 로컬 RAG 근거"
    if llm_result.get("mode") == "local_rag_fallback":
        error = llm_result.get("error", "OpenAI API 호출 실패")
        return f"답변 모드: 로컬 RAG fallback ({error})"
    return "답변 모드: 로컬 RAG"
