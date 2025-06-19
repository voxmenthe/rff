"""
Demonstration of the CodeWritingSpec with a Controller and LLM.
This script shows a basic setup for using the Reason From Future (RFF)
framework to generate code based on a problem statement.
"""

from reason_from_future.core import reason_from_future
from reason_from_future.specs.code_writing import CodeWritingSpec

def run_example(problem_config, max_iters: int = 8, verbose: bool = True):
    """Helper to run Reason-from-Future with CodeWritingSpec."""
    print("=" * 60)
    print("Code Writing Demo – Factorial Function")
    print("=" * 60)

    spec = CodeWritingSpec(problem_config)

    try:
        solution = reason_from_future(
            problem=problem_config["problem_statement"],
            spec=spec,
            max_iters=max_iters,
            min_iters=3,  # ensure a few iterations of exploration
            require_gold=False,  # no gold answer available
            verbose=verbose,
        )
        print("\n" + "=" * 60)
        print("FINAL GENERATED CODE:")
        print("=" * 60)
        print(solution)
    except RuntimeError as e:
        print(f"\nFailed to generate complete solution: {e}")


def main():
    """Entry-point for the demo."""
    problem_config = {
        "problem_statement": (
            "Write a Python function to calculate the factorial of a non-negative integer. "
            "The function should be named 'factorial', take an integer 'n' as input, "
            "and return its factorial. It should raise a ValueError for negative inputs."
        ),
        "language": "python",
        "requirements": [
            "The function must be named 'factorial'.",
            "It must accept one integer argument 'n'.",
            "It must return the factorial of 'n'.",
            "If 'n' is negative, it must raise a ValueError.",
            "The solution should preferably be iterative to avoid recursion depth limits for large 'n', though a recursive one is acceptable if clearly documented.",
        ],
        "evaluation_criteria": [
            "Correctness: Does it produce the correct factorial for valid inputs?",
            "Error Handling: Does it raise ValueError for negative inputs?",
            "Clarity: Is the code well-documented and easy to understand?",
            "Completeness: Is the function fully implemented as per the requirements?",
        ],
    }

    run_example(problem_config, max_iters=8, verbose=True)


if __name__ == "__main__":
    main()
