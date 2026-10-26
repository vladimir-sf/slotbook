"""CI-only pytest inventory/provenance; never imports application modules."""

import hashlib
import json
import os
from pathlib import Path


def pytest_collection_modifyitems(items):
    identities = [
        "QA-" + hashlib.sha256(item.nodeid.encode()).hexdigest() for item in items
    ]
    path = Path(os.environ["SLOTBOOK_CI_INVENTORY"])
    if path.exists():
        if json.loads(path.read_text()) != identities:
            raise RuntimeError("ci_inventory_changed")
    else:
        with path.open("x") as file:
            file.write(json.dumps(identities))
    # QA's own conftest emits these properties. Backend stays independent of QA packages.
    if os.environ["SLOTBOOK_CI_LANE"] == "backend":
        for item, identity in zip(items, identities, strict=True):
            item.user_properties.extend(
                [
                    ("evidence_id", identity),
                    ("candidate_sha256", os.environ["SLOTBOOK_CANDIDATE_SHA256"]),
                ]
            )
