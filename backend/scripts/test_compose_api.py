"""Test /prompt/compose API endpoint."""

import httpx

API_BASE = "http://127.0.0.1:8000"

# Test case 1: Simple tokens without LoRA
test_case_1 = {
    "tokens": ["masterpiece", "best_quality", "1girl", "smile", "standing", "classroom"],
    "mode": "auto",
    "loras": [],
    "is_break_enabled": True,
}

# Test case 2: With LoRA
test_case_2 = {
    "tokens": ["1girl", "smile", "standing", "classroom"],
    "mode": "auto",
    "loras": [
        {
            "name": "eureka_v9",
            "weight": 0.8,
            "trigger_words": ["Talho Yuki", "belt", "miniskirt"],
            "lora_type": "character",
            "optimal_weight": 0.8,
        }
    ],
    "is_break_enabled": True,
}


async def test_compose():
    async with httpx.AsyncClient() as client:
        print("=" * 60)
        print("Test Case 1: Simple tokens (no LoRA)")
        print("=" * 60)
        try:
            response = await client.post(f"{API_BASE}/prompt/compose", json=test_case_1, timeout=10.0)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("✅ Success!")
                print(f"Prompt: {result['prompt']}")
                print(f"Mode: {result['effective_mode']}")
            else:
                print(f"❌ Error: {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")

        print("\n" + "=" * 60)
        print("Test Case 2: With LoRA")
        print("=" * 60)
        try:
            response = await client.post(f"{API_BASE}/prompt/compose", json=test_case_2, timeout=10.0)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("✅ Success!")
                print(f"Prompt: {result['prompt']}")
                print(f"Mode: {result['effective_mode']}")
            else:
                print(f"❌ Error: {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_compose())
