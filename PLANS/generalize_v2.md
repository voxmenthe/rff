Excellent question. Based on the provided framework, we can design a new `ProblemSpec` for a more open-ended, qualitative domain like system design. This requires a significant shift from the numeric, deterministic logic of `GSM8KSpec` to a more structural, compositional, and qualitative logic.

### New Spec: `SystemDesignSpec`

This spec will guide an LLM to reason through a system design problem, such as "Design a URL shortening service like TinyURL" or "Outline the architecture for a real-time chat application."

---

### How would its logic, structure, and flow differ?

The core difference lies in moving from **quantitative calculation** to **qualitative composition**.

| Feature | `GSM8KSpec` (Quantitative) | `SystemDesignSpec` (Qualitative/Structural) |
| :--- | :--- | :--- |
| **Workspace State** | A dictionary of numeric variables. `{"num_apples": 10, "total_cost": 45.5}`. | A nested dictionary representing a design tree. Keys are component names, values are structured objects with descriptions, APIs, dependencies, etc. |
| **Goal (Target)** | A single variable (`final_answer`) holding a numeric value. | A complete, coherent design document. The target variable is a placeholder like `"final_system_design"`. |
| **Backward Step** | "What number do I need to calculate X?" (Prerequisite finding) | "To achieve goal Y, what are the primary components or sub-problems I need to solve/design first?" (Decomposition) |
| **Forward Step** | "Calculate the value for X using known variables." (Computation) | "Flesh out the design for component Z. Define its API, data model, and dependencies." (Elaboration/Creation) |
| **Local Check** | Is the variable's value a valid number? (`isinstance(val, (int, float))`) | Is the generated design for a component structurally sound? (e.g., "Does the JSON have 'api_endpoints' and 'data_model' keys?") It's a syntactic/structural check, not a semantic one. |
| **Final Verification** | `abs(llm_answer - gold_answer) < 1e-5`. A precise, objective check against a single correct number. | No single "gold" answer. Verification is qualitative, likely requiring another LLM call to act as a "reviewer." It would check for coherence, completeness against requirements, and major design flaws. |
| **Flow** | A directed acyclic graph (DAG) of calculations, converging on a final number. | A process of hierarchical decomposition followed by compositional synthesis. The system starts as a black box, is broken down into components, and then each component is designed and integrated. |

The RFF (Reason-from-Future) paradigm is exceptionally well-suited for this. The "future" is the high-level user requirement (e.g., "a scalable chat app"), and the reverse reasoning steps (`prompt_last_step`) are about architectural decomposition, which is exactly how human engineers approach such problems.

---

### Initial Code for `SystemDesignSpec`

Here is an initial implementation. It follows the `ProblemSpec` interface but adapts the internal logic for this new domain.

