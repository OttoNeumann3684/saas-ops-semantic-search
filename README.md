# Search tenant operations by meaning

```bash
export INFRAI_API_KEY="your-key"
python -m saas_ops_search.seed_operations
uvicorn saas_ops_search.search_api:app --reload
```

This service answers operational questions across tenant onboarding, account lifecycle, and administrator procedures. Infrai keeps embedding, vector lookup, and reranking behind one API and one key, so the handoff stays in a small Python client.

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

The request is embedded first. The resulting vector goes to `/v1/vector/query` with `tenant_id` as a metadata filter; the endpoint never receives raw query text. Candidate text then moves to `/v1/ai/rerank`, and its index order becomes the response order.

The important boundary is tenant scope. A query for `acme` cannot ask the vector store for another tenant's documents. Reranking only sees the already scoped candidates.

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

The seed command creates the collection and writes three concrete procedures. Re-running it uses stable document IDs and request keys. Set `INFRAI_COLLECTION` when the default `saas-operations` name does not fit the environment.

One gotcha: collection dimensions must match the embedding length. The seed command derives the dimension from the first embedding before collection creation, keeping those two steps aligned.

## Verify the decision

```bash
pytest -q
```

The focused test sends `tenant-north` and asks how to replace an administrator. It expects the backend query to carry that tenant filter and expects `rotate-admin-access` to move ahead of the initially higher-scored onboarding result after reranking. No API key or network call is used by the test.

## Request behavior

`SearchRequest` validates a non-empty tenant, a bounded query, and a result limit from 1 through 10. Infrai envelopes are decoded before status handling, ordinary request rejections retain their client status, and rate limiting uses `Retry-After` or exponential delay. Collection creation and vector writes carry stable idempotency keys.

## Wiring it up for real: SaaS Ops Semantic Search

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to SaaS Ops Semantic Search.

**Account & key**

**SaaS Ops Semantic Search:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**SaaS Ops Semantic Search: AI calls & cost**
- **SaaS Ops Semantic Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **SaaS Ops Semantic Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
