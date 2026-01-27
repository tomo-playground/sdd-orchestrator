import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.storyboard import create_storyboard
from schemas import StoryboardRequest, StoryboardScene

async def test_gender_prompts():
    scenarios = [
        {"gender": "male", "topic": "A cool spy action scene"},
        {"gender": "female", "topic": "A cool spy action scene"}
    ]
    
    print("\n=== Testing Gemini Gender Bias in Prompts ===\n")
    
    for scenario in scenarios:
        gender = scenario["gender"]
        print(f"--- Scenario: {gender.upper()} Actor ---")
        
        request = StoryboardRequest(
            topic=scenario["topic"],
            duration=5,
            style="Anime",
            language="Korean",
            structure="Monologue",
            actor_a_gender=gender
        )
        
        try:
            # We only generate the storyboard to check the prompt
            # Note: This calls the real Gemini API, so it consumes quota
            # create_storyboard is synchronous in the current implementation (based on file content)
            # wait, backend/services/storyboard.py uses gemini_client.models.generate_content which is sync?
            # Yes, the google-genai library client seems to be sync or used synchronously here.
            # But wait, create_storyboard is def (not async def).
            
            result_dict = create_storyboard(request)
            # Result is a dict {"scenes": [...]}, not an object with .scenes attribute
            
            if not result_dict or "scenes" not in result_dict:
                print("❌ Failed to generate storyboard")
                continue
                
            scenes_data = result_dict["scenes"]
            if not scenes_data:
                print("❌ No scenes generated")
                continue

            first_scene = scenes_data[0]
            # access as dict
            script = first_scene.get("script", "")
            image_prompt = first_scene.get("image_prompt", "")
            
            print(f"Script: {script}")
            print(f"Prompt: {image_prompt}")
            
            # Check for gender markers
            prompt_lower = image_prompt.lower()
            male_markers = ["1boy", "male", "man", "boy", "short hair"]
            female_markers = ["1girl", "female", "woman", "girl", "long hair", "skirt"]
            
            found_male = [m for m in male_markers if m in prompt_lower]
            found_female = [m for m in female_markers if m in prompt_lower]
            
            print(f"Found Male Markers: {found_male}")
            print(f"Found Female Markers: {found_female}")
            
            if gender == "male":
                if found_female and not found_male:
                    print("⚠️ WARNING: Female tags found for Male actor!")
                elif not found_male:
                    print("⚠️ WARNING: No explicit male tags found (might rely on character preset)")
                else:
                    print("✅ OK: Male tags present")
            else:
                if found_male and not found_female:
                    print("⚠️ WARNING: Male tags found for Female actor!")
                elif not found_female:
                    print("⚠️ WARNING: No explicit female tags found")
                else:
                    print("✅ OK: Female tags present")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            
        print("\n")

if __name__ == "__main__":
    asyncio.run(test_gender_prompts())
