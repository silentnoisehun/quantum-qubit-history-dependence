#!/usr/bin/env python3
"""
generate_prereg_hashes.py — Computes frozen SHA256 hashes with POSIX paths and LF normalization.
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
    SRC_DIR / "pilot_runner.py",
    SRC_DIR / "pilot_blind_analysis.py",
    PREREG_DIR / "manifest_audit.json",
    PREREG_DIR / "PREDICTIONS.md",
]

def hash_file_normalized(path: Path) -> str:
    with open(path, "rb") as f:
        content = f.read().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()

def freeze_all():
    records = {}
    for p in FILES_TO_FREEZE:
        if not p.exists():
            raise FileNotFoundError(f"Missing file to freeze: {p}")
        posix_rel = p.relative_to(REPO_ROOT).as_posix()
        records[p.name] = {
            "path": posix_rel,
            "sha256": hash_file_normalized(p),
            "size_bytes": p.stat().st_size
        }

    out_doc = {
        "frozen_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": "ibm_marrakesh",
        "processor": "Heron r2",
        "primary_qubit": 21,
        "spectator_qubit": 20,
        "files": records
    }

    out_path = PREREG_DIR / "FROZEN_SPEC.json"
    with open(out_path, "wb") as f:
        data_str = json.dumps(out_doc, sort_keys=True, indent=2).replace("\r\n", "\n")
        f.write(data_str.encode("utf-8"))

    print(f"Frozen specifications written to: {out_path}")
    for k, v in records.items():
        print(f"  {k:25s} : {v['sha256']}")

if __name__ == "__main__":
    freeze_all()
