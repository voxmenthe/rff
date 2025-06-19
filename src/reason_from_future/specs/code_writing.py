import json
import re
import textwrap
from typing import Dict, Set, Tuple, List, Any, Optional

from ..core import ProblemSpec, Workspace


class CodeWritingSpec(ProblemSpec):
    """
    ProblemSpec for generating code.
    
    The workspace will maintain a structure for:
    - Modules: Code files and their contents.
    - Functions: Signatures, descriptions, and bodies.
    - Classes: Definitions, attributes, and methods.
    - Test Cases: Inputs and expected outputs for verifying code.
    - Decisions: Design choices made during code generation.
    """
    def __init__(self, problem_config: Dict[str, Any]):
        super().__init__()
        self.problem_statement = problem_config.get("problem_statement", "")
        self.language = problem_config.get("language", "python")
        self.requirements = problem_config.get("requirements", [])
        self.evaluation_criteria = problem_config.get("evaluation_criteria", [])

        self.workspace_schema = {
            "modules": {},          # module_name: { "content": "...", "description": "..." }
            "functions": {},        # func_name: { "signature": "...", "body": "...", "description": "...", "module": "..." }
            "classes": {},          # class_name: { "attributes": {}, "methods": {}, "description": "...", "module": "..." }
            "test_cases": {},       # test_name: { "input": "...", "expected_output": "...", "target_element": "func_or_class_name" }
            "decisions": {},        # decision_name: { "choice": "...", "rationale": "..." }
            "dependencies": {},     # element_name: { "depends_on": [], "type": "import/call/inheritance" }
            "solution_code": None   # String containing the final assembled code or path to main file
        }

    def derive_final_target(self, problem: str) -> str:
        return "complete_code_solution"

    def parse_workspace_update(self, raw_text: str, state: Workspace) -> Workspace:
        clean_text = raw_text.strip()
        
        if not state:
            state = Workspace(self.workspace_schema.copy())

        try:
            # Attempt to extract JSON from potentially markdown-formatted text
            # Handles ```json ... ``` or just ``` ... ```
            json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', clean_text, re.DOTALL)
            if not json_match:
                # If not in triple backticks, look for a raw JSON object
                json_match = re.search(r'(\{[\s\S]*\})', clean_text)

            if not json_match:
                # Heuristic: if it's a large block of code, assume it's the solution
                if "solution_code" in state.workspace_schema and isinstance(raw_text, str) and len(raw_text.splitlines()) > 3:
                    if any(kw in raw_text for kw in ["def ", "class ", "import ", "{", "}"]) or raw_text.startswith("```"):
                         code_content = raw_text
                         if raw_text.startswith("```") and raw_text.endswith("```"):
                             code_content = raw_text[raw_text.find('\n')+1:-3].strip()
                         state["solution_code"] = code_content
                return state 

            json_text = json_match.group(1)
            
            update = json.loads(json_text)
            update_type = update.get("update_type", "")

            if update_type == "module":
                name = update.get("name")
                if name:
                    if "modules" not in state: state["modules"] = {}
                    state["modules"][name] = {
                        "content": update.get("content", ""),
                        "description": update.get("description", "")
                    }
            
            elif update_type == "function":
                name = update.get("name")
                if name:
                    if "functions" not in state: state["functions"] = {}
                    state["functions"][name] = {
                        "signature": update.get("signature", ""),
                        "body": update.get("body", ""),
                        "description": update.get("description", ""),
                        "module": update.get("module")
                    }

            elif update_type == "class":
                name = update.get("name")
                if name:
                    if "classes" not in state: state["classes"] = {}
                    state["classes"][name] = {
                        "attributes": update.get("attributes", {}),
                        "methods": update.get("methods", []), 
                        "description": update.get("description", ""),
                        "module": update.get("module")
                    }

            elif update_type == "test_case":
                name = update.get("name")
                if name:
                    if "test_cases" not in state: state["test_cases"] = {}
                    state["test_cases"][name] = {
                        "input": update.get("input", ""),
                        "expected_output": update.get("expected_output", ""),
                        "target_element": update.get("target_element", "")
                    }
            
            elif update_type == "decision":
                name = update.get("name")
                if name:
                    if "decisions" not in state: state["decisions"] = {}
                    state["decisions"][name] = {
                        "choice": update.get("choice", ""),
                        "rationale": update.get("rationale", "")
                    }

            elif update_type == "dependency":
                element_name = update.get("element_name")
                if element_name:
                    if "dependencies" not in state: state["dependencies"] = {}
                    state["dependencies"][element_name] = {
                        "depends_on": update.get("depends_on", []),
                        "type": update.get("type", "")
                    }
            
            elif update_type == "solution_code":
                code = update.get("code")
                if code is not None:
                    state["solution_code"] = code
            
            elif update_type == "batch":
                sub_updates = update.get("updates", [])
                if not isinstance(sub_updates, list):
                    return state
                
                for sub_update_item in sub_updates:
                    if isinstance(sub_update_item, dict):
                        sub_update_json_str = json.dumps(sub_update_item)
                        state = self.parse_workspace_update(sub_update_json_str, state)
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            pass

        return state

    def _summarize_state_for_prompt(self, state: Workspace) -> str:
        if not state or not state.get_all_data():  # Check if workspace has any data
            return "The code workspace is currently empty."

        summary_parts = []

        modules = state.get("modules", {})
        if not isinstance(modules, dict): modules = {}
        functions = state.get("functions", {})
        if not isinstance(functions, dict): functions = {}
        classes = state.get("classes", {})
        if not isinstance(classes, dict): classes = {}

        if modules:
            summary_parts.append("Current Modules:")
            for name, details in modules.items():
                content_len = len(details.get("content", ""))
                desc = details.get("description", "No description")
                summary_parts.append(f"  - Module '{name}': {content_len} chars, Description: {desc}")
        
        if functions:
            summary_parts.append("\nCurrent Functions:")
            for name, details in functions.items():
                sig = details.get("signature", "N/A")
                body_len = len(details.get("body", ""))
                module = details.get("module", "N/A")
                desc = details.get("description", "No description")
                summary_parts.append(f"  - Function '{name}': Signature: {sig}, Body length: {body_len} chars, Module: {module}, Description: {desc}")

        if classes:
            summary_parts.append("\nCurrent Classes:")
            for name, details in classes.items():
                num_attrs = len(details.get("attributes", {}))
                num_methods = len(details.get("methods", []))
                module = details.get("module", "N/A")
                desc = details.get("description", "No description")
                summary_parts.append(f"  - Class '{name}': Attributes: {num_attrs}, Methods: {num_methods}, Module: {module}, Description: {desc}")

        if not summary_parts:
            return "The code workspace contains some data, but no modules, functions, or classes are defined yet."

        return "\n".join(summary_parts)

    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str:
        state_summary = self._summarize_state_for_prompt(state)

        avoid_instructions = ""
        if avoid:
            avoid_instructions = f"\n\nPlease avoid suggesting the following tasks as they have been tried or are problematic: {', '.join(avoid)}"

        prompt = f"""\
        You are a component in an AI coding system. Your task is to identify the single most critical next coding task to make progress towards a larger goal.

        Problem Statement: {self.problem_statement}
        Target Language: {self.language}

        Current Code Development Status:
        {state_summary}

        Ultimate Goal: {target}

        Based on the current status and the ultimate goal, what is the MOST CRITICAL next coding task to undertake? 
        Consider dependencies: e.g., a function cannot be implemented if its module isn't defined; tests cannot be written for a function that doesn't exist.
        Prioritize foundational elements first (modules, class shells, function signatures) before detailed implementations if they are missing.
        If foundational elements are in place, prioritize implementing core logic or writing tests for existing components.

        Examples of good task names (use these prefixes):
        - "define_module_<module_name>" (e.g., "define_module_utils")
        - "implement_function_<function_name>" (e.g., "implement_function_calculate_total_in_module_cart")
        - "define_class_<class_name>" (e.g., "define_class_User")
        - "implement_method_<method_name>_in_class_<class_name>" (e.g., "implement_method_add_item_in_class_ShoppingCart")
        - "write_tests_for_<element_name>" (e.g., "write_tests_for_function_calculate_total" or "write_tests_for_class_User")
        - "refactor_<area_to_refactor>" (e.g., "refactor_error_handling_in_module_payment")
        - "decide_on_<design_choice_name>" (e.g., "decide_on_database_schema_for_orders")
        {avoid_instructions}

        Respond with ONLY a single JSON object in the format: {{"next_task": "task_name_with_prefix_and_description"}}
        For example: {{"next_task": "define_module_user_authentication"}}
        """
        return textwrap.dedent(prompt)

    def prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]) -> str:
        state_summary = self._summarize_state_for_prompt(state)
        requirements_json = json.dumps(self.requirements, indent=2)

        task_instructions = "Please complete the following coding task. Structure your response as a single JSON object with the fields specified in the example."
        output_example = {"update_type": "generic", "details": "..."} # Default example

        if target_step.startswith("define_module_"):
            module_name = target_step[len("define_module_"):]
            task_instructions = f"Define the module '{module_name}'. Provide its full code content and a brief description."
            output_example = {"update_type": "module", "name": module_name, "content": "...", "description": "..."}
        
        elif target_step.startswith("implement_function_"):
            # e.g. implement_function_my_func_in_module_utils
            # e.g. implement_function_my_func
            func_name_parts = target_step[len("implement_function_"):].split("_in_module_")
            func_name = func_name_parts[0]
            module_name = func_name_parts[1] if len(func_name_parts) > 1 else None

            task_instructions = f"Implement the function '{func_name}'."
            if module_name:
                task_instructions += f" This function belongs to module '{module_name}'."
            task_instructions += " Provide its signature, full body code, and a description. If it belongs to a module, specify the module name."
            output_example = {"update_type": "function", "name": func_name, "signature": "def ...(...):", "body": "...", "description": "...", "module": module_name or "optional_module_name"}

        elif target_step.startswith("define_class_"):
            # e.g. define_class_MyClass_in_module_models
            # e.g. define_class_MyClass
            class_name_parts = target_step[len("define_class_"):].split("_in_module_")
            class_name = class_name_parts[0]
            module_name = class_name_parts[1] if len(class_name_parts) > 1 else None
            
            task_instructions = f"Define the class '{class_name}'."
            if module_name:
                task_instructions += f" This class belongs to module '{module_name}'."
            task_instructions += " Specify its attributes (as a dictionary), methods (as a list of names or simple signatures for now), and a description. If it belongs to a module, specify the module name."
            output_example = {"update_type": "class", "name": class_name, "attributes": {"attr_name": "type"}, "methods": ["method_signature_or_name"], "description": "...", "module": module_name or "optional_module_name"}

        elif target_step.startswith("implement_method_"):
            # e.g. implement_method_my_method_in_class_MyClass
            parts = target_step[len("implement_method_"):].split("_in_class_")
            method_name = parts[0]
            class_name = parts[1] if len(parts) > 1 else "UnknownClass"
            task_instructions = f"Implement the method '{method_name}' for class '{class_name}'. Provide its full body code. You can also update the class definition if needed."
            # This might be complex. For now, let's assume it updates a function/method body,
            # and the LLM should be smart enough to provide the context (class/function name)
            # Or it can be a special update type or use the function update type.
            # Let's use function update type for now, assuming methods are treated like functions in workspace.
            output_example = {"update_type": "function", "name": f"{class_name}.{method_name}", "signature": "def ...(...):", "body": "...", "description": f"Method {method_name} of class {class_name}", "module": "optional_module_name_if_class_is_in_module"}


        elif target_step.startswith("write_tests_for_"):
            element_name = target_step[len("write_tests_for_"):]
            task_instructions = f"Write test cases for '{element_name}'. For each test, provide a name, input(s), expected output, and the target element it tests."
            output_example = {"update_type": "test_case", "name": "test_my_scenario", "input": "...", "expected_output": "...", "target_element": element_name}
        
        elif target_step.startswith("decide_on_"):
            decision_name = target_step[len("decide_on_"):]
            task_instructions = f"Make a decision on '{decision_name}'. Provide your choice and a clear rationale for it."
            output_example = {"update_type": "decision", "name": decision_name, "choice": "...", "rationale": "..."}

        elif target_step == "complete_code_solution":
            task_instructions = "Provide the final, complete code solution. This could be a single block of code, or if the project is structured into modules, ensure all module definitions are up-to-date or provide instructions on how to assemble them."
            output_example = {"update_type": "solution_code", "code": "final code string or assembly instructions"}
        
        # TODO: Add more specific task types like "refactor_", "implement_method_in_class" etc.

        prompt = f"""\
        You are a component in an AI coding system. Your task is to perform a specific coding step based on the current state of the project and the target step defined.

        Problem Statement: {self.problem_statement}
        Target Language: {self.language}

        Project Requirements:
        {requirements_json}

        Current Code Development Status:
        {state_summary}

        Current Task: {target_step}
        Task Instructions: {task_instructions}
        {f"Please avoid generating content related to these if they were part of a previous error: {', '.join(avoid)}" if avoid else ""}

        Respond with ONLY a single JSON object matching the structure of the example below.
        Ensure all specified fields in the example are present in your JSON response.

        Output JSON Example:
        {json.dumps(output_example, indent=2)}
        """
        return textwrap.dedent(prompt)

    def parse_target_step(self, raw_text: str) -> str:
        clean_text = raw_text.strip()

        try:
            # Robust JSON extraction (handles backticks, leading/trailing text)
            json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', clean_text, re.DOTALL)
            if not json_match:
                json_match = re.search(r'(\{[\s\S]*\})', clean_text) # Look for raw JSON object

            if json_match:
                json_text = json_match.group(1)
                data = json.loads(json_text)
                next_task = data.get("next_task")
                if isinstance(next_task, str) and next_task.strip():
                    return next_task.strip()
        except json.JSONDecodeError:
            # JSON parsing failed, proceed to fallbacks
            pass

        # Fallback 1: Look for lines starting with common task prefixes
        lines = clean_text.splitlines()
        for line in lines:
            line = line.strip()
            # Common prefixes for tasks
            task_prefixes = [
                "define_module_", "implement_function_", "define_class_", 
                "implement_method_", "write_tests_for_", "decide_on_", "refactor_"
            ]
            for prefix in task_prefixes:
                if line.startswith(prefix) and len(line) > len(prefix): # Ensure there's a name after prefix
                    # Basic validation: ensure it's not just the prefix
                    # and doesn't contain problematic characters (e.g. often LLMs add "...")
                    if "..." not in line and " " not in line[len(prefix):]: # Avoid spaces in task names
                        return line 
        
        # Fallback 2: Return the last non-empty line if it seems like a plausible task
        if lines:
            last_line = lines[-1].strip()
            if last_line and not last_line.startswith("{") and not last_line.endswith("}"): # Avoid returning partial JSON
                 # Check if it resembles a task (simple heuristic)
                if any(prefix in last_line for prefix in ["define", "implement", "write", "refactor", "decide"]):
                    return last_line

        # Fallback 3: If the whole text seems like a single task name (no JSON, no obvious task lines)
        # This is a weaker heuristic.
        if not clean_text.startswith("{") and not clean_text.endswith("}") and len(clean_text.split()) < 5 and clean_text:
             if any(prefix in clean_text for prefix in ["define", "implement", "write", "refactor", "decide"]):
                return clean_text


        return "" # If all parsing and fallbacks fail

    def check_local(self, state: Workspace, target_step: str) -> bool:
        if not state:
            return False

        if target_step == "complete_code_solution":
            solution_code = state.get("solution_code")
            modules = state.get("modules")
            return bool(solution_code and isinstance(solution_code, str) and solution_code.strip()) or \
                   (isinstance(modules, dict) and bool(modules))

        elif target_step.startswith("define_module_"):
            module_name = target_step[len("define_module_"):]
            modules = state.get("modules", {})
            return module_name in modules and \
                   isinstance(modules[module_name], dict) and \
                   bool(modules[module_name].get("content", "").strip())

        elif target_step.startswith("implement_function_"):
            function_name = target_step[len("implement_function_"):]
            functions = state.get("functions", {})
            return function_name in functions and \
                   isinstance(functions[function_name], dict) and \
                   bool(functions[function_name].get("body", "").strip())

        elif target_step.startswith("define_class_"):
            class_name = target_step[len("define_class_"):]
            classes = state.get("classes", {})
            if class_name in classes and isinstance(classes[class_name], dict):
                class_def = classes[class_name]
                return bool(class_def.get("methods")) or bool(class_def.get("attributes"))
            return False

        elif target_step.startswith("write_tests_for_"):
            element_name = target_step[len("write_tests_for_"):]
            test_cases = state.get("test_cases", {})
            if not test_cases or not isinstance(test_cases, dict):
                return False
            return any(isinstance(tc, dict) and tc.get("target_element") == element_name 
                       for tc in test_cases.values())

        elif target_step.startswith("decide_on_"):
            decision_name = target_step[len("decide_on_"):]
            decisions = state.get("decisions", {})
            return decision_name in decisions and \
                   isinstance(decisions[decision_name], dict) and \
                   bool(decisions[decision_name].get("choice", "").strip()) and \
                   bool(decisions[decision_name].get("rationale", "").strip())
        
        normalized_target = target_step.replace(" ", "_").lower()
        for category_key in ["modules", "functions", "classes", "decisions"]:
            category = state.get(category_key)
            if isinstance(category, dict) and normalized_target in category:
                item = category[normalized_target]
                if isinstance(item, dict):
                    return any(bool(v) for k, v in item.items() if k not in ['name', 'description', 'module'])
                elif isinstance(item, str):
                    return bool(item.strip()) 
                elif bool(item): 
                    return True
        
        return self._find_in_nested_dict(state.get_internal_state_DEBUG(), normalized_target)


    def _find_in_nested_dict(self, d: Any, target: str) -> bool:
        if isinstance(d, dict):
            if target in d: 
                val = d[target]
                if isinstance(val, (dict, list)): return bool(val) 
                if isinstance(val, str): return bool(val.strip()) 
                return bool(val) 

            for k, v in d.items():
                if isinstance(v, str) and v == target: 
                    return True
                if self._find_in_nested_dict(v, target): 
                    return True
        elif isinstance(d, list):
            for item in d:
                if isinstance(item, str) and item == target:
                     return True
                if self._find_in_nested_dict(item, target): 
                    return True
        return False

    def verify_final(self, state: Workspace) -> Tuple[bool, str, float]:
        if not state:
            return False, "Workspace is empty.", 0.0

        solution_code = state.get("solution_code", "")
        modules = state.get("modules", {})
        functions = state.get("functions", {})
        classes = state.get("classes", {})
        test_cases = state.get("test_cases", {})

        # Ensure they are of expected types, default to empty if not
        if not isinstance(solution_code, str): solution_code = ""
        if not isinstance(modules, dict): modules = {}
        if not isinstance(functions, dict): functions = {}
        if not isinstance(classes, dict): classes = {}
        if not isinstance(test_cases, dict): test_cases = {}

        has_solution_code = bool(solution_code.strip())
        has_modules = bool(modules)
        
        if not has_solution_code and not has_modules:
            return False, "No complete code solution found (no solution_code or populated modules).", 0.0

        description_parts = []
        if has_solution_code:
            description_parts.append(f"Final solution code provided ({len(solution_code)} chars).")
        if has_modules:
            description_parts.append(f"Modules defined: {', '.join(modules.keys()) or 'none'}.")
        if functions:
            description_parts.append(f"Functions defined: {', '.join(functions.keys()) or 'none'}.")
        if classes:
            description_parts.append(f"Classes defined: {', '.join(classes.keys()) or 'none'}.")
        if test_cases:
            description_parts.append(f"Test cases defined: {', '.join(test_cases.keys()) or 'none'}.")

        solution_description = " ".join(description_parts) if description_parts else "A code solution is present but no specific elements were itemized."

        quality_score = 0.0
        # Max possible score is 1.0, distributed as:
        # 0.4 for base code (solution_code or modules)
        # 0.2 for functions
        # 0.2 for classes
        # 0.2 for test cases
        
        if has_solution_code or has_modules:
            quality_score += 0.4
        
        if functions: # Add score proportional to number of functions, capped at 0.2
            quality_score += min(0.2, len(functions) * 0.05) 
            
        if classes: # Add score proportional to number of classes, capped at 0.2
            quality_score += min(0.2, len(classes) * 0.1)

        if test_cases: # Add score proportional to number of test cases, capped at 0.2
            quality_score += min(0.2, len(test_cases) * 0.05)
        
        # Ensure score is between 0.0 and 1.0
        normalized_score = max(0.0, min(1.0, quality_score))
        
        is_acceptable = normalized_score >= 0.5 

        return is_acceptable, solution_description, normalized_score


    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str:
        # To be implemented
        return "Define the next coding task."

    def prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]) -> str:
        # To be implemented
        return f"Implement {target_step}."

    def parse_target_step(self, raw_text: str) -> str:
        # To be implemented
        return ""

    def merge_aliases(self, state: Workspace) -> Workspace:
        # To be implemented
        return state
