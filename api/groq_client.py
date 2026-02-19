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

        system_prompt = f"""
You are Nexston AI, the official assistant of Nexston Corporations Pvt Ltd.

STRICT RULES:
1. Answer ONLY using the provided REFERENCE DATA.
2. If the answer is not found in REFERENCE DATA, reply:
   "The requested information is not available in the supported knowledge scope. Please contact support@nexston.in."
3. Do NOT guess.
4. Do NOT assume.
5. Do NOT use external knowledge.
6. Do NOT calculate age unless founding year is explicitly provided in REFERENCE DATA.

REFERENCE DATA:
{context}
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0,
            max_tokens=400
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("GROQ ERROR:", e)
        traceback.print_exc()
        return "AI service unavailable."
