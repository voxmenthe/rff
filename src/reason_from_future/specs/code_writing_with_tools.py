from __future__ import annotations

"""Code writing spec that exposes file I/O helper tools to Gemini.

This variant augments the original :pyclass:`CodeWritingSpec` with
metadata describing two simple tools: ``read_file`` and ``write_to_file``.
The extra context is appended to both reverse- and forward-planning prompts
so the LLM is aware it can use them to inspect or modify the workspace on
its own rather than inlining large blobs of code in the response.

For now we **only** expose the *description* of the tools inside the prompt –
actual execution is handled by :pymod:`reason_from_future.tools`.  At a later
stage the controller can be updated to pass the structured *tools* argument
supported by ``google.genai`` so Gemini can issue function-call responses.
"""

from typing import List, Dict, Any, Set
import json
import textwrap

from ..tools import read_file, write_to_file  # noqa: F401 – imported for introspection
from .code_writing import CodeWritingSpec
from ..core import Workspace


class CodeWritingWithToolsSpec(CodeWritingSpec):
    """Same as :class:`CodeWritingSpec` but advertises file-I/O tools."""

    # ---------------------------------------------------------------------
    # Helper – build tool schema & human readable list
    # ---------------------------------------------------------------------
    def _tool_schemas(self) -> List[Dict[str, Any]]:
        """Return JSONSchema-like dicts suitable for ``tools=[...]`` arg."""
        return [
            {
                "name": "read_file",
                "description": "Return the UTF-8 text contents of the requested file path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute or relative path to the file you want to read."
                        }
                    },
                    "required": ["file_path"],
                },
            },
            {
                "name": "write_to_file",
                "description": "Write *content* to *file_path*, creating parents as needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Destination path."
                        },
                        "content": {
                            "type": "string",
                            "description": "Text to be written inside the file."
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "Whether to replace an existing file (default true).",
                            "default": True,
                        },
                    },
                    "required": ["file_path", "content"],
                },
            },
        ]

    def _human_tool_list(self) -> str:
        """Return a bullet list describing the available tools."""
        items = []
        for schema in self._tool_schemas():
            sig_parts = [p for p in schema["parameters"]["properties"].keys()]
            items.append(f"- {schema['name']}({', '.join(sig_parts)}) – {schema['description']}")
        return "\n".join(items)

    # ------------------------------------------------------------------
    # Prompt builders overriding base spec
    # ------------------------------------------------------------------
    def prompt_last_step(self, state: Workspace, target: str, avoid: Set[str]) -> str:  # noqa: D401 – keep same signature
        base = super().prompt_last_step(state, target, avoid)
        tool_info = f"\n\nYou can call the following *tools* when needed by outputting a valid tool invocation (see examples in the Gemini docs):\n{self._human_tool_list()}"
        return base + tool_info

    def prompt_forward_step(self, state: Workspace, target_step: str, avoid: Set[str]):  # noqa: D401
        base = super().prompt_forward_step(state, target_step, avoid)
        tool_info = f"\n\nRemember: the tools at your disposal are:\n{self._human_tool_list()}\nIf reading or writing a file would help complete the task, emit an appropriate tool call instead of inlining the file contents."
        return base + tool_info
