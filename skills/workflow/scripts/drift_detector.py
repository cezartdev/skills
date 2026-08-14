"""Tech drift and manifest anomaly detection engine."""

import os
import re
from typing import Dict, Any, Tuple
try:
    from .explorer import scan_codebase, generate_master_context
except ImportError:
    from explorer import scan_codebase, generate_master_context


def check_drift(root_dir: str = ".") -> Tuple[bool, Dict[str, Any]]:
    """Compares current manifest hashes against memory/00_project_context.md."""
    root_dir = os.path.abspath(root_dir)
    master_file = os.path.join(root_dir, "memory", "00_project_context.md")

    if not os.path.exists(master_file):
        return True, {"reason": "MISSING_MEMORY", "details": "memory/00_project_context.md does not exist"}

    with open(master_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract recorded manifest fingerprints
    recorded_fingerprints: Dict[str, str] = {}
    fingerprint_match = re.search(r"\*\*Manifest Fingerprints\*\*:\s*(.+)", content)
    if fingerprint_match:
        items = fingerprint_match.group(1).split("|")
        for item in items:
            parts = item.strip().split(":")
            if len(parts) == 2:
                filename = parts[0].strip()
                hashval = parts[1].strip().replace("`", "")
                recorded_fingerprints[filename] = hashval

    # Scan current manifests
    current_scan = scan_codebase(root_dir)
    current_fingerprints = current_scan.get("manifest_hashes", {})

    drift_detected = False
    drift_details = {}

    for manifest, current_hash in current_fingerprints.items():
        recorded_hash = recorded_fingerprints.get(manifest)
        if not recorded_hash:
            drift_detected = True
            drift_details[manifest] = f"New manifest added (hash: {current_hash})"
        elif recorded_hash != current_hash:
            drift_detected = True
            drift_details[manifest] = f"Hash changed (was: {recorded_hash}, now: {current_hash})"

    return drift_detected, {
        "drift_detected": drift_detected,
        "details": drift_details,
        "scanned_manifests": list(current_fingerprints.keys()),
    }


def sync_drift(root_dir: str = ".") -> Dict[str, Any]:
    """Re-runs explorer to reconcile memory and workflow config if drift occurred."""
    root_dir = os.path.abspath(root_dir)
    drift, info = check_drift(root_dir)
    if drift:
        master_path = generate_master_context(root_dir)
        return {
            "status": "SYNCED",
            "message": "Tech drift resolved and master context updated.",
            "master_file": master_path,
            "drift_info": info,
        }
    return {
        "status": "UP_TO_DATE",
        "message": "No tech drift detected. Context is synchronized.",
    }
