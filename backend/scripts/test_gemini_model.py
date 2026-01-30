
import os
import sys

sys.path.append(os.getcwd())

from config import GEMINI_TEXT_MODEL, gemini_client


def test_model():
    if not gemini_client:
        print("Gemini client not initialized (API key missing?)")
        return

    print(f"Testing model: {GEMINI_TEXT_MODEL}")
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents="Hello, are you working?",
        )
        print("Success! Response:", response.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_model()
