"""LLM glue using Google GenAI SDK"""
import os

from google import genai # new SDK – *not* google.generativeai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def llm_call(
    prompt: str,
    *,
    model: str = "gemini-2.5-flash-preview-05-20",
    max_tokens: int = 256,
    temperature: float = 0.3,
    verbose: bool = False,
) -> str:
    """Thin sync wrapper around the `google.genai` client."""
    if not GEMINI_API_KEY:
        raise EnvironmentError("GEMINI_API_KEY environment variable not set.")

    if verbose:
        print(f"--- LLM PROMPT ({model}) ---")
        print(prompt)
        print("---------------------------")

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=model,
        contents=[prompt]
    )
    result_text = response.text  # type: ignore[attr-defined]
    if verbose:
        print(f"--- LLM RESPONSE ({model}) ---")
        print(result_text)
        print("----------------------------")
    return result_text
