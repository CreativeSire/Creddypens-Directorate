from __future__ import annotations

import json
import uuid

import requests

BASE = "http://127.0.0.1:8010"


def main() -> None:
    org_id = f"test-org-{uuid.uuid4().hex[:8]}"
    memory = requests.post(
        f"{BASE}/v1/organizations/{org_id}/memories",
        json={
            "memory_type": "preference",
            "memory_key": "tone",
            "memory_value": "casual",
            "confidence": 0.9,
        },
        timeout=30,
    )
    memory.raise_for_status()
    created = memory.json()
    print("Created memory:", json.dumps(created, indent=2))

    listed = requests.get(f"{BASE}/v1/organizations/{org_id}/memories", timeout=30)
    listed.raise_for_status()
    print("List memories count:", len(listed.json()))


if __name__ == "__main__":
    main()
