# Reason-from-Future Python Package

A modular implementation of the **Reason-from-Future (RFF)** algorithm.  This package provides:

- A domain-agnostic controller (`reason_from_future`) that alternates reverse planning (G), forward stepping (R), and local checks (C).
- LLM glue built on the new `google.genai` SDK.
- Core abstractions: `Workspace`, `ProblemSpec`, and `LocalCheckFail`.
- Example `ProblemSpec` subclasses in `reason_from_future.specs`:
  - `Game24Spec` (reach 24 from four integers)
  - `GSM8KSpec` (toy math word problem)

---

## Installation

1. Activate your virtual environment:
   ```bash
   source .venv/bin/activate
   ```

2. Install the package in editable mode:
   ```bash
   pip install -e .
   ```

3. Set your Gemini API key:
   ```bash
   export GEMINI_API_KEY="your_key_here"
   ```

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

For more details, refer to `src/reason_from_future/core.py` and the original design in `PLANS/inital_setup.md`.
