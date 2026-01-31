from google.genai import Client, types
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")
api_key = os.getenv("GEMINI_API_KEY")
client = Client(api_key=api_key)

try:
    print("Testing gemini-2.0-flash-exp-image-generation with generate_images...")
    response = client.models.generate_images(
        model="gemini-2.0-flash-exp-image-generation",
        prompt="A simple cat",
        config=types.GenerateImagesConfig(number_of_images=1)
    )
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")
