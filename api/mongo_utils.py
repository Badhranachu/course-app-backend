import os
from pymongo import MongoClient
from datetime import datetime
import re

def get_db():
    uri = os.getenv("MONGO_URI")
    if not uri:
        return None

    # timeout prevents gunicorn freeze
    client = MongoClient(uri, serverSelectionTimeoutMS=2000)
    return client["groq_chatbot"]


def get_prompt_context():
    try:
        db = get_db()
        if not db:
            return ""

        docs = db["company-details"].find({"is_active": True})

        context_blocks = []
        for doc in docs:
            context_blocks.append(
                f"{doc.get('type','').upper()}:\n{doc.get('content','')}"
            )

        return "\n\n".join(context_blocks)

    except Exception:
        # NEVER crash API
        return ""


def sanitize_email(email):
    return re.sub(r"[^a-zA-Z0-9]", "_", email)

import traceback
def save_user_chat(email, question, answer):
    try:
        db = get_db()
        if db is None:

            print("MongoDB not connected")
            return

        if not email:
            print("Email is missing")
            return

        safe_name = sanitize_email(email)
        collection_name = f"user_{safe_name}"

        print("Saving chat to collection:", collection_name)

        db[collection_name].insert_one({
            "email": email,
            "question": question,
            "answer": answer,
            "timestamp": datetime.utcnow()
        })

        print("Chat saved successfully")

    except Exception as e:
        print("MongoDB SAVE ERROR:", e)
        traceback.print_exc()
    