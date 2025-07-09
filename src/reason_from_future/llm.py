"""LLM glue using Google GenAI SDK"""
import os
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def llm_call(
    prompt: str,
    *,
    model: str = "gemini-2.5-flash-preview-05-20",
    verbose: bool = False,
    tools: list | None = None,
) -> str:
    """Thin sync wrapper around the `google.genai` client."""
    if not GEMINI_API_KEY:
        raise EnvironmentError("GEMINI_API_KEY environment variable not set.")

    if verbose:
        print(f"--- LLM PROMPT ({model}) ---")
        print(prompt)
        print("---------------------------")

    # Build contents object per new SDK (single text part)
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

    cfg = None
    if tools:
        # Accept either Python callables or pre-built types.Tool instances.
        cfg = types.GenerateContentConfig(tools=tools)

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=cfg,
    )
    # If automatic function calling is enabled and the SDK handled it, the
    # final text is returned directly in ``response.text``.
    result_text = response.text
    if verbose:
        print(f"--- LLM RESPONSE ({model}) ---")
        print(result_text)
        print("----------------------------")
    return result_text
