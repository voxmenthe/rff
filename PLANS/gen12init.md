### New Spec: `SystemDesignSpec`

This spec will guide an LLM to reason through a system design problem, such as "Design a URL shortening service like TinyURL" or "Outline the architecture for a real-time chat application."

---

### How it would differ from GSM8KSpec:

1.  **Nature of the "Goal" (`derive_final_target`):**
    *   **GSM8K:** A single numeric variable (`final_answer`).
    *   **New Spec:** Not a variable, but a *description of a desired end-state*. For example, "A complete and feasible design for a microservices-based e-commerce backend," or "A robust plan to launch a new product." The symbolic target for the RFF controller might still be a placeholder like `"solution_complete"`, but the *meaning* of this target is tied to a qualitative description.

2.  **Workspace Content (`Workspace`):**
    *   **GSM8K:** Primarily stores numeric variables and their string expressions.
    *   **New Spec:** Stores much richer, structured, and qualitative information.
        *   **System Design:** Components, their interfaces, data models, technology choices, rationales, identified risks, unresolved questions, constraints.
        *   **Agentic Decisions:** Sequences of actions, observed outcomes, belief states, goals/sub-goals, chosen strategies, evaluated options.
        *   The workspace would likely be a nested dictionary/list structure, not just flat key-value pairs. For example, `state['components']` could be a list of component description objects.

3.  **Parsing LLM Output (`parse_workspace_update`):**
    *   **GSM8K:** Parses a simple JSON with `var`, `expr`, `value`.
    *   **New Spec:** Needs to parse more complex, possibly LLM-generated, structured output (e.g., JSON representing a design component, a decision rationale, or a proposed action). It might also need to interpret natural language updates if strict JSON isn't always produced. The LLM would be prompted to provide these structured updates.

4.  **Local Check (`check_local`):**
    *   **GSM8K:** Checks if a numeric variable is present and valid.
    *   **New Spec:** This becomes much more nuanced and potentially LLM-driven itself.
        *   If `target_step` was "Define API for User Service," `check_local` might verify that the workspace now contains a new entry under `state['components']['user_service']['api_definition']` and that this definition isn't empty or trivial.
        *   It could involve heuristic checks (e.g., "Does the API definition include common CRUD endpoints if it's a data-centric service?").
        *   More advanced: It could even be a quick LLM call: "Does this proposed API definition for X seem plausible and internally consistent at a high level? (Yes/No/Partially + brief reason)".

5.  **Final Verification (`verify_final`):**
    *   **GSM8K:** Compares a number to a gold standard.
    *   **New Spec:** This is the most significant change. There's rarely a single "gold answer" for a design or complex plan.
        *   Verification would likely be an LLM call: "Given the initial problem [problem_description] and the current proposed solution/plan [current_workspace_summary], does this solution appear complete, coherent, address all key requirements, and seem feasible? Identify any major gaps, inconsistencies, or unaddressed critical requirements."
        *   The `(is_correct, llm_answer_str, gold_answer_float)` tuple would change. `gold_answer_float` is irrelevant. `is_correct` would be True if the LLM (as verifier) deems the solution adequate. `llm_answer_str` would be the final proposed solution/plan.
        *   The `require_gold` parameter in `reason_from_future` becomes less about a numeric gold standard and more about whether this LLM-based final verification must pass.

6.  **Last Step Prompt (Backward Planning - G) (`prompt_last_step`):**
    *   **GSM8K:** "What variable do you need before `final_answer`?"
    *   **New Spec:** "Our ultimate goal is to [description_of_final_target]. The current state of our design/plan is [summary_of_workspace]. To make significant progress towards the final goal, what is the *single most important unresolved sub-problem, missing component definition, or critical decision* that we need to address *next*? This should be something whose resolution would unblock further progress or clarify a major aspect of the overall solution. Phrase this as a clear, actionable task or question. Avoid proposing something already well-defined in the current state."

7.  **Forward Step Prompt (R) (`prompt_forward_step`):**
    *   **GSM8K:** "Compute the value for variable `X`."
    *   **New Spec:** "The overall problem is [problem_description]. Our current design/plan state is [summary_of_workspace]. Your current task, derived from backward planning, is: [target_step_description (e.g., 'Define the database schema for the order_service')]. Propose a detailed solution/text/design for *this specific task*. Explain your reasoning and how it fits into the broader solution. Output your proposal in a structured format (e.g., JSON with fields like 'proposal_summary', 'details', 'rationale', 'potential_issues')."

8.  **Parsing Target Step (`parse_target_step`):**
    *   **GSM8K:** Extracts a variable name.
    *   **New Spec:** Extracts the natural language description of the sub-problem/task identified by the G-prompt.

9.  **Alias Merging (`merge_aliases`):**
    *   **GSM8K:** Merges synonymous variable names.
    *   **New Spec:** This could be more complex. It might involve recognizing that "user authentication module" and "identity service" refer to the same conceptual component and consolidating their descriptions or linking them. This might also require LLM assistance.

**Logic Needed:**

*   **Qualitative Reasoning:** Ability to understand and generate descriptions, rationales, and arguments.
*   **Structured Knowledge Representation:** Managing complex, evolving data structures in the workspace.
*   **Decomposition:** Breaking down a large problem (e.g., "design an e-commerce site") into manageable sub-problems (e.g., "design user auth," "design product catalog API," "choose payment gateway"). This is what the G-prompt aims to elicit.
*   **Constraint Satisfaction:** Implicitly, by checking if proposed solutions meet requirements.
*   **Trade-off Analysis (Implicit):** When making decisions, the LLM might internally weigh options, and the R-prompt could ask it to articulate these.
*   **Abstraction and Refinement:** Starting with high-level goals and progressively detailing components.
*   **Self-Correction/Critique:** The `verify_final` step is essentially a critique step. Local checks could also have a light critique aspect.

**Process and Flow:**

The RFF loop remains, but the *content* of G and R calls changes:

1.  **Initial Goal:** "Achieve a complete system design for X." (Symbolic target: `design_complete`)
2.  **Iteration 1 (G-Prompt):** "What's the first major component/decision needed for `design_complete` given an empty workspace?" -> LLM: "Define core services." (`target_step` = "Define core services")
3.  **Iteration 1 (R-Prompt):** "Define core services for X." -> LLM: Proposes `user_service`, `product_service`, `order_service` with brief descriptions (parsed into workspace).
4.  **Local Check:** Workspace now has entries for these services. Pass. (Assume `made_progress=True`).
5.  **Iteration 2 (G-Prompt):** "Goal: `design_complete`. Current state: basic core services defined. What's next most important unresolved task before `design_complete`?" -> LLM: "Specify API for `user_service`." (`target_step` = "Specify API for `user_service`")
6.  **Iteration 2 (R-Prompt):** "Specify API for `user_service`." -> LLM: Proposes API endpoints and data structures (parsed into workspace).
7.  ...and so on, iteratively detailing components, defining interfaces, making technology choices.
8.  **Final Check (`verify_final`):** After `max_iters` or if `design_complete` is directly attempted and "locally checked" (e.g., LLM claims it's done), a comprehensive LLM call reviews the entire workspace against the original problem.

---
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