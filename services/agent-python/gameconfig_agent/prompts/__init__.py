"""Prompt template loading."""

from pathlib import Path


def load_prompt(name: str) -> str:
    path = Path(__file__).with_name(f"{name}.md")
    return path.read_text(encoding="utf-8")
