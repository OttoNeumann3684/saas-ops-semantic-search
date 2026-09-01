from saas_ops_search.search_service import SaaSOpsSearch, SearchRequest


class RecordingBackend:
    def __init__(self) -> None:
        self.tenant_filter = ""

    def embed(self, text: str) -> list[float]:
        assert text == "How do I replace a workspace admin?"
        return [0.2, 0.8]

    def query(
        self, collection: str, embedding: list[float], tenant_id: str, top_k: int
    ) -> dict:
        assert collection == "operations"
        assert embedding == [0.2, 0.8]
        assert top_k == 6
        self.tenant_filter = tenant_id
        return {
            "matches": [
                {
                    "id": "invite-first-admin",
                    "score": 0.91,
                    "metadata": {
                        "title": "Invite the first administrator",
                        "content": "Send an invitation after domain verification.",
                        "operation": "tenant_onboarding",
                    },
                },
                {
                    "id": "rotate-admin-access",
                    "score": 0.84,
                    "metadata": {
                        "title": "Rotate administrator access",
                        "content": "Grant the replacement before revoking old access.",
                        "operation": "admin_operations",
                    },
                },
            ]
        }

    def rerank(self, query: str, candidates: list[str], top_k: int) -> dict:
        assert query == "How do I replace a workspace admin?"
        assert "replacement" in candidates[1]
        assert top_k == 2
        return {"results": [{"index": 1}, {"index": 0}]}


def test_search_applies_tenant_scope_and_uses_reranked_business_result() -> None:
    backend = RecordingBackend()
    service = SaaSOpsSearch(backend, "operations")

    result = service.search(
        SearchRequest(
            tenant_id="tenant-north",
            query="How do I replace a workspace admin?",
            limit=2,
        )
    )

    assert backend.tenant_filter == "tenant-north"
    assert [hit.document_id for hit in result.hits] == [
        "rotate-admin-access",
        "invite-first-admin",
    ]
    assert result.hits[0].operation == "admin_operations"

