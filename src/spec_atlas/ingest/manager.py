"""Ingest job manager and ETA calculation.

Tracks phase durations and estimates time remaining for indexing jobs.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TypedDict

# Phase ordering and expected durations (in seconds) based on typical repos
# These are learning-based estimates; actual times vary by repo size
PHASE_ORDER = [
    "resolve",      # Git clone, ~10-40% of total
    "inventory",    # File scan, ~40-70% of total
    "languages",    # Language detection, ~70-75% of total
    "symbols",      # Symbol extraction, ~75-80% of total
    "edges",        # Edge extraction, ~80-85% of total
    "specs",        # Spec generation, ~85-88% of total
    "groups",       # Group clustering, ~88-92% of total
    "summarize",    # Group summaries & writing, ~92-96% of total
    "embed",        # Embedding creation, ~96-98% of total
    "spec_graph",   # Spec graph building, ~98-99% of total
    "drift",        # Drift detection, ~99-100% of total
]

# Progress boundaries for each phase (in percentage)
PHASE_PROGRESS = {
    "resolve": (10, 40),
    "inventory": (40, 70),
    "languages": (70, 75),
    "symbols": (75, 80),
    "edges": (80, 85),
    "specs": (85, 88),
    "groups": (88, 92),
    "summarize": (92, 96),
    "embed": (96, 98),
    "spec_graph": (98, 99),
    "drift": (99, 100),
}

# Default estimated durations (in seconds) for each phase if no history
DEFAULT_PHASE_DURATIONS = {
    "resolve": 30,
    "inventory": 20,
    "languages": 3,
    "symbols": 10,
    "edges": 10,
    "specs": 30,
    "groups": 15,
    "summarize": 30,
    "embed": 10,
    "spec_graph": 5,
    "drift": 5,
}


class ETAResult(TypedDict):
    """Result from ETA calculation."""

    eta_seconds: int
    show_warning: bool
    warning_message: str | None


def calculate_eta(
    current_progress_pct: int,
    phase_durations: dict[str, float] | None = None,
    phase_start_time: datetime | None = None,
    current_phase: str | None = None,
) -> ETAResult:
    """
    Calculate estimated time remaining for an ingest job.

    Args:
        current_progress_pct: Current progress (0-100)
        phase_durations: Dict of {phase_name: seconds_elapsed}
        phase_start_time: When the current phase started
        current_phase: Name of the current phase

    Returns:
        ETAResult with eta_seconds, show_warning, and warning_message
    """
    if not phase_durations:
        phase_durations = {}

    # If we're at 100%, no time remaining
    if current_progress_pct >= 100:
        return ETAResult(eta_seconds=0, show_warning=False, warning_message=None)

    # If we're just starting, return default estimate
    if current_progress_pct <= 10:
        total_estimated = sum(DEFAULT_PHASE_DURATIONS.values())
        warning = total_estimated > 120
        return ETAResult(
            eta_seconds=total_estimated,
            show_warning=warning,
            warning_message="Large repository may take longer than usual" if warning else None,
        )

    # Calculate time elapsed so far
    total_elapsed = sum(phase_durations.values()) if phase_durations else 0

    # If we have elapsed time data, use it to project remaining time
    if total_elapsed > 0:
        # Linear interpolation: if we've done X% of work in Y seconds,
        # we estimate total time = Y / (X/100)
        elapsed_for_pct = current_progress_pct / 100.0
        if elapsed_for_pct > 0:
            estimated_total_time = total_elapsed / elapsed_for_pct
            estimated_remaining = estimated_total_time - total_elapsed
            eta_seconds = max(0, int(estimated_remaining))

            warning = estimated_total_time > 120
            return ETAResult(
                eta_seconds=eta_seconds,
                show_warning=warning,
                warning_message="Large repository may take longer than usual" if warning else None,
            )

    # Fallback: use default phase durations weighted by progress
    total_estimated = sum(DEFAULT_PHASE_DURATIONS.values())

    # Find which phase we're in based on progress percentage
    current_phase_idx = 0
    for idx, (phase_name, (start_pct, end_pct)) in enumerate(PHASE_PROGRESS.items()):
        if start_pct <= current_progress_pct < end_pct:
            current_phase_idx = idx
            break

    # Sum remaining phase durations
    remaining_seconds = 0
    for idx in range(current_phase_idx, len(PHASE_ORDER)):
        phase = PHASE_ORDER[idx]
        remaining_seconds += DEFAULT_PHASE_DURATIONS.get(phase, 0)

    # Adjust for partial progress in current phase
    if current_phase_idx < len(PHASE_ORDER):
        phase = PHASE_ORDER[current_phase_idx]
        start_pct, end_pct = PHASE_PROGRESS.get(phase, (0, 100))
        phase_progress = (current_progress_pct - start_pct) / (end_pct - start_pct)
        phase_duration = DEFAULT_PHASE_DURATIONS.get(phase, 0)
        remaining_in_phase = phase_duration * (1.0 - max(0, min(1, phase_progress)))
        remaining_seconds = remaining_in_phase + sum(
            DEFAULT_PHASE_DURATIONS.get(PHASE_ORDER[i], 0)
            for i in range(current_phase_idx + 1, len(PHASE_ORDER))
        )

    eta_seconds = max(0, int(remaining_seconds))
    warning = total_estimated > 120
    return ETAResult(
        eta_seconds=eta_seconds,
        show_warning=warning,
        warning_message="Large repository may take longer than usual" if warning else None,
    )


def format_eta_display(eta_seconds: int | None) -> str:
    """Format ETA seconds into a human-readable string like 'X min Y sec remaining'."""
    if eta_seconds is None or eta_seconds <= 0:
        return "Almost done!"

    minutes = eta_seconds // 60
    seconds = eta_seconds % 60

    if minutes == 0:
        return f"{seconds} sec remaining"
    elif seconds == 0:
        return f"{minutes} min remaining"
    else:
        return f"{minutes} min {seconds} sec remaining"
