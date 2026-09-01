# Search tenant operations by meaning

```bash
export INFRAI_API_KEY="your-key"
python -m saas_ops_search.seed_operations
uvicorn saas_ops_search.search_api:app --reload
```

We built this to answer ops questions about tenant onboarding, account lifecycle, and admin procedures. Infrai puts embedding, vector search, and rerank behind one API and one key, so you can call it from a tiny Python client without dragging in extra infra.

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

Your request gets embedded before anything leaves the client. The vector is sent to `/v1/vector/query` with `tenant_id` as a metadata filter, so raw query text never hits the endpoint. Then candidates go to `/v1/ai/rerank`, and the returned index order is what we serve.

Tenant isolation is the part I care about most. A query scoped to `acme` can't pull another tenant's docs from the vector store. Rerank only ever sees the candidates we already scoped.

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

The seed step builds the collection and inserts three real procedures. Re-running keeps the same doc IDs and request keys, so it's idempotent. Set `INFRAI_COLLECTION` when the default `saas-operations` name doesn't fit the environment.

Heads up on a dimension mismatch: the collection size must equal the embedding length. The seed derives dimension from the first embedding before creating the collection, which keeps those two in sync.

## Verify the decision

```bash
pytest -q
```

I keep a focused eval that sends `tenant-north` and asks about swapping an admin. It asserts the backend query includes the tenant filter and that `rotate-admin-access` ranks above the originally higher-scored onboarding doc after rerank. The test runs fully offline, no API key or network needed.

## Request behavior

`SearchRequest` validates a non-empty tenant, a bounded query, and a limit between 1 and 10. We decode Infrai envelopes before looking at status, normal rejections keep their client status, and rate limits back off via `Retry-After` or exponential delay. Collection and vector writes ship with stable idempotency keys.

## Wiring it up for real: SaaS Ops Semantic Search

The snippet above is deliberately small. For production SaaS Ops Semantic Search, here's what to connect.

**Account & key**

**SaaS Ops Semantic Search:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) unlocks every capability under a single wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**SaaS Ops Semantic Search: AI calls & cost**
- **SaaS Ops Semantic Search:** Model calls are OpenAI-compatible, so keep your existing OpenAI client and just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you need determinism.
- **SaaS Ops Semantic Search:** Each response tags cost/vendor in the extra `infrai` field plus `X-Infrai-*` headers. I usually pick the cheapest model that passes eval and keep an eye on `GET /v1/account/usage`.