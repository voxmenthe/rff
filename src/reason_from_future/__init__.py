"""Reason-from-Future – Near-Executable Reference Implementation.

This package contains a domain-agnostic controller implementing the
Reason-from-Future algorithm with example domain specs.  See
`PLANS/inital_setup.md` for the original design rationale.
"""

from __future__ import annotations

# Core abstractions and controller
from .core import ProblemSpec, Workspace, LocalCheckFail, reason_from_future

# LLM interface
from .llm import llm_call

# Example problem specifications
from .specs import Game24Spec, GSM8KSpec

__all__ = [
    # from .core
    "ProblemSpec",
    "Workspace",
    "LocalCheckFail",
    "reason_from_future",
    # from .llm
    "llm_call",
    # from .specs
    "Game24Spec",
    "GSM8KSpec",
]
