#!/usr/bin/env python3
"""
generate_prereg_hashes.py — Computes frozen SHA256 hashes of all protocol code and manifest.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PREREG_DIR = REPO_ROOT / "prereg"
SRC_DIR = REPO_ROOT / "src"

FILES_TO_FREEZE = [
    SRC_DIR / "circuit_builder.py",
    SRC_DIR / "audit_transpiler.py",
    SRC_DIR / "analysis.py",
    SRC_DIR / "simulator.py",
    PREREG_DIR / "manifest_audit.json",
]

def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def freeze_all():
    records = {}
    for p in FILES_TO_FREEZE:
        if not p.exists():
            raise FileNotFoundError(f"Missing file to freeze: {p}")
        records[p.name] = {
            "path": str(p.relative_to(REPO_ROOT)),
            "sha256": hash_file(p),
            "size_bytes": p.stat().st_size
        }

    out_doc = {
        "frozen_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": "ibm_marrakesh",
        "primary_qubit": 21,
        "spectator_qubit": 20,
        "files": records
    }

    out_path = PREREG_DIR / "FROZEN_SPEC.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_doc, f, indent=2)

    print(f"Frozen specifications written to: {out_path}")
    for k, v in records.items():
        print(f"  {k:25s} : {v['sha256']}")

if __name__ == "__main__":
    freeze_all()
