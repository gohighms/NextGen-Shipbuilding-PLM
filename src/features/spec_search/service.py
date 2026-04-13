from src.features.spec_search.compare import compare_spec_attributes
from src.features.spec_search.models import SpecDocument
from src.features.spec_search.query_parser import extract_attributes_from_text
from src.features.spec_search.repository import SpecRepository
from src.features.spec_search.similarity import cosine_similarity


class SpecSearchService:
    def __init__(self, repository: SpecRepository) -> None:
        self.repository = repository

    def search(self, project_name: str, spec_text: str, top_k: int = 3) -> dict:
        query = SpecDocument(
            spec_id=f"{project_name}-QUERY",
            project_name=project_name,
            text=spec_text,
            attributes=extract_attributes_from_text(spec_text),
        )

        candidates = self.repository.list_all()
        scored_items = []
        for item in candidates:
            score = cosine_similarity(query.text, item.text)
            scored_items.append(
                {
                    "spec_id": item.spec_id,
                    "project_name": item.project_name,
                    "ship_type": item.ship_type,
                    "score": score,
                    "document": item,
                }
            )

        scored_items.sort(key=lambda item: item["score"], reverse=True)
        top_items = scored_items[:top_k]

        comparison = {}
        if top_items:
            comparison = compare_spec_attributes(query, top_items[0]["document"])

        return {
            "query": query,
            "results": top_items,
            "comparison": comparison,
        }
