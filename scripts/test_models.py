from google.genai import Client, types
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
api_key = os.getenv("GEMINI_API_KEY")
client = Client(api_key=api_key)

try:
    print("Testing gemini-2.5-flash-image...")
    response = client.models.generate_images(
        model="gemini-2.5-flash-image",
        prompt="A simple cat",
        config=types.GenerateImagesConfig(number_of_images=1)
    )
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")

try:
    print("\nTesting gemini-3-pro-image-preview...")
    response = client.models.generate_images(
        model="gemini-3-pro-image-preview",
        prompt="A simple cat",
        config=types.GenerateImagesConfig(number_of_images=1)
    )
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")
