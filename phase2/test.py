# test.py - Updated for new SDK
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    from google import genai
    client = genai.Client(api_key=api_key)
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say 'Hello, LLVM!'"
    )
    print(response.text)
else:
    print("API key not found!")