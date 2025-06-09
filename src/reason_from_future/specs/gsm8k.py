"""GSM8K ProblemSpec implementation."""
import json
import re
from typing import Dict, Set, Tuple

from ..core import Workspace, ProblemSpec


# flake8: noqa: E501

class GSM8KSpec(ProblemSpec):
    """GSM8K ProblemSpec implementation for actual GSM8K evaluation."""

    def __init__(self, problem_data: Dict[str, str]):
        """
        Initializes the GSM8KSpec with a problem.

        Args:
            problem_data: A dictionary containing the 'question' and 'answer'
                          for the GSM8K problem.
                          Example: {"question": "Natalia sold clips to 48 of her friends...",
                                    "answer": "Natalia sold 48/2 = 24 clips to her friends... #### 24"}
        """
        super().__init__()
        self.question: str = problem_data["question"]
        self.problem_data: Dict[str, str] = problem_data # Store for potential future use

        # Extract the numeric answer from the 'answer' string
        # The answer format is typically "Explanation... #### numeric_answer", but we also handle if just the number is passed.
        # Make '#### ' part optional and capture the number.
        # The number can have commas and a decimal point.
        answer_str = str(problem_data["answer"]) # Ensure it's a string
        match = re.search(r"(?:####\s*)?([0-9,.]+)\s*$", answer_str)
        if match:
            # Remove commas for thousands separators before converting to float
            self.gold_numeric_answer: float = float(match.group(1).replace(",", ""))
        else:
            print(f"Warning: Could not parse gold numeric answer from: '{answer_str}'")
            self.gold_numeric_answer: float = float('nan')

    def derive_final_target(self, problem: str) -> str:
        """
        Determines the variable name for the final answer.
        The 'problem' argument (the question text) is available but not strictly needed here
        if we use a fixed target name.
        """
        return "final_answer"

    # ---------------------------------------------------------------------
    # Parsing & local check upgrades: now we expect expression + value and
    # evaluate expression numerically to verify the step.
    # ---------------------------------------------------------------------
    def parse_workspace_update(self, raw_text: str, state: Workspace) -> Workspace:
        """
        Expect a JSON line like {"var": "x", "expr": "a + b", "value": 123}.
        NOTE: This parsing logic is simplistic for LLM-generated structured output.
        Real-world scenarios might require more robust parsing for natural language
        assignments or more complex data structures.
        """
        clean_raw_text = raw_text.strip()
        try:
            # Try to find a JSON block, even if embedded
            match = re.search(r"\{[\s\S]*?\}", clean_raw_text) # Non-greedy match for a JSON-like structure
            if match:
                json_text = match.group(0)
                # Further clean common LLM quirks around JSON
                json_text = json_text.strip()
                if json_text.startswith("```json"):
                    json_text = json_text[7:-3].strip() # Remove ```json and ```
                elif json_text.startswith("```"):
                    json_text = json_text[3:-3].strip() # Remove ``` and ```
                clean_raw_text = json_text

            data = json.loads(clean_raw_text)
            var_name = data.get("var")
            var_value = data.get("value")
            expr = data.get("expr")  # optional

            if var_name and var_value is not None:
                # Workhorse: if 'expr' present, evaluate under current state
                if expr and isinstance(expr, str):
                    try:
                        # Build a safe eval namespace with numbers only
                        safe_locals = {k: v for k, v in state.items() if isinstance(v, (int, float))}
                        calculated = float(eval(expr, {}, safe_locals))
                        if abs(calculated - float(var_value)) > 1e-4:
                            # Mismatch – reject entire update
                            return Workspace()
                    except Exception:
                        return Workspace()
                elif isinstance(var_value, str):
                    try:
                        # Handle commas in numbers
                        var_value = float(var_value.replace(",", ""))
                    except ValueError:
                        pass # Keep as string if not purely numeric or if conversion fails
                elif isinstance(var_value, (int, float)):
                    var_value = float(var_value)
                return Workspace({var_name: var_value})
        except json.JSONDecodeError:
            # print(f"Warning: JSONDecodeError in parse_workspace_update for: {raw_text}")
            pass # Fall through to other parsing methods
        except Exception:
            # print(f"Warning: Unexpected error in parse_workspace_update for: {raw_text}")
            pass # Fall through to other parsing methods

        # Attempt 2: Look for "The final answer is $\boxed{<number>}$"
        # This is a fallback if the primary task was to get the final_answer.
        # We need to know what variable name `final_answer` corresponds to.
        # Let's assume `self.derive_final_target(self.question)` gives this.
        final_target_var_name = self.derive_final_target(self.question)
        
        boxed_match = re.search(r"The final answer is \$\\boxed\{([\d\.,]+)\}\$", clean_raw_text, re.IGNORECASE)
        if boxed_match:
            try:
                value_str = boxed_match.group(1).replace(",", "")
                numeric_value = float(value_str)
                # Heuristic: If this pattern is found, assume it's the final answer.
                # This might need to be tied to the 'target_step' if this function knew it.
                # For now, if we see this, we assume it's the final answer.
                return Workspace({final_target_var_name: numeric_value})
            except ValueError:
                # print(f"Warning: Could not convert boxed value to float: {boxed_match.group(1)}")
                pass

        # Attempt 3: Look for simpler "final answer is <number>"
        simple_match = re.search(r"(?:final answer is|result is|is simply|is:)\s*([\d\.,]+)", clean_raw_text, re.IGNORECASE)
        if simple_match:
            try:
                value_str = simple_match.group(1).replace(",", "")
                numeric_value = float(value_str)
                return Workspace({final_target_var_name: numeric_value})
            except ValueError:
                # print(f"Warning: Could not convert simple final answer to float: {simple_match.group(1)}")
                pass
                
        # print(f"Warning: Could not parse workspace update from: {raw_text}")
        return Workspace()

    # ------------------------------------------------------------------
    # Enhanced checks & alias merge utilities
    # ------------------------------------------------------------------
    def merge_aliases(self, state: Workspace) -> Workspace:
        """Coalesce obviously synonymous variable names (heuristic)."""
        if len(state) <= 1:
            return state  # nothing to do

        normalized_map: dict[str, str] = {}
        for var in state:
            norm = re.sub(r"(?:number|num|total|initial|before|after|of|the)", "", var.lower())
            norm = re.sub(r"[_\s]+", "_", norm).strip("_")
            normalized_map.setdefault(norm, var)

        # If two vars normalize to same key, keep the first that is numerically consistent.
        new_state = Workspace()
        for norm_key, representative_var in normalized_map.items():
            new_state[representative_var] = state[representative_var]
        return new_state

    def check_local(self, state: Workspace, target_step: str) -> bool:
        """Now also ensures the value is numeric."""
        if target_step not in state:
            return False
        return isinstance(state[target_step], (int, float))

    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str:
        """
        Generates a prompt to ask the LLM for the step immediately preceding the target.
        'target' here is expected to be "final_answer".
        """
        # Ensure problem context (self.question) is included.
        avoid_list_str = f"Do not choose any of these variables for 'next_variable': {sorted(list(avoid))}." if avoid else ""
        prompt = f"""You are reasoning backward through a math word problem to find the solution.
The problem is:
{self.question}

Known facts so far (intermediate variables and their computed values):
{json.dumps(state, indent=2)}

The goal is to compute: "{target}".
What single unknown variable or sub-result (that is not already in 'Known facts so far') needs to be computed immediately before you can determine the value of "{target}"?
Output your answer as a single JSON object with one key: 'next_variable', where the value is the name of this prerequisite variable. For example: {{"next_variable": "variable_name_here"}}.
{avoid_list_str}

IMPORTANT: Your *entire response* must be *only* the JSON object described above. Do not include any other text, explanations, reasoning, or conversational remarks before or after the JSON. Adhere strictly to this format.
"""
        return prompt

    def prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]) -> str:
        """
        Generates a prompt to ask the LLM to compute the value for target_step.
        If target_step is determined to be the final answer, LLM is instructed to use 'final_answer'.
        """
        final_goal_name = self.derive_final_target(self.question)

        prompt = f"""You are solving a math word problem step-by-step.
The problem is:
{self.question}

Known facts so far (intermediate variables and their computed values):
{json.dumps(state, indent=2)}

Your current task is to compute the value for the variable: "{target_step}".
Based on the problem statement and the known facts, calculate this value.
If you determine that the value of "{target_step}" is the final answer to the overall problem, use "{self.derive_final_target(self.question)}" as the 'var' in your JSON output. Otherwise, use "{target_step}" as the 'var'.

Output your answer as a single JSON object with three keys: 'var', 'expr', and 'value'.
  • 'var'  – either the target variable or "{self.derive_final_target(self.question)}" if it's final.
  • 'expr' – a Python-style arithmetic expression that evaluates to the value **using only previously
             known variables** (listed above). If the step is trivial or the final answer, just repeat the
             numeric value as the expression.
  • 'value' – the numerical result.
For example, if asked to compute 'X' and X is the final answer: {{"var": "{self.derive_final_target(self.question)}", "expr": "a + b", "value": 123.45}}
If asked to compute 'Y' and Y is an intermediate step: {{"var": "Y", "expr": "miles_driven / gallons", "value": 67.89}}
Ensure the 'value' is a number, not a string containing an expression.

IMPORTANT: Your *entire response* must be *only* the JSON object described above. Do not include any other text, explanations, reasoning, or conversational remarks before or after the JSON. Adhere strictly to this format.
"""
        return prompt

    def parse_target_step(self, raw_text: str) -> str:
        """Parse raw LLM output from backward reasoning to get the next target variable name."""
        clean_raw_text = raw_text.strip()
        # Attempt 1: Find and parse JSON {"next_variable": "..."}
        try:
            # Try to find a JSON block, even if embedded
            match = re.search(r"\{[\s\S]*?\"next_variable\"\s*:\s*\"(.*?)\"[\s\S]*?\}", clean_raw_text)
            if match:
                json_like_text = match.group(0)
                # Clean common LLM quirks around JSON
                if json_like_text.startswith("```json"):
                    json_like_text = json_like_text[7:].strip()
                    if json_like_text.endswith("```"):
                        json_like_text = json_like_text[:-3].strip()
                elif json_like_text.startswith("```"):
                    json_like_text = json_like_text[3:].strip()
                    if json_like_text.endswith("```"):
                        json_like_text = json_like_text[:-3].strip()
                
                data = json.loads(json_like_text) # Parse the found JSON-like segment
                if "next_variable" in data and isinstance(data["next_variable"], str):
                    return data["next_variable"].strip()
        except json.JSONDecodeError:
            # print(f"Warning: JSONDecodeError in parse_target_step (attempt 1) for: {raw_text}")
            pass # Fall through
        except Exception:
            # print(f"Warning: Unexpected error in JSON parsing (attempt 1) for: {raw_text}")
            pass

        # Attempt 2: Look for $\boxed{\text{variable_name}}$
        boxed_text_match = re.search(r"\$\\boxed\{\text\{([_a-zA-Z0-9\s]+)\}\}\$", clean_raw_text)
        if boxed_text_match:
            return boxed_text_match.group(1).strip().replace(" ", "_") # Replace spaces with underscores for var names

        # Attempt 3: Look for `variable_name` (often at the end of reasoning)
        # This is a more general heuristic. We might take the last line if it looks like a variable.
        lines = [line.strip() for line in clean_raw_text.split('\n') if line.strip()]
        if lines:
            last_line = lines[-1]
            # Remove common conversational prefixes or JSON artifacts if any still present
            last_line = re.sub(r"^(?:The next variable to compute is|Here is the JSON output:)\s*", "", last_line, flags=re.IGNORECASE).strip()
            last_line = last_line.replace("`", "").replace("'", "").replace("\"", "") # Remove backticks/quotes
            
            # Check if it looks like a variable name (alphanumeric with underscores)
            if re.fullmatch(r"[_a-zA-Z][_a-zA-Z0-9]*", last_line):
                return last_line

        # Fallback: return the cleaned raw text if no specific pattern is found,
        # hoping it's just the variable name (as per original fallback).
        # Or, decide if it's better to return a specific error string or raise an exception.
        # For now, let's return a cleaned version of the last line or the whole text.
        # print(f"Warning: Could not parse target step reliably from: {raw_text}. Using fallback.")
        return lines[-1] if lines else clean_raw_text # Fallback to last line or original cleaned text

    def verify_final(self, state: Workspace) -> Tuple[bool, str, float]:
        """
        Verifies the computed final answer against the gold numeric answer.
        Returns: (is_correct, llm_answer_str, gold_answer_float)
        """
        guess_val = state.get(self.derive_final_target(self.question)) # Use derive_final_target for consistency
        
        if guess_val is None:
            return False, "No final answer provided."

        try:
            # Attempt to convert the guess to a float for comparison
            # LLM might output a number as int, float, or string representation of a number.
            if isinstance(guess_val, str):
                # Remove commas if present
                guess_val_cleaned = guess_val.replace(",", "")
                # Handle potential non-numeric strings gracefully
                # Regex to check if string is a valid representation of a float/int
                if not re.fullmatch(r"-?\d+(\.\d+)?", guess_val_cleaned): 
                     return False, f"Invalid numeric format for final answer: {guess_val}"
                numeric_guess = float(guess_val_cleaned)
            elif isinstance(guess_val, (int, float)):
                numeric_guess = float(guess_val) # Works for int and float
            else: # if guess_val is not convertible (e.g. dict, list)
                return False, f"Final answer '{guess_val}' has an unexpected type {type(guess_val).__name__}."

        except ValueError: # Catch error if float conversion fails for a string
            return False, f"Final answer '{guess_val}' is not a valid number."
        
        # Compare with the gold standard
        # Using a small tolerance for float comparisons if necessary,
        # but for GSM8K, answers are often integers or exact decimals.
        is_correct = abs(numeric_guess - self.gold_numeric_answer) < 1e-5 # Tolerance for float comparison
        
        return is_correct, str(numeric_guess), self.gold_numeric_answer
