def build_prompt(query, context_chunks):
    context_text = "\n\n".join([c["text"] for c in context_chunks])
    return f"""You are a helpful assistant. You use the context below to answer the question.

            Context:
            {context_text}

            Question: {query}
            Answer:"""
    