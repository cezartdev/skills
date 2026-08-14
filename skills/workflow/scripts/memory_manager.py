"""Hierarchical markdown memory manager and deterministic 00-10 compaction engine."""

import os
import re
from typing import Dict, Any, List
from datetime import datetime


ARCHETYPES = ["fix", "refactor", "implement", "doc_sync"]


def get_archetype_memory_dir(root_dir: str, archetype: str) -> str:
    """Returns directory path for a specific archetype's memory namespace under .workflow/memory/."""
    root_dir = os.path.abspath(root_dir)
    wf_root = os.path.join(root_dir, ".workflow") if os.path.basename(root_dir) != ".workflow" else root_dir
    arch_dir = os.path.join(wf_root, "memory", archetype)
    os.makedirs(arch_dir, exist_ok=True)
    return arch_dir


def log_decision(
    root_dir: str,
    archetype: str,
    title: str,
    content: str,
    spec_name: str = ""
) -> str:
    """Writes an episodic decision file (e.g. 01_title.md) in the archetype's memory."""
    arch_dir = get_archetype_memory_dir(root_dir, archetype)
    existing_files = sorted([f for f in os.listdir(arch_dir) if f.endswith(".md") and not f.startswith("00_")])
    next_idx = len(existing_files) + 1
    
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", title.lower()).strip("_")
    filename = f"{next_idx:02d}_{slug}.md"
    file_path = os.path.join(arch_dir, filename)

    doc = f"""# Decision: {title}

**Archetype**: `{archetype}`  
**Spec**: `{spec_name or 'N/A'}`  
**Recorded At**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  

---

## Context & Rationale
{content}
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(doc)

    # Check if threshold reached for automatic compaction
    if len(existing_files) + 1 >= 10:
        compact_archetype_memory(root_dir, archetype)

    return file_path


def compact_archetype_memory(root_dir: str, archetype: str) -> Dict[str, Any]:
    """Compacts episodic files (01..10) into memory/<archetype>/00_<archetype>_context.md."""
    arch_dir = get_archetype_memory_dir(root_dir, archetype)
    episodic_files = sorted([f for f in os.listdir(arch_dir) if f.endswith(".md") and not f.startswith("00_")])

    if not episodic_files:
        return {"status": "SKIPPED", "message": f"No episodic files to compact in memory/{archetype}/"}

    context_file = os.path.join(arch_dir, f"00_{archetype}_context.md")
    
    # Read existing 00 context or create new
    existing_summary = ""
    if os.path.exists(context_file):
        with open(context_file, "r", encoding="utf-8") as f:
            existing_summary = f.read()

    new_entries: List[str] = []
    for filename in episodic_files:
        filepath = os.path.join(arch_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()
        first_line = raw.splitlines()[0].replace("#", "").strip() if raw else filename
        new_entries.append(f"- **{filename}**: {first_line}")

    rollup_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    compacted_content = f"""# Consolidated Context: {archetype.capitalize()} Archetype

**Last Compacted**: `{rollup_date}`  
**Compacted Batch Count**: `{len(episodic_files)} items`

---

## 1. Key Invariants & Architectural Patterns
<!-- Cumulative synthesized insights for {archetype} operations -->

## 2. Compacted Decision History
{chr(10).join(new_entries)}

---
{existing_summary if "## Past Batches" in existing_summary else ""}
"""

    with open(context_file, "w", encoding="utf-8") as f:
        f.write(compacted_content)

    # Prune episodic files (01..10)
    for filename in episodic_files:
        os.remove(os.path.join(arch_dir, filename))

    return {
        "status": "COMPACTED",
        "archetype": archetype,
        "compacted_count": len(episodic_files),
        "context_file": context_file,
    }


def get_memory_status(root_dir: str = ".") -> Dict[str, Any]:
    """Returns memory status and file counts across all archetypes under .workflow/memory/."""
    root_dir = os.path.abspath(root_dir)
    wf_root = os.path.join(root_dir, ".workflow") if os.path.basename(root_dir) != ".workflow" else root_dir
    mem_dir = os.path.join(wf_root, "memory")
    
    status = {"master_context_exists": os.path.exists(os.path.join(mem_dir, "00_project_context.md")), "namespaces": {}}

    for arch in ARCHETYPES:
        arch_dir = os.path.join(mem_dir, arch)
        if os.path.exists(arch_dir):
            files = [f for f in os.listdir(arch_dir) if f.endswith(".md")]
            episodic = [f for f in files if not f.startswith("00_")]
            has_context = any(f.startswith("00_") for f in files)
            status["namespaces"][arch] = {
                "episodic_count": len(episodic),
                "has_context": has_context,
                "needs_compaction": len(episodic) >= 10,
            }
        else:
            status["namespaces"][arch] = {
                "episodic_count": 0,
                "has_context": False,
                "needs_compaction": False,
            }

    return status
