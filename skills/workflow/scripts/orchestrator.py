"""Hybrid Orchestrator: dispatches AI Subagents across Antigravity, Claude Code, and generic CLIs."""

import os
from typing import Dict, Any, Optional


def get_archetype_prompt(archetype: str) -> str:
    """Reads archetype system prompt from references/prompts/."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_dir = os.path.abspath(os.path.join(script_dir, "..", "references", "prompts"))
    prompt_file = os.path.join(prompts_dir, f"{archetype}.prompt.md")
    
    if os.path.exists(prompt_file):
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    return f"You are the {archetype} archetype specialist for workflow executions."


def prepare_subagent_dispatch(
    daemon_name: str,
    archetype: str,
    worktree_path: str,
    spec_dir: str
) -> Dict[str, Any]:
    """Generates the subagent configuration payload for AI agent dispatching."""
    system_prompt = get_archetype_prompt(archetype)
    return {
        "runner": "subagent",
        "subagent_name": f"workflow-{daemon_name}",
        "role": f"{archetype.capitalize()} Specialist",
        "system_prompt": system_prompt,
        "working_directory": worktree_path,
        "spec_directory": spec_dir,
        "task_prompt": (
            f"Execute the {archetype} workflow for spec at '{spec_dir}'. "
            f"Operate strictly within physical worktree at '{worktree_path}'. "
            f"Follow the TDD cycle (RED -> GREEN -> REFACTOR) and record decisions in .workflow/memory/{archetype}/."
        ),
    }


def generate_subagent_directive(
    daemon_name: str,
    archetype: str,
    worktree_path: str,
    cron_expression: str = "*/10 * * * *",
    interval_minutes: int = 10
) -> Dict[str, Any]:
    """Builds the Universal SUBAGENT_DISPATCH_DIRECTIVE for AI coding assistants."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_file = os.path.join(script_dir, "..", "references", "prompts", f"{archetype}.prompt.md")
    
    return {
        "action": "INVOKE_SUBAGENT",
        "role": f"{daemon_name.title()} Specialist",
        "working_directory": worktree_path,
        "system_prompt_file": prompts_file,
        "schedule": {
            "type": "recurring_cron",
            "cron_expression": cron_expression,
            "interval_minutes": interval_minutes,
        },
        "task_prompt": (
            f"Execute background cycle for '{daemon_name}' ({archetype}) "
            f"inside isolated Git Worktree at '{worktree_path}'. "
            f"Inspect .workflow/specs/ for active tasks, "
            f"run TDD cycle (RED -> GREEN -> REFACTOR), ensure 100% test pass, and record ADRs."
        ),
    }
