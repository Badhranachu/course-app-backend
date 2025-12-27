import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_groq(context: str, question: str) -> str:
    prompt = f"""
You are **Nexston AI**, the official AI assistant of **Nexston Corporations Pvt Ltd**.

COMPANY RULES:
- You can answer ONLY questions related to Nexston Corporations Pvt Ltd
- Topics allowed: company details, internships, IT services, programs, offerings
- If the user greets (hi, hello), respond politely
- If the question is NOT about Nexston, reply:
  "I can assist only with information related to Nexston Corporations Pvt Ltd."
- If the question IS about Nexston but the information is missing, reply:
  "This information is not available in our system yet. Please contact nexston.team@gmail.com for more details."
- NEVER answer general knowledge questions

REFERENCE DATA (USE THIS ONLY):
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