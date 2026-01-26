import re

def clean_script_for_tts(raw_script: str) -> str:
    # Copied from backend/services/video.py
    clean = re.sub(
        r"[^	
]",
        "",
        raw_script
    )
    return clean.replace("'", "").strip()

test_str = "소수점은 1보다 작은 수를 나타내요. 0.1은 1/10! 0.5는 1/2과 같아요!"
cleaned = clean_script_for_tts(test_str)
print(f"Original: {test_str}")
print(f"Cleaned : {cleaned}")

if "/" not in cleaned:
    print("❌ Slash '/' was removed!")
else:
    print("✅ Slash '/' preserved.")
