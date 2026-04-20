from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv


load_dotenv()


def is_openai_ready() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def get_default_model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def generate_grounded_answer(
    question: str,
    rag_result: dict,
    context: dict,
    model_name: str | None = None,
) -> dict:
    if not is_openai_ready():
        return {
            "enabled": False,
            "answer": rag_result["answer"],
            "mode": "local_rag",
        }

    try:
        from openai import OpenAI

        client = OpenAI()
        model = model_name or get_default_model_name()
        evidence_rows = rag_result.get("evidence_rows", [])[:8]
        evidence_text = "\n".join(
            f"- [{row['구분']}] TAG={row['TAG']} | 근거={row['근거 문구']}"
            for row in evidence_rows
        )
        input_text = (
            f"현재 프로젝트: {context.get('project_name', '-')}\n"
            f"기준 실적선: {context.get('baseline_project_name', '-')}\n"
            f"질문: {question}\n"
            f"로컬 RAG 초안 답변: {rag_result.get('answer', '')}\n"
            f"검색된 근거:\n{evidence_text}\n\n"
            "위 근거만 사용해서 한국어로 간결하게 답변하세요. "
            "근거가 부족하면 부족하다고 명시하고, 추정은 하지 마세요."
        )
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "당신은 조선 PLM 데모용 RAG 어시스턴트입니다. "
                            "반드시 제공된 근거 범위 안에서만 답변하고, 한국어로 짧고 명확하게 답하세요.",
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": input_text}],
                },
            ],
        )
        answer_text = _extract_response_text(response) or rag_result["answer"]
        return {
            "enabled": True,
            "answer": answer_text,
            "mode": "openai",
            "model": model,
        }
    except Exception as exc:  # pragma: no cover - network/runtime fallback
        return {
            "enabled": False,
            "answer": rag_result["answer"],
            "mode": "local_rag_fallback",
            "error": str(exc),
        }


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text).strip()

    output = getattr(response, "output", None) or []
    parts: list[str] = []
    for item in output:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(str(text))
    return "\n".join(part.strip() for part in parts if part).strip()
