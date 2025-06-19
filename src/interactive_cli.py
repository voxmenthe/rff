import re
from typing import List, Tuple, Type

from reason_from_future.core import reason_from_future
from reason_from_future.specs import Game24Spec, GSM8KSpec, CodeWritingSpec, GeneralProblemSolvingSpec

SpecEntry = Tuple[str, Type]

AVAILABLE_SPECS: dict[str, SpecEntry] = {
    "1": ("Game24", Game24Spec),
    "2": ("GSM8K", GSM8KSpec),
    "3": ("Code Writing", CodeWritingSpec),
    "4": ("General Problem Solving", GeneralProblemSolvingSpec),
}

def select_spec() -> Tuple[Type | None, str]:
    print("Available problem specs:")
    for key, (name, _) in AVAILABLE_SPECS.items():
        print(f" {key}. {name}")
    choice = input("Select a problem type: ").strip()
    if choice not in AVAILABLE_SPECS:
        print("Invalid choice")
        return None, ""
    return AVAILABLE_SPECS[choice][1], AVAILABLE_SPECS[choice][0]

def parse_int_list(text: str) -> List[int]:
    return [int(n) for n in re.split(r"[\s,]+", text.strip()) if n]

def build_spec(spec_cls: Type) -> Tuple[object | None, str]:
    if spec_cls is Game24Spec:
        nums_raw = input("Enter four numbers separated by space or comma: ")
        nums = parse_int_list(nums_raw)
        return Game24Spec(nums), f"Reach 24 with numbers {nums}"
    if spec_cls is GSM8KSpec:
        question = input("Enter the GSM8K question: ")
        answer = input("Enter the gold answer (number): ")
        return GSM8KSpec({"question": question, "answer": answer}), question
    if spec_cls is CodeWritingSpec:
        stmt = input("Describe the coding problem: ")
        lang = input("Language [python]: ").strip() or "python"
        req = input("Optional requirements (comma separated) [none]: ").strip()
        req_list = [r.strip() for r in req.split(',')] if req else []
        cfg = {
            "problem_statement": stmt,
            "language": lang,
            "requirements": req_list,
            "evaluation_criteria": [],
        }
        return CodeWritingSpec(cfg), stmt
    if spec_cls is GeneralProblemSolvingSpec:
        stmt = input("Describe the problem: ")
        ptype = input("Problem type [general]: ").strip() or "general"
        req = input("Requirements (comma separated) [none]: ").strip()
        req_list = [r.strip() for r in req.split(',')] if req else []
        cfg = {
            "problem_statement": stmt,
            "problem_type": ptype,
            "requirements": req_list,
            "evaluation_criteria": [],
        }
        return GeneralProblemSolvingSpec(cfg), stmt
    return None, ""

def main() -> None:
    spec_cls, _ = select_spec()
    if not spec_cls:
        return
    spec, problem = build_spec(spec_cls)
    if spec is None:
        return
    try:
        max_iters_str = input("Max iterations [8]: ").strip() or "8"
        max_iters = int(max_iters_str)
    except ValueError:
        max_iters = 8
    verbose = input("Verbose output? (y/N): ").strip().lower() == "y"
    try:
        result = reason_from_future(
            problem=problem,
            spec=spec,
            max_iters=max_iters,
            require_gold=False,
            verbose=verbose,
        )
        print("\nFINAL RESULT:\n" + result)
    except Exception as exc:
        print(f"\nFailed to solve problem: {exc}")


if __name__ == "__main__":
    main()
