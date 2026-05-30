"""Shared formatting utilities for discussion logs and artifacts."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def get_sender_label(sender_type: str, sender_id: Optional[str]) -> str:
    """Get human-readable label for a message sender.
    
    Args:
        sender_type: Type of sender (orchestrator, expert, system, etc.)
        sender_id: Optional ID of the sender (used for expert labels)
        
    Returns:
        Human-readable sender label string
    """
    if sender_type == "orchestrator":
        return "主持人"
    elif sender_type == "expert":
        return f"专家 ({sender_id})"
    elif sender_type == "system":
        return "系统"
    else:
        return sender_type


def build_discussion_markdown(
    room_name: str,
    goal: str,
    messages: List[Dict[str, Any]],
    include_summary: bool = False,
) -> str:
    """Build formatted Markdown content for discussion messages.
    
    Args:
        room_name: Name of the discussion room
        goal: Discussion goal/objective
        messages: List of message dicts with keys: sender_type, sender_id, content, round
        include_summary: Whether to append a statistics summary section
        
    Returns:
        Formatted Markdown string
    """
    lines: List[str] = []
    lines.append(f"# {room_name}")
    lines.append("")
    lines.append(f"**目标**: {goal}")
    lines.append("")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"*生成时间: {now}*")
    lines.append("")
    lines.append("---")
    lines.append("")

    rounds: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for msg in messages:
        rounds[msg["round"]].append(msg)

    for round_num in sorted(rounds.keys()):
        lines.append(f"## Round {round_num}")
        lines.append("")
        for msg in rounds[round_num]:
            sender_label = get_sender_label(
                msg["sender_type"], msg.get("sender_id")
            )
            lines.append(f"**{sender_label}**: {msg['content']}")
            lines.append("")
        lines.append("---")
        lines.append("")

    if include_summary:
        summary = build_summary(messages)
        lines.append("## 统计摘要")
        lines.append("")
        lines.append(summary)

    return "\n".join(lines)


def build_summary(messages: List[Dict[str, Any]]) -> str:
    """Build a statistics summary string for a list of messages.
    
    Args:
        messages: List of message dicts with keys: round, sender_type, sender_id
        
    Returns:
        Summary string with message count, round count, and expert count
    """
    round_count = len({m["round"] for m in messages})
    expert_count = len({m.get("sender_id") for m in messages if m["sender_type"] == "expert"})
    return f"共 {len(messages)} 条消息，{round_count} 轮讨论，{expert_count} 位专家参与"


__all__ = [
    "get_sender_label",
    "build_discussion_markdown",
    "build_summary",
]
