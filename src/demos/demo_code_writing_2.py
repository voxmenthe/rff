"""
Demonstration of the CodeWritingSpec with a Controller and LLM *for a multi-step problem*.

This demo intentionally poses a task that cannot be solved in a single shot so
that the Reason-from-Future (RFF) loop must incrementally plan out modules,
classes, and tests.  The chosen problem is a **tiny URL shortener library**.
"""

from reason_from_future.core import reason_from_future
from reason_from_future.specs.code_writing import CodeWritingSpec


HEADER = "=" * 60

def run_example(problem_config: dict, *, max_iters: int = 12, verbose: bool = True) -> None:
    """Helper that drives one RFF session and prints the outcome."""
    print(HEADER)
    print("Code Writing Demo – Tiny URL Shortener")
    print(HEADER)

    spec = CodeWritingSpec(problem_config)

    try:
        solution = reason_from_future(
            problem=problem_config["problem_statement"],
            spec=spec,
            max_iters=max_iters,
            min_iters=4,  # encourage a few iterations of exploration
            require_gold=False,  # no gold answer available
            verbose=verbose,
        )
        print("\n" + HEADER)
        print("FINAL GENERATED CODE:")
        print(HEADER)
        print(solution)
    except RuntimeError as exc:
        print("\nFailed to generate complete solution:", exc)


def main() -> None:
    """Entry-point for the demo."""
    problem_config = {
        "problem_statement": (
            "Create a small *in-memory* URL shortener library in Python.  "
            "Expose a *ShortURLService* class with two public methods:  "
            "`shorten(long_url: str) -> str` which returns a unique 6-character "
            "code for the given URL, and `resolve(code: str) -> str` which returns "
            "the original long URL or raises a `KeyError` if the code is unknown.  "
            "The generated codes must be URL-safe (alphanumerics only) and the "
            "service must guarantee uniqueness even for concurrent calls."
        ),
        "language": "python",
        "requirements": [
            "Provide a *ShortURLService* class with an __init__ method that initialises any internal state.",
            "Implement `shorten(long_url)` which: (1) validates that long_url starts with http or https, (2) creates a unique 6-character alphanumeric code, (3) stores the mapping, and (4) returns the code.",
            "Implement `resolve(code)` which returns the original long URL stored for *code* or raises KeyError if none exists.",
            "Ensure codes are unique across multiple shorten calls (hint: collision check or random with retry).",
            "Include at least two unit tests demonstrating shortening / resolving and handling of an unknown code.",
        ],
        "evaluation_criteria": [
            "Correctness: Methods behave as specified and tests pass.",
            "Robustness: Proper validation and error handling are present.",
            "Code Quality: Readable, documented, and logically organised (may include a separate utilities module).",
            "Completeness: All requirements are satisfied including tests.",
        ],
    }

    run_example(problem_config, max_iters=12, verbose=True)


if __name__ == "__main__":
    main()
