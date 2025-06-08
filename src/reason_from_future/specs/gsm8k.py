"""GSM8K ProblemSpec implementation."""
import json
from typing import Set, Tuple

from ..core import Workspace, ProblemSpec


class GSM8KSpec(ProblemSpec):
    """*Extremely* simplified demo – not suitable for real GSM8K eval."""

    def derive_final_target(self, problem: str) -> str:
        return "numeric_answer"

    def parse_workspace_update(self, raw_text: str) -> Workspace:
        """Expect a JSON line like {"var": "x", "value": 123}."""
        try:
            data = json.loads(raw_text)
            return Workspace({data["var"]: data["value"]})
        except Exception:
            return Workspace()

    def check_local(self, state: Workspace, target_step: str) -> bool:
        return target_step in state

    def verify_final(self, state: Workspace) -> Tuple[bool, str]:
        guess = state.get("answer")
        return isinstance(guess, (int, float)), str(guess)

    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str:
        return (
            "You are reasoning backward through a math word problem.\n"
            "Known facts so far:\n" + json.dumps(state, indent=2) + "\n\n"
            f"What single sub-result must be computed immediately before the final answer?\n"
            f"Return just the variable name. Avoid: {list(avoid)}"
        )

    def prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]) -> str:
        return (
            "Given the problem context and known facts, compute the value for \""
            f"{target_step}\" and output JSON {{ \"var\": \"...\", \"value\": ... }}.\n"
            "Context: [problem_context_stub]\n"
            "Known facts:\n" + json.dumps(state, indent=2)
        )
