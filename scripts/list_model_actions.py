from google.genai import Client
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
api_key = os.getenv("GEMINI_API_KEY")
client = Client(api_key=api_key)

pager = client.models.list()
for model in pager:
    if "image" in model.name.lower() or "imagen" in model.name.lower():
        print(f"{model.name}: {model.supported_actions}")
