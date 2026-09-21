import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def get_gemini_client() -> genai.Client:
    """
    Initializes a highly-secure genai.Client instance without hardcoded credentials.
    Requires GEMINI_API_KEY in the environment.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("CRITICAL ERROR: GEMINI_API_KEY is missing or unconfigured in the environment. Cannot perform secure AI planning.")
    
    return genai.Client(api_key=api_key)
