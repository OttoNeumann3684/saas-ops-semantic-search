from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class SearchRequest:
    tenant_id: str
    query: str
    limit: int = 3

    def __post_init__(self) -> None:
        if not self.tenant_id:
            raise ValueError("tenant_id must not be empty")
        if not 2 <= len(self.query) <= 500:
            raise ValueError("query must contain between 2 and 500 characters")
        if not 1 <= self.limit <= 10:
            raise ValueError("limit must be between 1 and 10")


@dataclass
class SearchHit:
    document_id: str
    title: str
    content: str
    operation: str
    score: float


@dataclass
class SearchResponse:
    tenant_id: str
    hits: list[SearchHit]


class SearchBackend(Protocol):
    embed: Callable[[str], list[float]]
    query: Callable[[str, list[float], str, int], dict[str, Any]]
    rerank: Callable[[str, list[str], int], dict[str, Any]]


class SaaSOpsSearch:
    def __init__(self, backend: SearchBackend, collection: str) -> None:
        self._backend = backend
        self._collection = collection

    def search(self, request: SearchRequest) -> SearchResponse:
        embedding = self._backend.embed(request.query)
        vector_data = self._backend.query(
            self._collection, embedding, request.tenant_id, request.limit * 3
        )
        matches = vector_data.get("matches", [])
        if not matches:
            return SearchResponse(tenant_id=request.tenant_id, hits=[])

        candidates = [self._candidate_text(match) for match in matches]
        reranked = self._backend.rerank(request.query, candidates, request.limit)
        ordered = [matches[item["index"]] for item in reranked.get("results", [])]
        hits = [self._to_hit(match) for match in ordered]
        return SearchResponse(tenant_id=request.tenant_id, hits=hits)

    @staticmethod
    def _candidate_text(match: dict[str, Any]) -> str:
        metadata = match["metadata"]
        return f'{metadata["title"]}\n{metadata["content"]}'

    @staticmethod
    def _to_hit(match: dict[str, Any]) -> SearchHit:
        metadata = match["metadata"]
        return SearchHit(
            document_id=str(match["id"]),
            title=str(metadata["title"]),
            content=str(metadata["content"]),
            operation=str(metadata["operation"]),
            score=float(match["score"]),
        )
