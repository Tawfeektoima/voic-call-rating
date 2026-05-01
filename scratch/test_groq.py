import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=key)

try:
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": "Hello"}],
    )
    print("Groq OK:", completion.choices[0].message.content)
except Exception as e:
    print("Groq Error:", e)
