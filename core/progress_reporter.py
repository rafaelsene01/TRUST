"""Progress reporting for TRUST pipeline phases.

Provides a simple terminal progress bar and phase-level timing for phases
that take more than a few seconds. Falls back to plain text when the
terminal doesn't support ANSI codes (e.g. CI environments).

Usage:
    from core.progress_reporter import PhaseProgress, ProgressReporter

    reporter = ProgressReporter(verbose=True)

    with reporter.phase("Grounding", total_steps=7) as p:
        for doc in docs:
            p.step(f"Loading {doc.path}")
        # bar completes automatically on context exit

    reporter.summary()
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


# ---------------------------------------------------------------------------
# Terminal capability detection
# ---------------------------------------------------------------------------


def _supports_ansi() -> bool:
    """Return True if the terminal supports ANSI escape codes."""
    if not sys.stdout.isatty():
        return False
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return False
    if os.name == "nt":
        # Windows 10+ supports ANSI in conhost/Windows Terminal
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            # Enable VIRTUAL_TERMINAL_PROCESSING (0x0004)
            mode = ctypes.c_ulong()
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            return True
        except Exception:
            return False
    return True


_ANSI = _supports_ansi()
_BOLD = "\033[1m" if _ANSI else ""
_DIM = "\033[2m" if _ANSI else ""
_GREEN = "\033[32m" if _ANSI else ""
_YELLOW = "\033[33m" if _ANSI else ""
_RED = "\033[31m" if _ANSI else ""
_CYAN = "\033[36m" if _ANSI else ""
_RESET = "\033[0m" if _ANSI else ""
_CLEAR_LINE = "\r\033[K" if _ANSI else "\n"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class PhaseRecord:
    name: str
    started_at: float
    finished_at: float | None = None
    steps_done: int = 0
    steps_total: int = 0
    status: str = "running"  # "running" | "done" | "halted" | "skipped"
    last_message: str = ""
    elapsed_s: float = field(init=False, default=0.0)

    def finish(self, status: str = "done") -> None:
        self.finished_at = time.monotonic()
        self.elapsed_s = self.finished_at - self.started_at
        self.status = status


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------


_BAR_WIDTH = 24


def _render_bar(done: int, total: int) -> str:
    if total <= 0:
        filled = _BAR_WIDTH
        return f"[{'█' * filled}]"
    ratio = min(done / total, 1.0)
    filled = int(_BAR_WIDTH * ratio)
    empty = _BAR_WIDTH - filled
    return f"[{'█' * filled}{'░' * empty}]"


def _elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    return f"{int(seconds // 60)}m{int(seconds % 60):02d}s"


# ---------------------------------------------------------------------------
# PhaseProgress context
# ---------------------------------------------------------------------------


class PhaseProgress:
    """In-progress phase. Use as a context manager."""

    def __init__(
        self,
        name: str,
        total_steps: int,
        reporter: "ProgressReporter",
        record: PhaseRecord,
    ):
        self.name = name
        self.total_steps = total_steps
        self._reporter = reporter
        self._record = record

    def step(self, message: str = "") -> None:
        """Advance by one step and optionally update the status message."""
        self._record.steps_done += 1
        self._record.last_message = message
        self._reporter._render(self._record)

    def message(self, text: str) -> None:
        """Update the status message without advancing the step counter."""
        self._record.last_message = text
        self._reporter._render(self._record)

    def __enter__(self) -> "PhaseProgress":
        self._reporter._render(self._record)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self._record.finish("halted")
        else:
            self._record.steps_done = self._record.steps_total
            self._record.finish("done")
        self._reporter._render_final(self._record)


# ---------------------------------------------------------------------------
# ProgressReporter
# ---------------------------------------------------------------------------


class ProgressReporter:
    """Manages progress reporting for the TRUST pipeline.

    Args:
        verbose:    If True, show detailed per-step messages.
        min_phase_s: Phases faster than this (in seconds) don't show a bar.
    """

    def __init__(self, verbose: bool = False, min_phase_s: float = 1.0):
        self.verbose = verbose
        self.min_phase_s = min_phase_s
        self._phases: list[PhaseRecord] = []
        self._pipeline_start = time.monotonic()

    @contextmanager
    def phase(self, name: str, total_steps: int = 0) -> Iterator[PhaseProgress]:
        """Context manager for a pipeline phase.

        Args:
            name:        Phase name shown in the progress output.
            total_steps: Number of discrete steps (0 = indeterminate).

        Yields:
            PhaseProgress — call .step() and .message() inside the block.
        """
        record = PhaseRecord(
            name=name,
            started_at=time.monotonic(),
            steps_total=total_steps,
        )
        self._phases.append(record)
        progress = PhaseProgress(name, total_steps, self, record)

        with progress:
            yield progress

    def _render(self, record: PhaseRecord) -> None:
        elapsed = time.monotonic() - record.started_at
        if elapsed < self.min_phase_s and not self.verbose:
            return

        if record.steps_total > 0:
            bar = _render_bar(record.steps_done, record.steps_total)
            pct = f"{int(100 * record.steps_done / record.steps_total):3d}%"
            msg = f"  {_CYAN}{record.name}{_RESET} {bar} {pct}"
        else:
            spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[int(elapsed * 8) % 10]
            msg = f"  {_CYAN}{record.name}{_RESET} {spinner} {_elapsed(elapsed)}"

        if record.last_message and self.verbose:
            msg += f"  {_DIM}{record.last_message[:60]}{_RESET}"

        if _ANSI:
            sys.stdout.write(f"{_CLEAR_LINE}{msg}")
            sys.stdout.flush()
        else:
            if self.verbose:
                print(msg)

    def _render_final(self, record: PhaseRecord) -> None:
        elapsed = record.elapsed_s
        icon = {
            "done": f"{_GREEN}✅{_RESET}",
            "halted": f"{_RED}🛑{_RESET}",
            "skipped": f"{_DIM}⏭{_RESET}",
        }.get(record.status, "?")

        if record.steps_total > 0:
            steps_info = f"{record.steps_done}/{record.steps_total} steps"
        else:
            steps_info = ""

        elapsed_info = _elapsed(elapsed)
        timing = f"{_DIM}({elapsed_info}){_RESET}" if elapsed >= self.min_phase_s else ""

        parts = [f"  {icon} {_BOLD}{record.name}{_RESET}"]
        if steps_info:
            parts.append(steps_info)
        if timing:
            parts.append(timing)

        line = "  ".join(parts)
        if _ANSI:
            sys.stdout.write(f"{_CLEAR_LINE}{line}\n")
        else:
            print(line)
        sys.stdout.flush()

    def skip_phase(self, name: str, reason: str = "") -> None:
        """Record a skipped phase (e.g. traceability disabled)."""
        record = PhaseRecord(
            name=name,
            started_at=time.monotonic(),
        )
        record.finish("skipped")
        record.last_message = reason
        self._phases.append(record)
        self._render_final(record)

    def halt(self, phase_name: str, reason: str) -> None:
        """Print a HALT banner."""
        print(
            f"\n{_RED}{_BOLD}🛑 HALT — {phase_name}{_RESET}\n"
            f"   {reason}\n"
            f"   {_DIM}Next action: check the .trust-halt file in the run directory.{_RESET}\n"
        )

    def error(self, message: str, next_action: str = "") -> None:
        """Print an error with an optional next-action hint."""
        print(f"\n{_RED}✗ {message}{_RESET}")
        if next_action:
            print(f"  {_YELLOW}→ {next_action}{_RESET}")

    def info(self, message: str) -> None:
        """Print an informational message."""
        print(f"  {_DIM}{message}{_RESET}")

    def success(self, message: str) -> None:
        """Print a success message."""
        print(f"  {_GREEN}✓ {message}{_RESET}")

    def summary(self) -> None:
        """Print a summary table of all phases."""
        total = time.monotonic() - self._pipeline_start
        done = sum(1 for p in self._phases if p.status == "done")
        halted = sum(1 for p in self._phases if p.status == "halted")
        skipped = sum(1 for p in self._phases if p.status == "skipped")

        print(f"\n{_BOLD}Pipeline summary:{_RESET}")
        print(f"  {done} done · {skipped} skipped · {halted} halted · {_elapsed(total)} total\n")

        if self.verbose:
            for p in self._phases:
                icon = {"done": "✅", "halted": "🛑", "skipped": "⏭"}.get(p.status, "?")
                timing = f"({_elapsed(p.elapsed_s)})" if p.elapsed_s > 0 else ""
                print(f"    {icon} {p.name:<24} {timing}")
            print()
