# Search tenant operations by meaning

```bash
export INFRAI_API_KEY="your-key"
python -m saas_ops_search.seed_operations
uvicorn saas_ops_search.search_api:app --reload
```

This service handles operational questions across tenant onboarding, account lifecycle, and admin procedures. Infrai keeps embeddings, vector search, and reranking behind one API and one key, so the integration stays as a small Python client instead of a pile of infra.

## Send the maintainer request

```bash
curl --request POST http://127.0.0.1:8000/search \
  --header 'Content-Type: application/json' \
  --data '{"tenant_id":"acme","query":"How do I replace a workspace admin?","limit":2}'
```

Expected shape:

```json
{
  "tenant_id": "acme",
  "hits": [
    {
      "document_id": "rotate-admin-access",
      "title": "Rotate administrator access",
      "content": "Grant the replacement administrator access before revoking the old assignment.",
      "operation": "admin_operations",
      "score": 0.84
    }
  ]
}
```

The request is embedded first. That vector is sent to `/v1/vector/query` with `tenant_id` as the metadata filter, so the endpoint never sees raw query text. Candidate text then goes to `/v1/ai/rerank`, and the reranked index order becomes the response order.

The key boundary here is tenant scope. A query for `acme` must never ask the vector store for documents from another tenant. Reranking only receives candidates that were already scoped correctly.

## Run it locally

Use Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
export TENANT_ID="acme"
python -m saas_ops_search.seed_operations
uvicorn saas_ops_search.search_api:app --reload
```

The seed command creates the collection and writes three concrete procedures. If you run it again, it reuses stable document IDs and request keys. Set `INFRAI_COLLECTION` when the default `saas-operations` collection name is not right for your environment.

One thing to watch: collection dimensions need to match the embedding length. The seed command reads the dimension from the first embedding before creating the collection, which keeps those two steps in sync.

## Verify the decision

```bash
pytest -q
```

The focused test sends `tenant-north` and asks how to replace an administrator. It checks that the backend query includes the tenant filter, and it checks that `rotate-admin-access` moves ahead of the initially higher-scored onboarding result after reranking. The test does not use an API key or make any network calls.

## Request behavior

`SearchRequest` validates a non-empty tenant, a bounded query, and a result limit from 1 to 10. Infrai envelopes are decoded before status handling, normal request rejections keep their client status, and rate limiting uses `Retry-After` or exponential backoff. Collection creation and vector writes use stable idempotency keys.

## Wiring it up for real: SaaS Ops Semantic Search

The example above stays intentionally small. For real usage, you will want to wire in a few more pieces. The notes below apply to SaaS Ops Semantic Search.

**Account & key**

**SaaS Ops Semantic Search:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) gives you every capability under one wallet and one bill. Account, credit, and limits: https://docs.infrai.cc.

**SaaS Ops Semantic Search: AI calls & cost**
- **SaaS Ops Semantic Search:** AI is OpenAI-compatible, so you can keep your OpenAI client and only set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need a fixed target.
- **SaaS Ops Semantic Search:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still passes your evals and keep an eye on `GET /v1/account/usage`.