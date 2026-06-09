"""
Token counting and budget management utilities for Expert Room.

Provides heuristic token estimation and budget enforcement for building
prompts in multi-expert discussion contexts. Used by ContextBuilder to
manage token budgets when constructing LLM prompts.
"""

from dataclasses import dataclass


@dataclass
class TokenBudget:
    """Budget allocations for a discussion context, in tokens.

    Default total is 12000 tokens. Each sub-budget reserves capacity for
    a specific part of the prompt assembly pipeline.
    """

    total: int = 12000
    system_prompt: int = 1500
    context_summary: int = 2000
    shared_data: int = 2000
    expert_memory: int = 2000
    current_turn: int = 2000
    output_reserve: int = 1500
    safety_margin: int = 1000

    @property
    def allocated(self) -> int:
        """Sum of all sub-budget allocations."""
        return (
            self.system_prompt
            + self.context_summary
            + self.shared_data
            + self.expert_memory
            + self.current_turn
            + self.output_reserve
            + self.safety_margin
        )

    @property
    def remaining(self) -> int:
        """Tokens not yet allocated to a sub-budget."""
        return self.total - self.allocated


# Degradation sequence: ordered actions when token budget is exceeded.
# Each entry is (threshold_pct, action, description).
# threshold_pct is the percentage of budget used at which this action kicks in.
DEGRADATION_SEQUENCE: list[tuple[int, str, str]] = [
    (80, "compress_context", "Compress context summary to key points"),
    (85, "trim_shared_data", "Remove low-relevance shared data snippets"),
    (90, "reduce_expert_memory", "Trim older expert memory entries"),
    (95, "truncate_current_turn", "Truncate current turn context"),
    (100, "force_summarize", "Force full summarization, drop raw content"),
]

# Token estimation constants
TOKEN_ESTIMATES: dict = {
    # Average tokens per character for different languages
    "chinese_chars_per_token": 2.0,  # ~2 Chinese characters per token
    "english_chars_per_token": 4.0,  # ~4 English characters per token
    # Overhead per message in a conversation (role, formatting, etc.)
    "message_overhead_tokens": 4,
    # System prompt fixed overhead
    "system_overhead_tokens": 50,
    # Per-round overhead for orchestration instructions
    "round_overhead_tokens": 100,
    # Per-expert overhead for role identification
    "expert_overhead_tokens": 30,
    # Average tokens per line of code
    "code_line_tokens": 8,
    # Average tokens per line of plain text
    "text_line_tokens": 12,
}


def estimate_tokens(text: str) -> int:
    """Estimate token count for a mixed Chinese/English text string.

    Uses a rough heuristic:
    - Chinese characters: ~2 chars per token
    - English (ASCII) characters: ~4 chars per token
    - Adds a small buffer for punctuation and whitespace.

    Args:
        text: The input text to estimate.

    Returns:
        Estimated number of tokens.
    """
    if not text:
        return 0

    chinese_chars = 0
    english_chars = 0

    for ch in text:
        if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf":
            # CJK Unified Ideographs range
            chinese_chars += 1
        elif ch.isascii() and ch.isalpha():
            english_chars += 1
        # Punctuation, digits, whitespace counted as english for simplicity
        else:
            english_chars += 1

    chinese_tokens = chinese_chars / TOKEN_ESTIMATES["chinese_chars_per_token"]
    english_tokens = english_chars / TOKEN_ESTIMATES["english_chars_per_token"]

    return int(chinese_tokens + english_tokens + 0.5)


def estimate_round_tokens(round_number: int, expert_count: int) -> int:
    """Estimate token usage for a single discussion round.

    Each round includes:
    - Orchestration instruction overhead
    - Per-expert contribution (question prompt + response)
    - Message formatting overhead per expert

    Args:
        round_number: Current round number (1-indexed).
        expert_count: Number of experts participating.

    Returns:
        Estimated tokens for this round.
    """
    base = TOKEN_ESTIMATES["round_overhead_tokens"]
    per_expert = (
        TOKEN_ESTIMATES["expert_overhead_tokens"] + TOKEN_ESTIMATES["message_overhead_tokens"] * 2
    )
    # Later rounds may reference more history, add a small ramp
    round_multiplier = 1.0 + (round_number - 1) * 0.05

    return int((base + per_expert * expert_count) * round_multiplier)


def estimate_total_tokens(rounds: int, expert_count: int) -> int:
    """Estimate total token usage across all discussion rounds.

    Sums per-round estimates for rounds 1..rounds.

    Args:
        rounds: Total number of discussion rounds.
        expert_count: Number of experts participating.

    Returns:
        Estimated total tokens for the full discussion.
    """
    return sum(estimate_round_tokens(r, expert_count) for r in range(1, rounds + 1))


def check_budget(current_tokens: int, budget: TokenBudget) -> dict:
    """Check current token usage against the budget.

    Args:
        current_tokens: Tokens currently consumed.
        budget: The TokenBudget to check against.

    Returns:
        Dict with:
            - within_budget: bool
            - usage_pct: float (percentage of budget used)
            - remaining: int (tokens left)
            - overage: int (tokens over budget, 0 if within)
    """
    usage_pct = (current_tokens / budget.total * 100) if budget.total > 0 else 0
    remaining = budget.total - current_tokens

    return {
        "within_budget": current_tokens <= budget.total,
        "usage_pct": round(usage_pct, 1),
        "remaining": max(0, remaining),
        "overage": max(0, current_tokens - budget.total),
    }


def get_degradation_action(current_tokens: int, budget: TokenBudget) -> tuple[str, str] | None:
    """Determine the appropriate degradation action for current token usage.

    Walks the DEGRADATION_SEQUENCE from highest threshold down and returns
    the first action whose threshold is met or exceeded.

    Args:
        current_tokens: Tokens currently consumed.
        budget: The TokenBudget to check against.

    Returns:
        Tuple of (action_name, description) if degradation is needed,
        None if within budget.
    """
    if budget.total <= 0:
        return None

    usage_pct = (current_tokens / budget.total) * 100

    # Walk from highest threshold to lowest so we pick the most severe action
    for threshold, action, description in reversed(DEGRADATION_SEQUENCE):
        if usage_pct >= threshold:
            return (action, description)

    return None
