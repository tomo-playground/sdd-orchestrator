import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from config import gemini_client


async def check_available_models():
    print("🔍 Checking available models with current API Key...")

    if not gemini_client:
        print("❌ Gemini Client not initialized. Check GEMINI_API_KEY.")
        return

    try:
        # Correct method for Google Gen AI SDK v1.0+
        # It's client.models.list()
        count = 0
        pager = gemini_client.models.list()

        print(f"{ 'Model Name':<40} | { 'Display Name'}")
        print("-" * 60)

        for model in pager:
            count += 1
            print(f"{model.name:<40} | {model.display_name}")

            # Check for image generation capability if attributes exist
            # Note: The SDK object attributes might vary, just printing name is safest first step.

        print("-" * 60)
        print(f"✅ Found {count} models.")

    except Exception as e:
        print(f"❌ Failed to list models: {e}")
        # Try fallback for older SDK versions or different structures
        try:
            import google.generativeai as genai
            print("\n🔄 Trying legacy genai.list_models()...")
            for m in genai.list_models():
                print(f"{m.name:<40} | {m.supported_generation_methods}")
        except Exception as e2:
            print(f"   Legacy check also failed: {e2}")

if __name__ == "__main__":
    asyncio.run(check_available_models())
