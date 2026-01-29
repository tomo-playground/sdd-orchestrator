import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env variables
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '../.env')))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment.")
    sys.exit(1)

def get_civitai_info():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        target_loras = [
            'chibi-laugh', 
            'eureka_v9', 
            'flat_color', 
            'Gentle_Cubism_Light', 
            'blindbox_v1_mix', 
            'harukaze-doremi-casual', 
            'mha_midoriya-10'
        ]
        
        # Construct placeholders based on length
        placeholders = ', '.join([f"'{name}'" for name in target_loras])
        query = text(f"SELECT name, civitai_id, civitai_url, trigger_words FROM loras WHERE name IN ({placeholders})")
        
        result = conn.execute(query)
        
        print("--- LoRA Civitai Info ---")
        for row in result:
            print(f"LoRA: {row.name}")
            print(f"  ID: {row.civitai_id}")
            print(f"  URL: {row.civitai_url}")
            print(f"  Triggers: {row.trigger_words}")
            print("-" * 20)

if __name__ == "__main__":
    get_civitai_info()
