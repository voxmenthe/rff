"""General Problem Solving Spec for RFF - handles system design, planning, and complex decisions."""
import json
import re
import textwrap
from typing import Dict, Set, Tuple, List, Any, Optional
from collections import defaultdict

from ..core import Workspace, ProblemSpec


class GeneralProblemSolvingSpec(ProblemSpec):
    """
    A flexible ProblemSpec for complex qualitative problems like system design,
    strategic planning, or multi-step decision making.
    
    The workspace maintains a hierarchical structure of:
    - Components: design artifacts with properties
    - Decisions: choices made with rationales
    - Constraints: requirements and limitations
    - Dependencies: relationships between elements
    """
    
    def __init__(self, problem_config: Dict[str, Any]):
        """
        Initialize with a problem configuration.
        
        Args:
            problem_config: Dict containing:
                - problem_statement: The problem to solve
                - problem_type: 'system_design', 'strategic_planning', 'decision_making', etc.
                - requirements: List of key requirements/constraints
                - evaluation_criteria: What constitutes a good solution
        """
        super().__init__()
        self.problem_statement = problem_config.get("problem_statement", "")
        self.problem_type = problem_config.get("problem_type", "general")
        self.requirements = problem_config.get("requirements", [])
        self.evaluation_criteria = problem_config.get("evaluation_criteria", [])
        
        # Initialize structured workspace schema
        self.workspace_schema = {
            "components": {},      # Design artifacts
            "decisions": {},       # Key decisions made
            "constraints": {},     # Requirements and limitations
            "dependencies": {},    # Relationships between elements
            "rationales": {},      # Explanations for choices
            "open_questions": [],  # Unresolved issues
            "assumptions": []      # Working assumptions
        }
    
    def derive_final_target(self, problem: str) -> str:
        """The ultimate goal is a complete, coherent solution."""
        return "complete_solution"
    
    def parse_workspace_update(self, raw_text: str, state: Workspace) -> Workspace:
        """
        Parse structured updates from LLM output.
        Expects JSON with update_type and content.
        """
        clean_text = raw_text.strip()
        
        # Initialize current state structure if empty
        if not state:
            state = Workspace(self.workspace_schema.copy())
        
        try:
            # Extract JSON from LLM response
            json_match = re.search(r'\{[\s\S]*\}', clean_text)
            if json_match:
                json_text = json_match.group(0)
                # Clean up common JSON formatting issues
                if json_text.startswith("```json"):
                    json_text = json_text[7:-3].strip()
                elif json_text.startswith("```"):
                    json_text = json_text[3:-3].strip()
                
                update = json.loads(json_text)
                
                # Process different update types
                update_type = update.get("update_type", "")
                
                if update_type == "component":
                    # Adding/updating a design component
                    comp_name = update.get("name")
                    if comp_name:
                        if "components" not in state:
                            state["components"] = {}
                        state["components"][comp_name] = {
                            "description": update.get("description", ""),
                            "properties": update.get("properties", {}),
                            "interfaces": update.get("interfaces", []),
                            "rationale": update.get("rationale", "")
                        }
                        return state
                
                elif update_type == "decision":
                    # Recording a decision
                    decision_name = update.get("name")
                    if decision_name:
                        if "decisions" not in state:
                            state["decisions"] = {}
                        state["decisions"][decision_name] = {
                            "choice": update.get("choice", ""),
                            "alternatives": update.get("alternatives", []),
                            "rationale": update.get("rationale", ""),
                            "trade_offs": update.get("trade_offs", {})
                        }
                        return state
                
                elif update_type == "dependency":
                    # Adding a dependency relationship
                    if "dependencies" not in state:
                        state["dependencies"] = {}
                    from_comp = update.get("from")
                    to_comp = update.get("to")
                    if from_comp and to_comp:
                        if from_comp not in state["dependencies"]:
                            state["dependencies"][from_comp] = []
                        state["dependencies"][from_comp].append({
                            "to": to_comp,
                            "type": update.get("dependency_type", "uses")
                        })
                        return state
                
                elif update_type == "solution_summary":
                    # Final solution summary
                    state["complete_solution"] = {
                        "summary": update.get("summary", ""),
                        "key_components": update.get("key_components", []),
                        "key_decisions": update.get("key_decisions", []),
                        "implementation_order": update.get("implementation_order", [])
                    }
                    return state
                
                elif update_type == "batch":
                    # Multiple updates at once
                    for sub_update in update.get("updates", []):
                        # Recursively process each sub-update
                        sub_json = json.dumps(sub_update)
                        state = self.parse_workspace_update(sub_json, state)
                    return state
                    
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Fallback: try to extract any structured information
            pass
        
        # If we couldn't parse structured updates, return unchanged state
        return state
    
    def check_local(self, state: Workspace, target_step: str) -> bool:
        """
        Check if a target step has been adequately addressed.
        For qualitative problems, this checks structural completeness.
        """
        if target_step == "complete_solution":
            # Check if we have a solution summary
            return "complete_solution" in state and bool(state["complete_solution"].get("summary"))
        
        # Check various target patterns
        if target_step.startswith("define_"):
            component_name = target_step[7:]  # Remove "define_"
            return (
                "components" in state and 
                component_name in state["components"] and
                bool(state["components"][component_name].get("description"))
            )
        
        elif target_step.startswith("decide_"):
            decision_name = target_step[7:]  # Remove "decide_"
            return (
                "decisions" in state and
                decision_name in state["decisions"] and
                bool(state["decisions"][decision_name].get("choice"))
            )
        
        elif target_step.startswith("analyze_"):
            # Check if analysis results exist (could be in components or decisions)
            analysis_name = target_step[8:]
            return (
                ("components" in state and analysis_name in state["components"]) or
                ("decisions" in state and analysis_name in state["decisions"])
            )
        
        # Generic check: see if the target_step exists anywhere in state
        return self._find_in_nested_dict(state, target_step)
    
    def _find_in_nested_dict(self, d: dict, target: str) -> bool:
        """Helper to search for a key in nested dictionaries."""
        if target in d:
            return True
        for v in d.values():
            if isinstance(v, dict) and self._find_in_nested_dict(v, target):
                return True
        return False
    
    def verify_final(self, state: Workspace) -> Tuple[bool, str, float]:
        """
        Verify the final solution quality.
        Since there's no gold standard, we use criteria-based evaluation.
        Returns (is_acceptable, solution_description, quality_score).
        """
        if "complete_solution" not in state:
            return False, "No complete solution found", 0.0
        
        solution = state["complete_solution"]
        solution_text = solution.get("summary", "")
        
        # Basic completeness checks
        has_components = bool(state.get("components"))
        has_decisions = bool(state.get("decisions"))
        has_summary = bool(solution_text)
        
        if not (has_components or has_decisions) or not has_summary:
            return False, "Solution is incomplete", 0.0
        
        # For now, we'll use a simple heuristic for quality
        # In a real implementation, this could call an LLM to evaluate
        quality_score = 0.0
        if has_summary:
            quality_score += 0.4
        if has_components:
            quality_score += 0.3 * min(len(state["components"]) / 3, 1.0)
        if has_decisions:
            quality_score += 0.3 * min(len(state["decisions"]) / 2, 1.0)
        
        # Consider solution acceptable if quality > 0.7
        is_acceptable = quality_score > 0.7
        
        return is_acceptable, solution_text, quality_score
    
    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str:
        """
        Generate backward planning prompt for decomposition.
        """
        # Summarize current state
        state_summary = self._summarize_state(state)
        
        avoid_str = f"\nDo not propose any of these already-attempted tasks: {sorted(avoid)}" if avoid else ""
        
        prompt = f"""You are planning the solution to this problem:
{self.problem_statement}

Current solution state:
{state_summary}

Your ultimate goal is to achieve: {target}

Given the current state, identify the MOST CRITICAL missing piece or unresolved sub-problem that must be addressed before the {target} can be achieved.

This should be:
1. Something not already well-defined in the current state
2. A concrete, actionable task (not vague like "improve design")
3. Something whose completion would significantly advance the solution

{avoid_str}

Respond with a JSON object containing exactly one key "next_task" with a string value.
The task should be prefixed with an action verb like:
- "define_" for creating components/modules
- "decide_" for making architectural/strategic choices  
- "analyze_" for understanding requirements/constraints
- "design_" for creating detailed specifications

Example: {{"next_task": "define_core_services"}}

IMPORTANT: Respond with ONLY the JSON object.
"""
        return prompt
    
    def prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]) -> str:
        """
        Generate forward execution prompt to accomplish a specific task.
        """
        state_summary = self._summarize_state(state)
        
        # Determine the type of task from the target_step
        if target_step.startswith("define_"):
            task_type = "component"
            instructions = "Define the component with its description, key properties, and interfaces."
        elif target_step.startswith("decide_"):
            task_type = "decision"
            instructions = "Make the decision, listing alternatives considered, your choice, rationale, and trade-offs."
        elif target_step.startswith("analyze_"):
            task_type = "component"  # Analysis results stored as components
            instructions = "Analyze the aspect and document your findings with key insights."
        elif target_step == "complete_solution":
            task_type = "solution_summary"
            instructions = "Provide a comprehensive summary of the complete solution."
        else:
            task_type = "component"
            instructions = "Complete this task with appropriate detail and rationale."
        
        prompt = f"""You are solving this problem:
{self.problem_statement}

Requirements: {json.dumps(self.requirements, indent=2)}

Current solution state:
{state_summary}

Your current task: {target_step}

{instructions}

Output your response as a JSON object with these fields:
- "update_type": "{task_type}"
- "name": (the specific name of what you're defining/deciding, without the action prefix)
- Additional fields based on type:
  - For components: "description", "properties" (dict), "interfaces" (list), "rationale"
  - For decisions: "choice", "alternatives" (list), "rationale", "trade_offs" (dict)
  - For solution_summary: "summary", "key_components" (list), "key_decisions" (list), "implementation_order" (list)

Example for a component:
{{
  "update_type": "component",
  "name": "user_service",
  "description": "Manages user authentication and profiles",
  "properties": {{"database": "PostgreSQL", "framework": "FastAPI"}},
  "interfaces": ["REST API", "GraphQL endpoint"],
  "rationale": "Chosen for scalability and type safety"
}}

IMPORTANT: Respond with ONLY the JSON object.
"""
        return prompt
    
    def parse_target_step(self, raw_text: str) -> str:
        """Extract the next task from backward planning output."""
        clean_text = raw_text.strip()
        
        try:
            # Look for JSON with next_task
            json_match = re.search(r'\{[^}]*"next_task"[^}]*\}', clean_text)
            if json_match:
                json_text = json_match.group(0)
                data = json.loads(json_text)
                task = data.get("next_task", "").strip()
                if task:
                    return task
        except:
            pass
        
        # Fallback: look for action patterns
        action_match = re.search(r'(define_|decide_|analyze_|design_)\w+', clean_text)
        if action_match:
            return action_match.group(0)
        
        # Last resort: clean and return
        lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
        if lines:
            last_line = lines[-1].strip('"\'`).,')
            if last_line:
                return last_line
        
        return ""
    
    def merge_aliases(self, state: Workspace) -> Workspace:
        """
        Merge potential aliases in the workspace.
        For complex problems, different names might refer to the same concept.
        """
        # For now, return state as-is
        # In a more sophisticated implementation, we could use semantic similarity
        return state
    
    def _summarize_state(self, state: Workspace) -> str:
        """Generate a human-readable summary of the current state."""
        if not state:
            return "Empty - no progress yet"
        
        summary_parts = []
        
        # Summarize components
        if "components" in state and state["components"]:
            comp_names = list(state["components"].keys())
            summary_parts.append(f"Components defined: {', '.join(comp_names)}")
        
        # Summarize decisions
        if "decisions" in state and state["decisions"]:
            dec_names = list(state["decisions"].keys())
            summary_parts.append(f"Decisions made: {', '.join(dec_names)}")
        
        # Summarize dependencies
        if "dependencies" in state and state["dependencies"]:
            dep_count = sum(len(deps) for deps in state["dependencies"].values())
            summary_parts.append(f"Dependencies mapped: {dep_count}")
        
        # Check for solution
        if "complete_solution" in state:
            summary_parts.append("Solution summary: Available")
        
        return "\n".join(summary_parts) if summary_parts else "Minimal progress"