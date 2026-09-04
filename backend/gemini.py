import os
from google import genai

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def ask_gemini(prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    return response.text
