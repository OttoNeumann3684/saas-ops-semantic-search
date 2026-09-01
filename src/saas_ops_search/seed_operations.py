from __future__ import annotations

import hashlib
import os

from .infrai_client import InfraiClient

DOCUMENTS = [
    {
        "id": "invite-first-admin",
        "title": "Invite the first workspace administrator",
        "content": "Create the tenant, verify its domain, then send an administrator invitation.",
        "operation": "tenant_onboarding",
    },
    {
        "id": "suspend-account",
        "title": "Suspend an account",
        "content": "Suspend access while retaining account records for an operator review.",
        "operation": "account_lifecycle",
    },
    {
        "id": "rotate-admin-access",
        "title": "Rotate administrator access",
        "content": "Grant the replacement administrator access before revoking the old assignment.",
        "operation": "admin_operations",
    },
]


def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    collection = os.environ.get("INFRAI_COLLECTION", "saas-operations")
    tenant_id = os.environ.get("TENANT_ID", "acme")
    client = InfraiClient(api_key)
    try:
        embedded = [(doc, client.embed(f'{doc["title"]}\n{doc["content"]}')) for doc in DOCUMENTS]
        dimension = len(embedded[0][1])
        client.create_collection(
            collection, dimension, {"purpose": "saas_operations_search"}
        )
        vectors = [
            {
                "id": doc["id"],
                "values": values,
                "metadata": {
                    "tenant_id": tenant_id,
                    "title": doc["title"],
                    "content": doc["content"],
                    "operation": doc["operation"],
                },
            }
            for doc, values in embedded
        ]
        digest = hashlib.sha256(
            f'{tenant_id}:{":".join(doc["id"] for doc in DOCUMENTS)}'.encode()
        ).hexdigest()[:16]
        client.upsert(collection, vectors, digest)
        print(f"Indexed {len(vectors)} operations for tenant {tenant_id}.")
    finally:
        client.close()


if __name__ == "__main__":
    main()

