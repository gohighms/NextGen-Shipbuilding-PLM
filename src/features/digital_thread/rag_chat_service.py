from __future__ import annotations

import re
from collections import defaultdict

from src.features.tag_management.tag_generator import generate_tags_from_attributes
from src.features.tag_management.ui import _build_extended_tag_result


STAGE_LABELS = {
    "spec": "건조사양서",
    "pos": "POS",
    "model": "모델",
    "bom": "BOM",
}

SYNONYM_MAP = {
    "주기관": ["메인 엔진", "main engine", "기자재", "engine"],
    "메인엔진": ["메인 엔진", "main engine", "기자재", "engine"],
    "기자재": ["메인 엔진", "main engine", "engine", "foundation"],
    "화물창": ["cargo tank", "tank", "membrane", "cargo"],
    "용적": ["capacity", "cargo capacity", "m3"],
    "선폭": ["breadth", "beam"],
    "전장": ["loa", "length overall"],
    "흘수": ["draft"],
    "배관": ["pipe", "piping", "flange"],
    "탱크": ["cargo tank", "membrane", "tank"],
    "foundation": ["기초", "bed", "support"],
}


def build_rag_chat_context(current_spec: dict | None, selected_project: dict | None) -> dict:
    if not current_spec or not selected_project:
        return {
            "project_name": "",
            "baseline_project_name": "",
            "documents": [],
            "paths": [],
            "tag_count": 0,
            "document_count": 0,
        }

    tag_result = _build_extended_tag_result(
        generate_tags_from_attributes(current_spec.get("attributes", {})),
        current_spec,
        selected_project,
    )
    paths = tag_result.get("tag_link_rows", [])
    documents = _build_documents(paths)

    return {
        "project_name": current_spec["project_name"],
        "baseline_project_name": selected_project["project_name"],
        "documents": documents,
        "paths": paths,
        "tag_count": len(tag_result.get("tags", [])),
        "document_count": len(documents),
    }


def answer_rag_question(question: str, context: dict) -> dict:
    query = (question or "").strip()
    if not query:
        return {
            "answer": "질문을 입력하면 관련 건조사양서, POS, 모델, BOM 항목을 찾아 보여드립니다.",
            "evidence_rows": [],
            "matched_tags": [],
        }

    documents = context.get("documents", [])
    ranked = _rank_documents(query, documents)
    top_docs = ranked[:8]
    matched_tags = _collect_top_tags(top_docs)
    best_path = _find_best_path(context.get("paths", []), matched_tags, query)
    answer = _compose_answer(query, best_path, top_docs, matched_tags)

    evidence_rows = [
        {
            "구분": STAGE_LABELS[item["stage"]],
            "TAG": item["tag"],
            "근거 문구": item["text"],
            "점수": round(item["score"], 2),
        }
        for item in top_docs
    ]

    return {
        "answer": answer,
        "evidence_rows": evidence_rows,
        "matched_tags": matched_tags,
    }


def _build_documents(paths: list[dict]) -> list[dict]:
    documents: list[dict] = []
    seen = set()

    for row in paths:
        tag_name = str(row.get("TAG", "")).strip()
        stage_map = {
            "spec": str(row.get("건조사양서 문구", "")).strip(),
            "pos": str(row.get("POS 문구", "")).strip(),
            "model": str(row.get("모델 연결 객체", "")).strip(),
            "bom": str(row.get("BOM 연결 항목", "")).strip(),
        }

        for stage, text in stage_map.items():
            if not text:
                continue
            key = (stage, text, tag_name)
            if key in seen:
                continue
            seen.add(key)
            documents.append(
                {
                    "id": f"{stage}::{len(documents) + 1}",
                    "stage": stage,
                    "tag": tag_name,
                    "text": text,
                    "tokens": _tokenize(f"{text} {tag_name}"),
                }
            )

    return documents


def _rank_documents(query: str, documents: list[dict]) -> list[dict]:
    query_tokens = _expand_tokens(_tokenize(query))
    scored = []

    for item in documents:
        item_tokens = set(item["tokens"])
        overlap = len(query_tokens & item_tokens)
        substring_bonus = 2.0 if query.lower() in item["text"].lower() else 0.0
        tag_bonus = 1.5 if any(token in item["tag"].lower() for token in query_tokens) else 0.0
        score = overlap + substring_bonus + tag_bonus
        if score <= 0:
            continue
        scored.append({**item, "score": score})

    scored.sort(key=lambda item: (-item["score"], item["stage"], item["text"]))
    return scored


def _collect_top_tags(top_docs: list[dict]) -> list[str]:
    tag_scores: dict[str, float] = defaultdict(float)
    for item in top_docs:
        tag_scores[item["tag"]] += float(item["score"])
    return [tag for tag, _ in sorted(tag_scores.items(), key=lambda pair: (-pair[1], pair[0]))[:5]]


def _find_best_path(paths: list[dict], matched_tags: list[str], query: str) -> dict | None:
    if not paths:
        return None

    query_tokens = _expand_tokens(_tokenize(query))
    best_row = None
    best_score = -1.0

    for row in paths:
        tag_name = str(row.get("TAG", ""))
        row_text = " ".join(
            [
                str(row.get("건조사양서 문구", "")),
                str(row.get("POS 문구", "")),
                str(row.get("모델 연결 객체", "")),
                str(row.get("BOM 연결 항목", "")),
                tag_name,
            ]
        )
        row_tokens = _expand_tokens(_tokenize(row_text))
        score = len(query_tokens & row_tokens)
        if tag_name in matched_tags:
            score += 2.0
        if score > best_score:
            best_score = score
            best_row = row

    return best_row


def _compose_answer(query: str, best_path: dict | None, top_docs: list[dict], matched_tags: list[str]) -> str:
    if not top_docs:
        return (
            f"`{query}`와 직접 맞닿는 항목을 현재 데모 데이터에서 찾지 못했습니다. "
            "다른 키워드로 질문하거나 메인 엔진, 화물창, 선폭, 전장 같은 핵심 용어로 다시 질문해보세요."
        )

    if best_path:
        spec_text = best_path.get("건조사양서 문구", "-")
        pos_text = best_path.get("POS 문구", "-")
        model_text = best_path.get("모델 연결 객체", "-")
        bom_text = best_path.get("BOM 연결 항목", "-")
        tag_text = best_path.get("TAG", "-")
        return (
            f"질문 `{query}`와 가장 가까운 연결은 TAG `{tag_text}` 기준입니다. "
            f"건조사양서에서는 `{spec_text}`로 나타나고, POS에서는 `{pos_text}`로 이어집니다. "
            f"이후 모델에서는 `{model_text}` 객체로 연결되고, BOM에서는 `{bom_text}` 항목까지 추적됩니다."
        )

    stage_summary = ", ".join(STAGE_LABELS[item["stage"]] for item in top_docs[:4])
    tag_summary = ", ".join(matched_tags[:3]) if matched_tags else "관련 TAG 없음"
    return (
        f"질문 `{query}`에 대해 `{tag_summary}` 중심으로 검색했습니다. "
        f"현재 근거는 `{stage_summary}` 단계에서 확인됐습니다."
    )


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9가-힣\-_\.]+", str(text)) if len(token) >= 2}


def _expand_tokens(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    for token in list(tokens):
        for key, synonyms in SYNONYM_MAP.items():
            if key in token or token in key:
                expanded.add(key.lower())
                expanded.update(item.lower() for item in synonyms)
    return expanded
