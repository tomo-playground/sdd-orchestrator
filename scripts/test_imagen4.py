from google.genai import Client, types
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
api_key = os.getenv("GEMINI_API_KEY")
client = Client(api_key=api_key)

try:
    print("Testing imagen-4.0-generate-001...")
    response = client.models.generate_images(
        model="imagen-4.0-generate-001",
        prompt="A simple cat",
        config=types.GenerateImagesConfig(number_of_images=1)
    )
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")
