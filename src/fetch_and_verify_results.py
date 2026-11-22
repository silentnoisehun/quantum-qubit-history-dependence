#!/usr/bin/env python3
"""
fetch_and_verify_results.py
Waits for all confirmatory jobs to complete, downloads raw counts,
records them to data/confirmatory_result_block_{b}_{job_id}.json,
and commits each result to Git.
"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from qiskit_ibm_runtime import QiskitRuntimeService

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
TOKEN_PATH = Path(r"C:\Users\mater\Downloads\apikey (6).json")

with open(TOKEN_PATH, encoding="utf-8") as f:
    token = json.load(f)["apikey"]

svc = QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance="open-instance")

jobs = [
    (1, "dc1a72inj2vs73df3ebg"),
    (2, "dc1a73dhdvas73bkj2q0"),
    (3, "dc1a745s2omc738ac0k0"),
    (4, "dc1a74thdvas73bkj2rg"),
    (5, "dc1a75thdvas73bkj2t0"),
    (6, "dc1a76lhdvas73bkj2u0"),
    (7, "dc1a77anj2vs73df3eh0"),
]

print("Starting fetch and verification of Confirmatory Blocks 1 to 7...")

for b, jid in jobs:
    out_file = DATA_DIR / f"confirmatory_result_block_{b}_{jid}.json"
    if out_file.exists():
        print(f"Block {b} ({jid}) already downloaded to {out_file.name}. Skipping download.")
        continue

    print(f"\nWaiting for Block {b} ({jid})...")
    j = svc.job(jid)
    while True:
        st = str(j.status())
        print(f"  Block {b} status: {st}")
        if st in ["DONE", "CANCELLED", "ERROR"]:
            break
        time.sleep(5)

    if st != "DONE":
        raise RuntimeError(f"Job {jid} failed with status {st}!")

    res = j.result()
    usage = j.usage()
    print(f"  Block {b} DONE! Usage: {usage}")

    raw_counts = []
    for pub_res in res:
        data_dict = {}
        for cr_name in pub_res.data:
            bitarray = getattr(pub_res.data, cr_name)
            counts = bitarray.get_counts()
            data_dict[cr_name] = counts
        raw_counts.append(data_dict)

    out_data = {
        "job_id": jid,
        "backend": "ibm_marrakesh",
        "block_idx": b,
        "shots": 1000,
        "usage_seconds": usage.get("quantum_seconds", None) if isinstance(usage, dict) else str(usage),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "num_circuits": len(raw_counts),
        "counts": raw_counts
    }

    with open(out_file, "wb") as f:
        f.write(json.dumps(out_data, indent=2).replace("\r\n", "\n").encode("utf-8"))
    print(f"  Saved {len(raw_counts)} circuit results to {out_file.name}")

    # Commit and push result
    subprocess.run(["git", "add", str(out_file)], cwd=str(REPO_ROOT), check=True)
    subprocess.run(["git", "commit", "-m", f"record(confirmatory): downloaded block {b} result {jid} (usage {usage})"], cwd=str(REPO_ROOT), check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=str(REPO_ROOT), check=True)
    print(f"  Block {b} committed and pushed to git.")

print("\nALL 7 BLOCKS DOWNLOADED, COMMITTED, AND PUSHED SUCCESSFULLY!")
