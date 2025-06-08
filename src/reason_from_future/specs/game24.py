"""Game24 ProblemSpec implementation."""
import json
import re
import textwrap
import uuid
from typing import List, Set, Tuple

from ..core import Workspace, ProblemSpec


class Game24Spec(ProblemSpec):
    """Toy domain: given 4 integers, compose ops to reach exactly 24."""

    OPS = {"+", "-", "*", "/"}

    def __init__(self, nums: List[int]):
        self.original_nums = nums
        self._re = re.compile(
            r"(?P<lhs>\d+)\s*(?P<op>[+\-*/])\s*(?P<rhs>\d+)\s*=\s*(?P<res>\d+)"
        )

    def derive_final_target(self, problem: str) -> str:
        return "24"

    def parse_workspace_update(self, raw_text: str) -> Workspace:
        """Expect lines such as `12 * 2 = 24`."""
        ws = Workspace()
        for m in self._re.finditer(raw_text):
            expr = f"{m['lhs']} {m['op']} {m['rhs']} = {m['res']}"
            ws[str(uuid.uuid4())] = expr
        return ws

    def check_local(self, state: Workspace, target_step: str) -> bool:
        m = self._re.search(target_step)
        if not m:
            return False
        return any(m["res"] in v for v in state.values())

    def verify_final(self, state: Workspace) -> Tuple[bool, str]:
        for expr in state.values():
            if expr.endswith("= 24"):
                return True, "24"
        return False, ""

    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str:
        return textwrap.dedent(
            f"""
            You are a strategic mathematician playing the 24-Game.
            Current expressions:
            {json.dumps(list(state.values()), indent=2)}
            Goal: reach exactly 24.
            Avoid: {list(avoid)}

            Propose a single equation a OP b = c that gets closer to 24.
            Output ONLY that equation.
            """
        ).strip()

    def prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]) -> str:
        return textwrap.dedent(
            f"""
            Numbers available: {self.original_nums}
            Existing workspace lines:
            {json.dumps(list(state.values()), indent=2)}

            Your micro-goal to achieve now is:
            {target_step}

            Write exactly one new arithmetic line that makes the micro-goal true.
            Only use each original number at most once in total.
            Output ONLY the new line.
            """
        ).strip()
