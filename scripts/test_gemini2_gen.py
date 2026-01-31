from google.genai import Client, types
import os
from dotenv import load_dotenv
import base64

load_dotenv("backend/.env")
api_key = os.getenv("GEMINI_API_KEY")
client = Client(api_key=api_key)

try:
    print("Testing gemini-2.0-flash-exp-image-generation...")
    # NOTE: The method name and model name might vary. 
    # Usually multimodal generation uses generate_content
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp-image-generation",
        contents="Generate an image of a simple cat"
    )
    
    # Check if there's an image in the response parts
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            print(f"Found inline data: {part.inline_data.mime_type}")
            with open("cat_test.png", "wb") as f:
                f.write(part.inline_data.data)
            print("Saved cat_test.png")
            break
    else:
        print("No image found in response.")
        print(f"Response text: {response.text}")
except Exception as e:
    print(f"Failed: {e}")
