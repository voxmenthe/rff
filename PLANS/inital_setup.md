```python
###############################################################################
#  Reason-from-Future – Near-Executable Reference Implementation
#  ---------------------------------------------------------------------------
#  Goal: give you a *drop-in* scaffold that needs only:
#       • your own `llm_call()` wrapper
#       • one ProblemSpec subclass per domain (math, 24-game, path-finding …)
#
#  Design highlights
#  -----------------
#   1.  Controller is completely domain-agnostic → delegates semantics to
#       ProblemSpec (derive goal, parse updates, local / global checks …).
#   2.  Prompts are stored as Jinja-style f-strings for readability.
#   3.  Uses synchronous calls for clarity; in production convert to `async`.
###############################################################################

from __future__ import annotations
from typing import List, Dict, Set, Tuple, Optional, Any
from abc import ABC, abstractmethod
import re
import json
import textwrap
import uuid


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  0. Glue to the LLM endpoint                                             ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def llm_call(prompt: str,
             model: str = "gpt-4o",
             max_tokens: int = 256,
             temperature: float = 0.3) -> str:
    """
    Thin placeholder around your favourite SDK.
    In a real stack this would (a) stream tokens, (b) check usage quotas,
    (c) retry on 5xx.
    """
    raise NotImplementedError("hook up OpenAI / vLLM / LM Studio here")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  1. Domain abstractions                                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝
class Workspace(dict):
    """Scratch-pad that stores facts, expressions, partial paths, etc."""
    def add(self, key: str, val: Any) -> None:
        self[key] = val


class LocalCheckFail(Exception):
    """Raised when C() says the forward hop didn’t achieve target_step."""


class ProblemSpec(ABC):
    """
    Each concrete domain implements five contracts so the generic controller
    never needs to understand task semantics.
    """
    # ---------- extraction / parsing ----------
    @abstractmethod
    def derive_final_target(self, problem: str) -> str:
        ...

    @abstractmethod
    def parse_workspace_update(self, raw_text: str) -> Workspace:
        ...

    # ---------- validators ----------
    @abstractmethod
    def check_local(self, state: Workspace, target_step: str) -> bool:
        ...

    @abstractmethod
    def verify_final(self, state: Workspace) -> Tuple[bool, str]:
        """
        Returns (is_correct, formatted_answer).
        """

    # ---------- prompt builders ----------
    @abstractmethod
    def prompt_last_step(self, state: Workspace, target: str,
                         avoid: Set[str]) -> str:
        ...

    @abstractmethod
    def prompt_forward_step(self, state: Workspace, target_step: str,
                            avoid: Set[str]) -> str:
        ...


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  2. Controller (domain-agnostic)                                         ║
# ╚══════════════════════════════════════════════════════════════════════════╝
def reason_from_future(problem: str,
                       spec: ProblemSpec,
                       max_iters: int = 16,
                       model: str = "gpt-4o") -> str:
    """
    Main loop: (G → R → C)*  then V
    """
    state: Workspace = Workspace()
    target: str = spec.derive_final_target(problem)
    avoid: Set[str] = set()

    for step in range(max_iters):
        # 1 ▸ G()  – Reverse planner proposes one micro-goal
        g_prompt = spec.prompt_last_step(state, target, avoid)
        target_step = llm_call(g_prompt, model=model).strip()

        # 2 ▸ R()  – Forward hop tries to satisfy that micro-goal
        r_prompt = spec.prompt_forward_step(state, target_step, avoid)
        forward_raw = llm_call(r_prompt, model=model)
        new_state = state | spec.parse_workspace_update(forward_raw)  # merge

        # 3 ▸ C()  – Quick deterministic check
        if not spec.check_local(new_state, target_step):
            avoid.add(target_step)
            continue  # try a different proposal

        #     If target_step equals the ultimate goal, hand off to verifier
        if target_step == target:
            ok, answer = spec.verify_final(new_state)
            if ok:
                return answer
            else:
                avoid.add(target_step)
                continue

        #     Otherwise advance the frontier
        state, target = new_state, target_step

    raise RuntimeError("RFF exhausted iterations without solution.")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  3. Example ProblemSpec: 24-Game (integer arithmetic to reach 24)       ║
# ╚══════════════════════════════════════════════════════════════════════════╝
class Game24Spec(ProblemSpec):
    OPS = {"+", "-", "*", "/"}  # allowed binary ops

    def __init__(self, nums: List[int]):
        self.original_nums = nums

    # ----- Extraction -----
    def derive_final_target(self, problem: str) -> str:
        return "24"

    # ----- Parsing forward step -----
    _re_new_fact = re.compile(r"(?P<lhs>\d+)\s*(?P<op>[+\-*/])\s*(?P<rhs>\d+)\s*=\s*(?P<res>\d+)")

    def parse_workspace_update(self, raw_text: str) -> Workspace:
        """
        Expect lines like '12 * 2 = 24'.
        """
        ws = Workspace()
        for m in self._re_new_fact.finditer(raw_text):
            expr = f"{m['lhs']} {m['op']} {m['rhs']} = {m['res']}"
            ws[str(uuid.uuid4())] = expr
        return ws

    # ----- Validators -----
    def check_local(self, state: Workspace, target_step: str) -> bool:
        """
        Eg. target_step: '12 * 2 = 24 (left: 24)'
        Succeeds if the RHS equals the target RHS.
        """
        m = self._re_new_fact.search(target_step)
        if not m:
            return False
        return any(m['res'] in v for v in state.values())

    def verify_final(self, state: Workspace) -> Tuple[bool, str]:
        """
        Verifies that some equation in state exactly equals 24 on RHS.
        """
        for expr in state.values():
            if expr.endswith("= 24"):
                return True, "24"
        return False, ""

    # ----- Prompt builders -----
    def prompt_last_step(self, state: Workspace, target: str,
                         avoid: Set[str]) -> str:
        template = textwrap.dedent(f"""
        You are a strategic mathematician playing the Game of 24.
        Current expressions:
        {json.dumps(list(state.values()), indent=2)}
        Big goal: reach exactly 24.
        Avoid repeating these failed micro-targets:
        {list(avoid)}
        TASK: Propose a single arithmetic equation of the form
              a OP b = c
        such that c gets us *one step closer* to 24.
        Output *only* that equation.
        """)
        return template

    def prompt_forward_step(self, state: Workspace, target_step: str,
                            avoid: Set[str]) -> str:
        template = textwrap.dedent(f"""
        CONTEXT:
         Numbers available: {self.original_nums}
         Existing workspace lines:
        {json.dumps(list(state.values()), indent=2)}

        Your micro-goal to achieve now is:
        {target_step}

        Write exactly one new arithmetic line that makes the micro-goal true.
        Only use each original number at most once in total.
        Output ONLY the new line.
        """)
        return template


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  4. Example ProblemSpec: Math Word Problem (GSM8K-like)                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝
class GSM8KSpec(ProblemSpec):
    def derive_final_target(self, problem: str) -> str:
        # Use a dumb heuristic: capture last “?” sentence’s subject.
        return "numeric_answer"

    def parse_workspace_update(self, raw_text: str) -> Workspace:
        """
        Expect JSON lines like {"var":"swim_time","value":30}
        """
        try:
            data = json.loads(raw_text)
            return Workspace({data["var"]: data["value"]})
        except Exception:
            return Workspace()

    def check_local(self, state: Workspace, target_step: str) -> bool:
        """
        If target_step says we now know variable X, check it's now in workspace.
        """
        return target_step in state

    def verify_final(self, state: Workspace) -> Tuple[bool, str]:
        guess = state.get("answer")
        return (isinstance(guess, (int, float))), str(guess)

    # --- PROMPTS -----------------------------------------------------------
    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]):
        return f"""
You are reasoning backward through a math word problem.
Known facts so far:
{json.dumps(state, indent=2)}

What *single new sub-result* must be computed immediately before we can
compute the overall answer (“{target}”)?  Return just the variable name.
Avoid these: {list(avoid)}
""".strip()

    def prompt_forward_step(self, state: Workspace, target_step: str,
                            avoid: Set[str]):
        return f"""
Given the following problem context and known facts, compute the value for
\"{target_step}\" and output it as JSON {{ "var": "...", "value": ... }}.
Context:
{problem_context_stub}
Known facts:
{json.dumps(state, indent=2)}
""".strip()


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  5. Minimal demo run (mocked)                                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝
if __name__ == "__main__":
    # For illustration only – llm_call is NOT implemented.
    nums = [1, 3, 6, 11]
    spec = Game24Spec(nums)
    try:
        ans = reason_from_future("Reach 24 with numbers " + str(nums), spec)
        print("Solved:", ans)
    except NotImplementedError:
        print("Plug in your LLM backend first!  (llm_call)")
```

---

## How to Adapt This Skeleton

| Where to Touch               | What to Do                                                                                                                |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **`llm_call`**               | Swap in your async OpenAI SDK call or local vLLM runner.                                                                  |
| **`ProblemSpec` subclasses** | Create one per domain; fill the *five* abstract methods. Unit-test them in isolation before plugging into the controller. |
| **Prompt tone / style**      | Change the strings in `prompt_last_step` and `prompt_forward_step`. Keep them short (≤40 tokens) for RFF efficiency.      |
| **Local checks**             | Whenever possible make `check_local` deterministic Python (regex, `eval`, unit tests) – saves tokens.                     |
| **Verifier**                 | For strict domains (24-game, Sudoku) write pure-code verifiers; for open QA wrap a short LLM self-critique prompt.        |
| **Cost guardrails**          | Add `max_token_budget` and break if cumulative tokens exceed it.                                                          |

With those hooks filled in, this controller will run Reason-from-Future loops for *almost any task* that can be decomposed into goal-directed micro-targets and forward satisfiable steps.
