from api.mongo import company_collection

def get_prompt_context() -> str:
    """
    Fetch all active company knowledge and build AI context
    """
    docs = company_collection.find({"is_active": True})

    context_parts = []

    for doc in docs:
        content = doc.get("content")
        if content:
            context_parts.append(content)

    # Combine all docs into one context
    return "\n\n".join(context_parts)
