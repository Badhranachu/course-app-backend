import os
from pymongo import MongoClient
from datetime import datetime
import re

client = MongoClient(os.getenv("MONGO_URI"))
db = client["groq_chatbot"]


# 🔹 Fetch AI prompt/reference data
def get_prompt_context():
    docs = db["company-details"].find({"is_active": True})

    context_blocks = []
    for doc in docs:
        context_blocks.append(
            f"{doc.get('type').upper()}:\n{doc.get('content')}"
        )

    return "\n\n".join(context_blocks)


# 🔹 Save user chat (username = collection name)
def sanitize_email(email):
    return re.sub(r"[^a-zA-Z0-9]", "_", email)


def save_user_chat(email, question, answer):
    safe_name = sanitize_email(email)
    collection_name = f"user_{safe_name}"
    collection = db[collection_name]

    collection.insert_one({
        "email": email,
        "question": question,
        "answer": answer,
        "timestamp": datetime.utcnow()
    })
