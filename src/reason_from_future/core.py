"""Core abstractions for Reason-from-Future."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Tuple, Set
from .llm import llm_call


class Workspace(dict):
    """Scratch-pad for intermediate facts and states."""

    def add(self, key: str, val: Any) -> None:
        self[key] = val


class LocalCheckFail(Exception):
    """Raised when a forward hop fails local validation."""


class ProblemSpec(ABC):
    """Contract that each reasoning domain must fulfill."""

    @abstractmethod
    def derive_final_target(self, problem: str) -> str:
        """Return symbolic representation of the ultimate goal."""

    @abstractmethod
    def parse_workspace_update(self, raw_text: str) -> Workspace:
        """Parse raw LLM output into structured Workspace entries."""

    @abstractmethod
    def check_local(self, state: Workspace, target_step: str) -> bool:
        """Deterministic check that a forward step satisfies the micro-goal."""

    @abstractmethod
    def verify_final(self, state: Workspace) -> Tuple[bool, str]:
        """Verify final state correctness and return formatted answer."""

    @abstractmethod
    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str:
        """Build reverse-planning prompt to propose next micro-goal."""

    @abstractmethod
    def prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]) -> str:
        """Build forward-step prompt to satisfy the micro-goal."""


# Controller
def reason_from_future(
    problem: str,
    spec: ProblemSpec,
    *,
    max_iters: int = 16,
    model: str = "gemini-2.5-flash-preview-05-20",
    verbose: bool = False,
) -> str:
    """Run an RFF loop until solved or *max_iters* exceeded."""
    state: Workspace = Workspace()
    target: str = spec.derive_final_target(problem)
    avoid: Set[str] = set()

    for _ in range(max_iters):
        g_prompt = spec.prompt_last_step(state, target, avoid)
        target_step = llm_call(g_prompt, model=model, verbose=verbose).strip()

        r_prompt = spec.prompt_forward_step(state, target_step, avoid)
        forward_raw = llm_call(r_prompt, model=model, verbose=verbose)
        new_state = state | spec.parse_workspace_update(forward_raw)

        if not spec.check_local(new_state, target_step):
            avoid.add(target_step)
            continue

        if target_step == target:
            ok, answer = spec.verify_final(new_state)
            if ok:
                return answer
            avoid.add(target_step)
            continue

        state, target = new_state, target_step

    raise RuntimeError("RFF exhausted iterations without solution.")

