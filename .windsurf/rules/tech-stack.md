---
trigger: always_on
---

When implementing gemini-related features, this codebase uses the new google-genai SDK (documentation can be found at https://googleapis.github.io/python-genai/ and also here https://ai.google.dev/gemini-api/docs/text-generation).

Note that the SDK and its documentation has recently changed, so when implementing anything related to the gemini llm or its features, it is important to read the current documentation to understand how to use it, and make sure we are using the latest version - you **CANNOT** use your existing knowledge here but must instead make sure to read the documentation, understand it, and document your findings, and use those in your implementation.

When running any of the code in this project, you will need to first activate the local Python environment using `source .venv/bin/activate`