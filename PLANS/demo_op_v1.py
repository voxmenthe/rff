"""Demo script showing GeneralProblemSolvingSpec in action."""
from reason_from_future.core import reason_from_future
from reason_from_future.specs.general_problem_solving import GeneralProblemSolvingSpec

# Example 1: System Design Problem
system_design_problem = {
    "problem_statement": "Design a scalable URL shortening service like TinyURL that can handle 100M requests per day",
    "problem_type": "system_design",
    "requirements": [
        "Handle 100M requests/day (1000+ requests/second)",
        "Sub-100ms latency for URL resolution",
        "Custom aliases support",
        "Analytics and click tracking",
        "High availability (99.9% uptime)"
    ],
    "evaluation_criteria": [
        "Scalability of the design",
        "Clear component separation",
        "Well-defined APIs",
        "Appropriate technology choices",
        "Consideration of edge cases"
    ]
}

# Example 2: Strategic Planning Problem
strategic_planning_problem = {
    "problem_statement": "Create a go-to-market strategy for launching a new AI-powered code review tool for enterprise customers",
    "problem_type": "strategic_planning",
    "requirements": [
        "Target Fortune 500 companies",
        "6-month launch timeline",
        "Limited initial budget ($500K)",
        "Must differentiate from GitHub Copilot",
        "Focus on security and compliance features"
    ],
    "evaluation_criteria": [
        "Clear market positioning",
        "Realistic timeline with milestones",
        "Defined customer acquisition strategy",
        "Competitive differentiation",
        "Risk mitigation plan"
    ]
}

# Example 3: Complex Decision Making
decision_making_problem = {
    "problem_statement": "Decide on the optimal cloud architecture migration strategy for a legacy monolithic e-commerce application with 1M daily users",
    "problem_type": "decision_making",
    "requirements": [
        "Minimal downtime during migration",
        "Maintain current performance levels",
        "Budget constraint of $2M",
        "Complete within 12 months",
        "Team has limited cloud experience"
    ],
    "evaluation_criteria": [
        "Risk assessment completeness",
        "Cost-benefit analysis",
        "Phased migration approach",
        "Team skill development plan",
        "Rollback strategies"
    ]
}

def run_example(problem_config, max_iters=10, verbose=True):
    """Run RFF with GeneralProblemSolvingSpec on a given problem."""
    print(f"\n{'='*60}")
    print(f"Problem: {problem_config['problem_statement'][:100]}...")
    print(f"Type: {problem_config['problem_type']}")
    print(f"{'='*60}\n")
    
    spec = GeneralProblemSolvingSpec(problem_config)
    
    try:
        solution = reason_from_future(
            problem=problem_config["problem_statement"],
            spec=spec,
            max_iters=max_iters,
            min_iters=3,  # Ensure some exploration
            require_gold=False,  # No gold standard for these problems
            verbose=verbose
        )
        
        print("\n" + "="*60)
        print("FINAL SOLUTION:")
        print("="*60)
        print(solution)
        
        return solution
        
    except RuntimeError as e:
        print(f"\nFailed to find complete solution: {e}")
        # Could still extract partial solution from state if needed
        return None

def main():
    """Run demonstrations of different problem types."""
    
    # You can choose which example to run
    examples = {
        "1": ("System Design", system_design_problem),
        "2": ("Strategic Planning", strategic_planning_problem),
        "3": ("Decision Making", decision_making_problem)
    }
    
    print("Available examples:")
    for key, (name, _) in examples.items():
        print(f"{key}: {name}")
    
    # For automated demo, run the system design example
    choice = "1"  # Change this to run different examples
    
    if choice in examples:
        name, problem = examples[choice]
        print(f"\nRunning: {name}")
        solution = run_example(problem, max_iters=8, verbose=True)
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()