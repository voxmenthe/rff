"""Game24 ProblemSpec implementation.
Enhanced to robustly evaluate expressions, track original number usage, and verify
24-Game solutions.
"""

from __future__ import annotations

import ast
import json
import operator
import re
import textwrap
import uuid
from collections import Counter
from typing import Any, Dict, List, Set, Tuple

from ..core import ProblemSpec, Workspace

__all__ = ["Game24Spec"]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
_ALLOWED_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


class _SafeEval(ast.NodeVisitor):
    """Safely evaluates arithmetic expressions containing +, -, *, / and parentheses."""

    def visit(self, node: ast.AST):  # type: ignore[override]
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self.visit(node.operand)
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN_OPS:
            left = self.visit(node.left)
            right = self.visit(node.right)
            return _ALLOWED_BIN_OPS[type(node.op)](left, right)
        raise ValueError("Unsafe or unsupported expression component encountered.")


def safe_eval(expr: str) -> float:
    """Evaluates `expr` safely with basic arithmetic support."""
    tree = ast.parse(expr, mode="eval")
    return _SafeEval().visit(tree)


_INT_RE = re.compile(r"\b\d+\b")


# ---------------------------------------------------------------------------
# Game24Spec implementation
# ---------------------------------------------------------------------------
class Game24Spec(ProblemSpec):
    """ProblemSpec for the 24-Game.

    The spec keeps a workspace of expressions; each entry is a dict::
        {"expr": "(11-1)*3-6", "value": 24.0, "nums": [11, 1, 3, 6]}
    """

    TARGET_VALUE = 24.0

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    def __init__(self, nums: List[int]):
        super().__init__()
        self.original_nums: List[int] = list(nums)
        self._orig_counter: Counter[int] = Counter(nums)

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    def _extract_numbers(self, expr: str) -> List[int]:
        return [int(n) for n in _INT_RE.findall(expr)]

    def _used_counter(self, state: Workspace) -> Counter[int]:
        cnt: Counter[int] = Counter()
        for item in state.values():
            if isinstance(item, dict):
                cnt.update(item.get("nums", []))
        return cnt

    def _available_counter(self, state: Workspace) -> Counter[int]:
        return self._orig_counter - self._used_counter(state)

    # ------------------------------------------------------------------
    # Backward-reasoning helpers (interface to core engine)
    # ------------------------------------------------------------------
    def parse_target_step(self, raw_text: str) -> str:  # noqa: D401
        """Return expression string for the micro-goal.

        Accepts either an arithmetic expression or an equation ``expr = value``.
        For equations we return the *expression* portion so that prompts remain
        consistent downstream.
        """
        raw = raw_text.strip()
        if "=" in raw:
            left, _ = raw.split("=", 1)
            return left.strip()
        return raw

    def check_local(self, state: Workspace, target_step: str) -> bool:
        """Check if *value* of `target_step` exists in workspace."""
        try:
            target_val = safe_eval(target_step)
        except Exception:
            return False
        for item in state.values():
            if isinstance(item, dict) and abs(item.get("value", 1e9) - target_val) < 1e-9:
                return True
        return False

    def verify_final(self, state: Workspace) -> Tuple[bool, str, float]:
        """Success when a workspace expression equals TARGET_VALUE and uses all numbers."""
        for item in state.values():
            if not isinstance(item, dict):
                continue
            # Check if the item's value is close to the target value
            if abs(item.get("value", 0.0) - self.TARGET_VALUE) > 1e-9:
                continue
            # Check if all original numbers were used exactly once
            if Counter(item.get("nums", [])) == self._orig_counter:
                return True, item["expr"], self.TARGET_VALUE
        return False, "", self.TARGET_VALUE

    # ------------------------------------------------------------------
    # Forward update parsing (LLM output → workspace)
    # ------------------------------------------------------------------
    def parse_workspace_update(self, raw_text: str, state: Workspace) -> Workspace:  # noqa: C901
        expr_line = raw_text.strip()
        if expr_line == "CANNOT_ACHIEVE_WITH_AVAILABLE_NUMBERS":
            return Workspace()
        if not expr_line:
            return Workspace()

        # Handle lines like "(3+1)*6 = 24" by stripping RHS if present.
        if "=" in expr_line:
            expr_part, _ = expr_line.split("=", 1)
            expr_line = expr_part.strip()

        # Basic hygiene – remove trailing semicolon or period.
        expr_line = expr_line.rstrip(";.")

        # Evaluate expression.
        try:
            value = safe_eval(expr_line)
        except Exception:
            return Workspace()  # Invalid expression

        nums_in_expr = self._extract_numbers(expr_line)
        avail_counter = self._available_counter(state)

        # Ensure the expression uses a subset (multiset) of available numbers.
        if not all(avail_counter[n] >= c for n, c in Counter(nums_in_expr).items()):
            return Workspace()

        # Valid – add to workspace.
        key = str(uuid.uuid4())
        entry: Dict[str, Any] = {
            "expr": expr_line,
            "value": value,
            "nums": nums_in_expr,
        }
        return Workspace({key: entry})

    # ------------------------------------------------------------------
    # Prompt helpers
    # ------------------------------------------------------------------
    def _serialisable_state(self, state: Workspace) -> List[Any]:
        """Convert state values into JSON-serialisable list."""
        out = []
        for v in state.values():
            if isinstance(v, (str, int, float, list, bool, type(None))):
                out.append(v)
            elif isinstance(v, dict):
                out.append(v)
            else:
                out.append(str(v))
        return out

    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str:
        # Show available numbers for context.
        available = list(self._available_counter(state).elements())
        prompt = textwrap.dedent(
            f"""
            You are a strategic mathematician playing the 24-Game.
            Original numbers: {self.original_nums}
            Numbers still available and that need to be used to reach 24: {available}
            Current expressions in workspace:
            {json.dumps(self._serialisable_state(state), indent=2)}

            Goal: Using each original number exactly once (and using all four numbers overall), reach the target value of 24.
            Avoid repeating expressions already present or any in this list: {sorted(list(avoid)) if avoid else '[]'}.

            Provide a single arithmetic expression that either:
              • Directly equals 24 using all the available numbers, or
              • Uses some of the numbers to produce a helpful intermediate value that will usually not be 24, but that can be combined with other expressions from the remaining numbers to eventually reach 24.

            Output ONLY the expression (no explanation, no equation form with '=').
            """
        ).strip()
        return prompt

    def prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]) -> str:
        available = list(self._available_counter(state).elements())
        # Evaluate target for clarity if possible.
        try:
            target_val = safe_eval(target_step)
            target_desc = f"{target_step} (≈ {target_val})"
        except Exception:
            target_desc = target_step

        prompt = textwrap.dedent(
            f"""
            You are trying to solve the 24-Game using the original numbers: {self.original_nums}.
            The overall goal is to create a single expression that evaluates to 24 and uses each of the original numbers exactly once.

            Current state:
            - Numbers still available for use in a NEW expression: {available}
            - Existing expressions in workspace (these numbers are already used):
            {json.dumps(self._serialisable_state(state), indent=2)}

            Your current micro-goal is to write a NEW arithmetic expression that evaluates to {target_desc}.
            This NEW expression MUST:
            1. Evaluate to {target_desc}.
            2. Use ONLY a subset of the 'Numbers still available for use': {available}.
            3. NOT use any numbers already consumed by 'Existing expressions in workspace'.

            Output ONLY the NEW arithmetic expression. Do not include explanations or the '=' sign.
            If the micro-goal {target_desc} cannot be achieved using ONLY the available numbers {available}, output the phrase 'CANNOT_ACHIEVE_WITH_AVAILABLE_NUMBERS'.
            """
        ).strip()
        return prompt

    # ------------------------------------------------------------------
    # Aliasing – not used but keep stub for interface compliance
    # ------------------------------------------------------------------
    def merge_aliases(self, state: Workspace) -> Workspace:  # noqa: D401
        return state

    # ------------------------------------------------------------------
    # Misc overrides required by core interface
    # ------------------------------------------------------------------
    def derive_final_target(self, problem: str) -> str:  # noqa: D401
        return "24"  # constant for 24-Game