```python
"""SystemDesignSpec: A ProblemSpec for reasoning through system architecture."""
import json
import re
import textwrap
from typing import Dict, Set, Tuple

from ..core import Workspace, ProblemSpec
from ..llm import llm_call # We need this for the qualitative verification step

class SystemDesignSpec(ProblemSpec):
    """
    A ProblemSpec for guiding an LLM through a system design problem.
    The state is not a set of numeric variables, but a collection of
    designed components and specifications.
    """

    def __init__(self, problem_data: Dict[str, str]):
        """
        Initializes the spec with a system design problem.

        Args:
            problem_data: A dict containing 'problem' and optional 'constraints'.
                          Example: {"problem": "Design a URL shortening service.",
                                    "constraints": "Must handle 1 billion requests/month."}
        """
        super().__init__()
        self.problem: str = problem_data["problem"]
        # Gold answer is not a number, but a rubric or set of key features.
        # For this example, we'll make verify_final use an LLM-as-a-judge.
        self.constraints: str = problem_data.get("constraints", "No specific constraints.")

    def derive_final_target(self, problem: str) -> str:
        """The final goal is a complete design document."""
        return "final_system_design"

    def parse_workspace_update(self, raw_text: str, state: Workspace) -> Workspace:
        """
        Expects a JSON object describing a system component.
        Example: {"component_name": "api_gateway", "design": {"description": "...", "endpoints": [...]}}
        """
        clean_raw_text = raw_text.strip()
        try:
            # Find a JSON block
            match = re.search(r"\{[\s\S]*?\}", clean_raw_text)
            if not match:
                return Workspace()
            
            json_text = match.group(0)
            data = json.loads(json_text)
            
            component_name = data.get("component_name")
            design_details = data.get("design")

            if component_name and isinstance(design_details, dict):
                return Workspace({component_name: design_details})
        except json.JSONDecodeError:
            pass # Failed to parse
        return Workspace()

    def check_local(self, state: Workspace, target_step: str) -> bool:
        """
        Checks if the component (`target_step`) exists in the workspace and
        has a minimal structure (e.g., a 'description' key).
        """
        if target_step not in state:
            return False
        
        component_data = state.get(target_step)
        if isinstance(component_data, dict) and "description" in component_data:
            return True
            
        return False

    def merge_aliases(self, state: Workspace) -> Workspace:
        """
        Coalesces synonymous component names.
        e.g., "auth_service" and "authentication_system".
        """
        # This can be more sophisticated for technical terms, but for now,
        # we'll use a simple normalization similar to GSM8K's.
        normalized_map: dict[str, str] = {}
        for var in state:
            norm = re.sub(r"(?:service|system|component|manager|api|database)", "", var.lower())
            norm = re.sub(r"[_\s]+", "_", norm).strip("_")
            normalized_map.setdefault(norm, var)

        new_state = Workspace()
        for norm_key, representative_var in normalized_map.items():
            new_state[representative_var] = state[representative_var]
        return new_state

    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str:
        """
        Asks the LLM to decompose the problem. "What are the next components to design?"
        This is the core "backward reasoning" step.
        """
        designed_components = sorted(list(state.keys()))
        avoid_list_str = f"Do not choose any of these components: {sorted(list(avoid))}." if avoid else ""

        prompt = textwrap.dedent(f"""
            You are a principal software architect designing a complex system.
            
            Overall Goal: {self.problem}
            Constraints: {self.constraints}

            Components already designed:
            {json.dumps(state, indent=2) if state else "None yet."}

            Your ultimate target is to produce the '{target}'. To get there, what are the most critical, high-level components or subsystems that need to be designed next? These should be independent modules if possible.

            {avoid_list_str}

            Provide up to **two** prerequisite component names that are the logical next step in the design. The names should be in snake_case.

            Output a single JSON object with one key "next_components" whose value is an array of 1-2 strings. Example:
            {{"next_components": ["api_gateway", "url_hashing_service"]}}

            IMPORTANT: Respond with ONLY the JSON.
        """).strip()
        return prompt

    def parse_target_step(self, raw_text: str) -> str:
        """Parse LLM output to get the next component name to design."""
        # This can be very similar to GSM8K's, looking for a JSON array.
        try:
            match = re.search(r"\{[\s\S]*?\}", raw_text.strip())
            if match:
                data = json.loads(match.group(0))
                if "next_components" in data and isinstance(data["next_components"], list):
                    for component in data["next_components"]:
                        if isinstance(component, str) and component:
                            return component.strip()
        except Exception:
            pass
        # Fallback to a simple text extraction if JSON fails
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        return lines[-1] if lines else ""

    def prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]) -> str:
        """
        Asks the LLM to design a specific component. This is the "forward" step.
        """
        designed_components = sorted(list(state.keys()))

        prompt = textwrap.dedent(f"""
            You are a principal software architect designing a complex system.

            Overall Goal: {self.problem}
            Constraints: {self.constraints}
            
            Components designed so far:
            {json.dumps(designed_components, indent=2)}

            Your current task is to design the component: "{target_step}".

            Provide a detailed design for this component. Consider its responsibilities, its public API (if any), the data it manages, and its dependencies on other components.

            Output your answer as a single JSON object with two keys:
            1. "component_name": A string, which must be exactly "{target_step}".
            2. "design": A JSON object containing the details. It should include at least a "description" key. You can also add "api_endpoints", "data_model", "dependencies", etc.

            Example format:
            {{
                "component_name": "url_hashing_service",
                "design": {{
                    "description": "A stateless service that generates a unique 6-character hash from a long URL.",
                    "api_endpoints": [
                        {{"method": "POST", "path": "/hash", "body": "long_url", "response": "short_hash"}}
                    ],
                    "dependencies": []
                }}
            }}

            IMPORTANT: Your entire response must be ONLY the JSON object.
        """).strip()
        return prompt

    def verify_final(self, state: Workspace) -> Tuple[bool, str, float]:
        """
        Uses an LLM-as-a-judge to perform a qualitative review of the final design.
        """
        final_target = self.derive_final_target(self.problem)
        if final_target not in state:
            # In our design, the final state is the collection of all components.
            # We will use the entire state for verification.
            if not state:
                return False, "No design components were created.", float('nan')
            final_design_doc = json.dumps(state, indent=2)
        else:
            final_design_doc = json.dumps(state[final_target], indent=2)

        # Prompt for an LLM-based "reviewer"
        reviewer_prompt = textwrap.dedent(f"""
            You are an expert system design reviewer. Your task is to evaluate a proposed system design based on a problem description and constraints.

            Problem Description: {self.problem}
            Constraints: {self.constraints}

            Proposed System Design:
            ---
            {final_design_doc}
            ---

            Please review the design for completeness, coherence, and feasibility.
            1. Does the design address all major aspects of the problem?
            2. Are the components well-defined and do their interactions make sense?
            3. Are there any glaring omissions or major flaws in the design?
            
            Based on your review, conclude with a single line: "Verdict: [PASS]" or "Verdict: [FAIL]".
            Follow this with a brief one-sentence justification.
        """).strip()

        # Call the LLM to act as the judge
        review_text = llm_call(reviewer_prompt, model="gemini-1.5-pro-preview-0514", verbose=False)

        # Parse the review
        is_correct = False
        if re.search(r"Verdict:\s*\[PASS\]", review_text, re.IGNORECASE):
            is_correct = True
        
        # Return the verdict, the review text, and NaN for the unused float
        return is_correct, review_text, float('nan')

```