"""
Demonstration of the CodeWritingSpec with a Controller and LLM.
This script shows a basic setup for using the Reason From Future (RFF)
framework to generate code based on a problem statement.
"""
import os
import json
from dotenv import load_dotenv

from reason_from_future.core import Controller, Workspace
from reason_from_future.llm import OpenAILLM
from reason_from_future.specs.code_writing import CodeWritingSpec

def main():
    """
    Main function to run the CodeWritingSpec demo.
    """
    print("Starting Code Writing Demo...")

    # Load environment variables from .env file
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Please set it in your environment or in a .env file.")
        return

    # 1. Initialize the LLM
    # Make sure to have OPENAI_API_KEY set in your environment
    llm = OpenAILLM(model_name="gpt-4-turbo-preview", api_key=api_key)

    # 2. Define the problem configuration for CodeWritingSpec
    problem_config = {
        "problem_statement": "Write a Python function to calculate the factorial of a non-negative integer. "
                             "The function should be named 'factorial', take an integer 'n' as input, "
                             "and return its factorial. It should raise a ValueError for negative inputs.",
        "language": "python",
        "requirements": [
            "The function must be named 'factorial'.",
            "It must accept one integer argument 'n'.",
            "It must return the factorial of 'n'.",
            "If 'n' is negative, it must raise a ValueError.",
            "The solution should preferably be iterative to avoid recursion depth limits for large 'n', though a recursive one is acceptable for simplicity if clearly documented."
        ],
        "evaluation_criteria": [
            "Correctness: Does it produce the correct factorial for valid inputs?",
            "Error Handling: Does it raise ValueError for negative inputs?",
            "Clarity: Is the code well-documented and easy to understand?",
            "Completeness: Is the function fully implemented as per the requirements?"
        ]
    }

    # 3. Initialize the CodeWritingSpec
    spec = CodeWritingSpec(problem_config=problem_config)

    # 4. Initialize the Controller
    # The initial workspace can be empty or pre-populated if needed
    initial_workspace = Workspace(spec.workspace_schema.copy())
    controller = Controller(spec=spec, llm=llm, workspace=initial_workspace)

    # 5. Run the RFF loop (Simplified for now)
    # In a full scenario, this would involve multiple turns of:
    #   - controller.propose_next_step()
    #   - (User/Agent review/approval of the step)
    #   - controller.execute_step(target_step)
    #   - Loop until controller.is_solved() or max_turns

    print("\nInitial Workspace:")
    print(json.dumps(controller.workspace.get_all_data(), indent=2))

    # 5. Run the RFF loop
    max_turns = 7 # Increased for more complex tasks
    previous_target_step = None
    final_target_str = spec.derive_final_target(problem_config["problem_statement"])

    for i in range(max_turns):
        print(f"\n--- Turn {i+1}/{max_turns} ---")
        try:
            current_target_step = controller.propose_next_step()
            print(f"Suggested next step: {current_target_step}")

            if not current_target_step:
                print("No further steps proposed. Ending loop.")
                break

            if current_target_step == previous_target_step:
                print(f"Proposed step '{current_target_step}' is the same as the previous one. Ending loop to prevent stagnation.")
                # Optionally, could call controller.propose_next_step(avoid={current_target_step}) here
                # but for now, just break.
                break

            controller.execute_step(target_step=current_target_step)
            print("\nWorkspace after step execution:")
            # print(json.dumps(controller.workspace.get_all_data(), indent=2)) # Can be very verbose
            # Instead, let's use the spec's summary function
            print(spec._summarize_state_for_prompt(controller.workspace))


            previous_target_step = current_target_step

            # Check if the final target is achieved
            if current_target_step == final_target_str:
                if spec.check_local(controller.workspace, current_target_step):
                    print(f"\nFinal target '{final_target_str}' achieved and verified locally.")
                    break
                else:
                    print(f"\nFinal target '{final_target_str}' reached, but local check failed. Continuing...")

            # Optional: Early exit if solution seems complete by other means
            # is_solved_interim, _, _ = controller.verify_solution()
            # if is_solved_interim:
            #     print("Solution verified as acceptable during the loop. Ending early.")
            #     break

        except Exception as e:
            print(f"An error occurred during turn {i+1}: {e}")
            print("Current workspace state before error:")
            print(json.dumps(controller.workspace.get_all_data(), indent=2))
            break # Stop the loop on error

    # 6. Retrieve and print the final solution from the workspace
    print("\n--- Retrieving Final Solution from Workspace ---")
    solution_code = controller.workspace.get("solution_code")
    modules = controller.workspace.get("modules")

    if solution_code and isinstance(solution_code, str) and solution_code.strip():
        print("\nFinal Generated Solution Code (from solution_code field):")
        print(solution_code)
    elif modules and isinstance(modules, dict) and modules:
        print("\nFinal Generated Modules (assembled from modules field):")
        full_code = []
        for name, module_data in modules.items():
            if isinstance(module_data, dict) and "content" in module_data:
                full_code.append(f"# --- Module: {name} ---\n{module_data['content']}")
        if full_code:
            print("\n\n".join(full_code))
        else:
            print("Modules field was present but contained no parsable content.")
            print(json.dumps(modules, indent=2)) # Print raw modules for debugging
    else:
        print("No final code generated in 'solution_code' or 'modules' fields.")
        print("Current workspace state:")
        print(json.dumps(controller.workspace.get_all_data(), indent=2))


    # 7. Verify the final solution using the spec's method
    print("\n--- Final Verification ---")
    is_acceptable, description, quality_score = controller.verify_solution()
    print(f"Is solution acceptable (by spec.verify_final)? {is_acceptable}")
    print(f"Solution Description: {description}")
    print(f"Quality Score: {quality_score:.2f}")

    print("\nDemo Complete.")

if __name__ == "__main__":
    main()
