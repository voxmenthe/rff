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
    def verify_final(self, state: Workspace) -> Tuple[bool, str, float]:
        """Verify final state correctness. Returns (is_correct, llm_answer_str, gold_answer_float)."""

    @abstractmethod
    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str:
        """Build reverse-planning prompt to propose next micro-goal."""

    @abstractmethod
    def prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]) -> str:
        """Build forward-step prompt to satisfy the micro-goal."""

    @abstractmethod
    def parse_target_step(self, raw_text: str) -> str:
        """Parse raw LLM output from backward reasoning to get the next target variable name."""


# Controller
def reason_from_future(
    problem: str,
    spec: ProblemSpec,
    *,
    max_iters: int = 16,
    model: str = "gemini-2.5-flash-preview-05-20",
    verbose: bool = False,
) -> str:
    """Run an RFF loop until solved or *max_iters* exceeded.

    The old implementation updated `target` to be the *prerequisite* variable
    returned by the model each iteration.  This caused the search to walk
    backwards forever (cycling through synonyms) and *never* come back to the
    original goal (``final_answer``).  We now:

    1. Fix a constant ``goal`` representing the ultimate answer the user cares
       about.
    2. At the start of every iteration first check whether the goal is already
       present and, if so, verify and return it.
    3. Otherwise ask the model for **one** prerequisite symbol needed before
       the goal, request its value, validate it and store it.
    4. Add every successfully‐computed symbol to an ``avoid`` set so the model
       will not propose it again.
    """
    state: Workspace = Workspace()
    goal: str = spec.derive_final_target(problem)  # Remains constant.
    avoid: Set[str] = set()

    for _ in range(max_iters):
        # 1) If we already have the goal, try to verify and finish.
        if spec.check_local(state, goal):
            ok, answer_from_llm, gold_val_for_debug = spec.verify_final(state)
            if ok:
                return answer_from_llm
            # If goal was present but incorrect, it will be added to avoid list later if not already.
            # This initial check is just to see if we already have the correct answer without an LLM call this iteration.
            # Wrong value present – blacklist and remove so we can try again.
            avoid.add(goal)

        # 1b) Try computing the goal directly with current knowledge (fast-fail)
        if goal not in avoid:
            direct_prompt = spec.prompt_forward_step(state, goal, avoid)
            direct_raw = llm_call(direct_prompt, model=model, verbose=verbose)
            direct_state = state | spec.parse_workspace_update(direct_raw)
            if spec.check_local(direct_state, goal):
                ok, answer_from_llm, gold_val_for_debug = spec.verify_final(direct_state)
                if ok:
                    return answer_from_llm
                elif verbose: # Only print if verbose is on
                    print(f"INFO (direct attempt): LLM proposed final_answer='{answer_from_llm}', but gold_answer='{gold_val_for_debug}'. Adding to avoid list.")
            # Either not present or wrong – continue searching but keep any new
            # facts the model might have provided (besides a wrong goal).
            state = direct_state
            avoid.add(goal)

        # 2) Ask for the immediate prerequisite needed before we can compute
        #    the *goal* (not the previously returned prerequisite).
        g_prompt = spec.prompt_last_step(state, goal, avoid)
        raw_target_step_response = llm_call(g_prompt, model=model, verbose=verbose)
        target_step = spec.parse_target_step(raw_target_step_response)

        # 2a) Guard against the LLM returning something empty or already in
        #     avoid; if that happens, skip the iteration.
        if not target_step or target_step in avoid:
            continue

        # 3) Ask the model to *compute* that prerequisite.
        r_prompt = spec.prompt_forward_step(state, target_step, avoid)
        forward_raw = llm_call(r_prompt, model=model, verbose=verbose)
        parsed_update = spec.parse_workspace_update(forward_raw)

        # Determine what variable the LLM actually provided a value for.
        llm_provided_var = None
        if parsed_update: # Check if workspace is not empty
            llm_provided_var_keys = list(parsed_update.keys())
            if llm_provided_var_keys:
                llm_provided_var = llm_provided_var_keys[0]

        if llm_provided_var == goal:
            # LLM claims to have computed the GOAL variable.
            # This can happen if it was asked for target_step, but realized target_step IS the goal.
            temp_state_for_goal = state | parsed_update
            # LLM claims to have computed the GOAL variable.
            # We use 'parsed_update' directly for verification, as it contains the LLM's attempt for the goal.
            # We create a temporary state for verification that includes current state + the LLM's attempt.
            temp_state_for_verification = state | parsed_update
            if spec.check_local(temp_state_for_verification, goal): # Check if the goal var from LLM is in a valid format etc.
                ok, answer_from_llm, gold_val_for_debug = spec.verify_final(temp_state_for_verification) # Verify using the state that includes the LLM's goal value
                if ok:
                    return answer_from_llm # Solved!
                elif verbose: # Only print if verbose is on
                    print(f"INFO (after computing '{target_step}'): LLM proposed final_answer='{answer_from_llm}', but gold_answer='{gold_val_for_debug}'. Adding to avoid list.")
                else: # Goal computed, but verification failed
                    avoid.add(goal) # Avoid this incorrect goal value
                    # Also avoid the target_step that led to this incorrect goal, if different
                    if target_step != goal:
                        avoid.add(target_step)
                    # CRITICAL: Do not update 'state' with 'parsed_update' if it contained the incorrect goal.
                    # Since gsm8k.parse_workspace_update typically puts one var, parsed_update IS the incorrect goal.
                    # So, 'state' remains as it was before this attempt to compute 'goal' via 'target_step'.
                    continue
            else: # LLM provided goal var, but it failed check_local (e.g. wrong type, or not present in parsed_update)
                avoid.add(goal)
                if target_step != goal:
                    avoid.add(target_step)
                # 'state' also remains unchanged here.
                continue
        elif llm_provided_var == target_step:
            # LLM computed the intermediate variable (target_step) as requested.
            temp_state_for_target_step = state | parsed_update
            if spec.check_local(temp_state_for_target_step, target_step):
                state = temp_state_for_target_step # Commit the new intermediate state
                avoid.add(target_step)
                # Successfully added intermediate, loop to top to re-evaluate.
                # This allows the logic at the start of the loop (1 & 1b) to check if 'goal' is now computable.
            else: # check_local failed for the target_step
                avoid.add(target_step)
                # Don't update state if check_local failed for the target_step
                continue
        else:
            # LLM didn't provide 'goal' or 'target_step' in 'var', or provided nothing/malformed JSON.
            # This means the attempt to compute target_step effectively failed.
            avoid.add(target_step)
            # Don't update state as the response was not useful for target_step
            continue

    # If we exit the loop, we did not manage to find the correct answer.
    raise RuntimeError("RFF exhausted iterations without solution.")
