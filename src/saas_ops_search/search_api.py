from __future__ import annotations

import os
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from openai import OpenAIError

from .infrai_client import InfraiClient, InfraiError
from .search_service import SaaSOpsSearch, SearchRequest, SearchResponse

app = FastAPI(title="SaaS operations semantic search")


@lru_cache
def get_search_service() -> SaaSOpsSearch:
    api_key = os.environ["INFRAI_API_KEY"]
    collection = os.environ.get("INFRAI_COLLECTION", "saas-operations")
    return SaaSOpsSearch(InfraiClient(api_key), collection)


@app.post("/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    service: SaaSOpsSearch = Depends(get_search_service),
) -> SearchResponse:
    try:
        return service.search(request)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except OpenAIError as exc:
        upstream_status = getattr(exc, "status_code", None)
        status = upstream_status if isinstance(upstream_status, int) and 400 <= upstream_status < 500 else 502
        raise HTTPException(
            status_code=status,
            detail={"code": "openai_error", "message": str(exc)},
        ) from exc
