# Reason-from-Future Python Package

A modular implementation of the **Reason-from-Future (RFF)** algorithm.  This package provides:

- A domain-agnostic controller (`reason_from_future`) that alternates reverse planning (G), forward stepping (R), and local checks (C).
- LLM glue built on the new `google.genai` SDK.
- Core abstractions: `Workspace`, `ProblemSpec`, and `LocalCheckFail`.
- Example `ProblemSpec` subclasses in `reason_from_future.specs`:
  - `Game24Spec` (reach 24 from four integers)
  - `GSM8KSpec` (toy math word problem)
  - `GeneralProblemSolvingSpec` (system design, planning, decision making)

---

## Installation

1. Activate your virtual environment:
   ```bash
   source .venv/bin/activate
   ```

2. Install the package using our prebuilt script:
   ```bash
   sh project_setup.sh
   ```

3. Set your Gemini API key:
   ```bash
   export GEMINI_API_KEY="your_key_here"
   ```
or add it to your local .env file.

---

## Quickstart

```python
from reason_from_future.controller import reason_from_future
from reason_from_future.specs import Game24Spec

# Example: reach 24
spec = Game24Spec([1, 3, 6, 11])
answer = reason_from_future("Reach 24 with numbers [1,3,6,11]", spec)
print("Solution:", answer)
```

---

## Adding a New `ProblemSpec`

To support a new problem domain, follow these steps:

1. **Create a new spec module**
   - File: `src/reason_from_future/specs/my_domain.py`
   - Subclass `ProblemSpec` and implement the five abstract methods:
     - `derive_final_target(self, problem: str) -> str`
     - `parse_workspace_update(self, raw_text: str) -> Workspace`
     - `check_local(self, state: Workspace, target_step: str) -> bool`
     - `verify_final(self, state: Workspace) -> Tuple[bool, str]`
     - `prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str`
     - `prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]) -> str`

2. **Register your spec**
   - Add an import in `src/reason_from_future/specs/__init__.py`:
     ```python
     from .my_domain import MyDomainSpec
     __all__.append("MyDomainSpec")
     ```

3. **Use your spec**
   ```python
   from reason_from_future.specs import MyDomainSpec
   spec = MyDomainSpec(/* domain-specific args */)
   result = reason_from_future("Your problem prompt", spec)
   ```

---

## Conceptual Background and Relation to RFF Paper

This project draws its core inspiration from the **Reason-from-Future (RFF)** paradigm, notably detailed in the paper *[Reason from Future: Reverse Thought Chain Enhances LLM Reasoning](https://arxiv.org/abs/2506.03673)*. The paper proposes a bidirectional reasoning approach where reverse thinking (identifying a step just before the target) guides forward reasoning to enhance LLM problem-solving by providing global context and constraining the search space.

Our implementation embraces this foundational idea but expands upon it by providing a **modular and extensible framework**:

*   **Domain-Agnostic Controller:** At its heart, our package features a generic `reason_from_future` controller. This controller orchestrates the RFF flow without being tied to a specific problem type.
*   **`ProblemSpec` Abstraction:** The key to this generality is the `ProblemSpec` interface. Users can integrate new problem domains by implementing this interface, defining how the problem is decomposed, how steps are generated, and how states are verified. This contrasts with the paper's more direct application of RFF to specific tasks like Game of 24 and GSM8K.
*   **Generalized RFF Cycle:** Our controller implements a cycle of:
    1.  **Reverse Planning (G):** The `ProblemSpec.prompt_last_step` method asks the LLM to identify a plausible precursor step (the "last step") required to achieve the current target.
    2.  **Forward Stepping (R):** The `ProblemSpec.prompt_forward_step` method then instructs the LLM to generate the reasoning or action to reach this identified precursor step.
    3.  **Local Check (C):** `ProblemSpec.check_local` verifies if the forward step successfully achieved the precursor. The `Workspace` object manages the evolving state.
*   **Flexibility over Specific RFF Variants:** The paper details RFF-T (for tree-like searches with backtracking) and RFF-G (for graph-like accumulation of knowledge). Our framework is designed to be flexible. While the controller itself is general, `ProblemSpec` implementations can incorporate logic to emulate these behaviors (e.g., using the `avoid` mechanism in prompts for RFF-T-like exploration, or designing `Workspace` updates and `parse_workspace_update` for RFF-G-like information accumulation).
*   **Expansion and Evolution:** This project has evolved to include a more general problem-solving module and has seen specific enhancements, such as to the `GSM8KSpec`. This reflects an ongoing effort to refine and broaden the applicability of the RFF approach beyond the initial concepts presented in the paper. The `Workspace` abstraction also provides a more structured approach to state management than implicitly described in the paper's algorithms.

The original paper introduced the RFF concept and demonstrated its efficacy. This package aims to provide a robust, reusable, and adaptable toolkit for applying and experimenting with Reason-from-Future style reasoning across diverse challenges.
