# LLM Prompts - Contract Analysis API

This folder contains all LLM prompts used in the system, extracted verbatim from the code with rationale explanations.

## Files

1. **extraction_prompt.txt** - Field extraction from contracts
2. **audit_prompt.txt** - Risk detection and auditing
3. **rag_system_prompt.txt** - RAG question answering
4. **prompts_rationale.md** - Design decisions and rationale

---

## Usage

These prompts are used in the following endpoints:

- `/extract` → `extraction_prompt.txt`
- `/audit` → `audit_prompt.txt`
- `/ask` and `/ask/stream` → `rag_system_prompt.txt`

---

## Prompt Engineering Best Practices

1. **Clear Instructions**: Explicit, step-by-step instructions
2. **Output Format**: Specify JSON structure exactly
3. **Constraints**: Define what to do when information is missing
4. **Examples**: Include few-shot examples when needed
5. **Temperature**: Use 0 for structured output, 0.7 for creative responses
