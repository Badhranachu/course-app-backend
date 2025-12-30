import os


from groq import Groq
import os
import traceback

try:
    from groq import Groq
except ImportError:
    Groq = None

def ask_groq(context: str, question: str) -> str:
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "AI service not configured."

        client = Groq(api_key=api_key)

        prompt = f"""
You are Nexston AI, the official AI assistant of Nexston Corporations Pvt Ltd.

REFERENCE DATA:
{context}

USER QUESTION:
{question}
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("GROQ ERROR:", e)
        traceback.print_exc()
        return "AI service unavailable."