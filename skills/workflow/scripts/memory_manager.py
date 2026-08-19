"""Centralized Memory Manager for Project Context, Coding Preferences, and Documentation Notes.

Manages:
- .workflow/memory/coding_preferences.md (Code style, linters, naming conventions)
- .workflow/memory/project_context.md (Polyglot stack, architectural invariants, frameworks)
- .workflow/memory/docs/ (Sequential indexed notes: 01_title.md, 02_title.md, etc.)
"""

import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from scaffolder import get_workflow_root, reconcile_gitkeep
except ImportError:
    from .scaffolder import get_workflow_root, reconcile_gitkeep


def get_memory_dir(target_dir: str = ".") -> str:
    """Returns absolute path to .workflow/memory/."""
    target_dir = os.path.abspath(target_dir)
    wf_root = get_workflow_root(target_dir)
    mem_dir = os.path.join(wf_root, "memory")
    os.makedirs(mem_dir, exist_ok=True)
    return mem_dir


def get_memory_docs_dir(target_dir: str = ".") -> str:
    """Returns absolute path to .workflow/memory/docs/."""
    mem_dir = get_memory_dir(target_dir)
    docs_dir = os.path.join(mem_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    reconcile_gitkeep(docs_dir)
    return docs_dir


def add_memory_doc(
    title: str,
    content: str,
    target_dir: str = ".",
    author: Optional[str] = None
) -> Dict[str, Any]:
    """Adds a sequential indexed documentation note under .workflow/memory/docs/."""
    docs_dir = get_memory_docs_dir(target_dir)
    
    # Calculate next index based on existing files
    existing_files = sorted([f for f in os.listdir(docs_dir) if f.endswith(".md")])
    indices = []
    for f in existing_files:
        m = re.match(r"^(\d+)_", f)
        if m:
            indices.append(int(m.group(1)))
    next_idx = max(indices, default=0) + 1

    clean_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", title.lower()).strip("_")
    filename = f"{next_idx:02d}_{clean_slug}.md"
    filepath = os.path.join(docs_dir, filename)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header_content = f"""# {title}

- **Recorded At**: `{now_str}`
- **Index**: `{next_idx:02d}`
{f"- **Author**: `{author}`" if author else ""}

---

## 📝 Details & Guidelines
{content.strip()}
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header_content)

    reconcile_gitkeep(docs_dir)

    return {
        "status": "CREATED",
        "index": next_idx,
        "filename": filename,
        "path": filepath,
        "title": title,
    }


def list_memory_catalog(target_dir: str = ".") -> Dict[str, Any]:
    """Returns all memory artifacts: coding_preferences, project_context, and docs/*.md."""
    mem_dir = get_memory_dir(target_dir)
    docs_dir = get_memory_docs_dir(target_dir)

    # Core master files (support both new and legacy filenames)
    pref_file = os.path.join(mem_dir, "coding_preferences.md")
    legacy_pref = os.path.join(mem_dir, "00_coding_preferences.md")
    has_prefs = os.path.exists(pref_file) or os.path.exists(legacy_pref)
    actual_pref_path = pref_file if os.path.exists(pref_file) else (legacy_pref if os.path.exists(legacy_pref) else pref_file)

    context_file = os.path.join(mem_dir, "project_context.md")
    legacy_context = os.path.join(mem_dir, "00_project_context.md")
    has_context = os.path.exists(context_file) or os.path.exists(legacy_context)
    actual_context_path = context_file if os.path.exists(context_file) else (legacy_context if os.path.exists(legacy_context) else context_file)

    # Docs directory
    doc_items = []
    if os.path.exists(docs_dir):
        files = sorted([f for f in os.listdir(docs_dir) if f.endswith(".md")])
        for filename in files:
            filepath = os.path.join(docs_dir, filename)
            title = filename
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("# "):
                            title = line.replace("# ", "").strip()
                            break
            except Exception:
                pass
            
            m = re.match(r"^(\d+)_(.*)\.md$", filename)
            idx_str = m.group(1) if m else "-"
            doc_items.append({
                "index": idx_str,
                "filename": filename,
                "title": title,
                "path": filepath,
            })

    return {
        "memory_dir": mem_dir,
        "coding_preferences": {
            "exists": has_prefs,
            "path": actual_pref_path,
        },
        "project_context": {
            "exists": has_context,
            "path": actual_context_path,
        },
        "docs": doc_items,
        "total_docs": len(doc_items),
    }


def read_memory_doc(identifier: str, target_dir: str = ".") -> Optional[Dict[str, Any]]:
    """Retrieves content of a specific memory document by name, alias, or sequential index."""
    mem_dir = get_memory_dir(target_dir)
    docs_dir = get_memory_docs_dir(target_dir)
    clean_id = identifier.strip().lower()

    if clean_id in ["coding_preferences", "preferences", "style", "coding_preferences.md", "00_coding_preferences.md"]:
        for cand in ["coding_preferences.md", "00_coding_preferences.md"]:
            p = os.path.join(mem_dir, cand)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return {"filename": cand, "path": p, "content": f.read()}

    if clean_id in ["project_context", "context", "project_context.md", "00_project_context.md"]:
        for cand in ["project_context.md", "00_project_context.md"]:
            p = os.path.join(mem_dir, cand)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return {"filename": cand, "path": p, "content": f.read()}

    # Check in docs directory
    if os.path.exists(docs_dir):
        files = sorted([f for f in os.listdir(docs_dir) if f.endswith(".md")])
        for filename in files:
            if clean_id in filename.lower() or clean_id == filename.replace(".md", ""):
                p = os.path.join(docs_dir, filename)
                with open(p, "r", encoding="utf-8") as f:
                    return {"filename": filename, "path": p, "content": f.read()}

    return None
