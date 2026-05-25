def build_prompt(question: str, chunks: list):
    context = "\n\n".join(
        [c["chunk_text"] for c in chunks]
    )

    return f"""
You are an SAT tutor.

Use the context below to answer the student's question clearly.

CONTEXT:
{context}

QUESTION:
{question}

Rules:
- Explain step by step
- Keep it simple
- Give reasoning
"""