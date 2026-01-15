import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    print("🚀 [Project Flow Test] 시작합니다...\n")

    # 1. 프로젝트 저장 (복잡한 데이터 포함)
    payload = {
        "title": "Product Review Test",
        "data": {
            "storyTopic": "테스트 스토리",
            "storyDuration": 45,
            "resolution": "square",
            "characterDesc": "테스트 로봇",
            "overlaySettings": {
                "enabled": True,
                "profile_name": "Reviewer_Bot",
                "likes_count": "99.9k",
                "caption": "기능 점검 중입니다 #테스트"
            }
        }
    }
    
    try:
        print("1️⃣ 저장(Save) 테스트 중...")
        res = requests.post(f"{BASE_URL}/projects/save", json=payload)
        res.raise_for_status()
        data = res.json()
        project_id = data["id"]
        print(f"   ✅ 저장 성공! ID: {project_id}\n")
    except Exception as e:
        print(f"   ❌ 저장 실패: {e}")
        sys.exit(1)

    # 2. 목록 조회 및 확인
    try:
        print("2️⃣ 목록(List) 조회 테스트 중...")
        res = requests.get(f"{BASE_URL}/projects/list")
        projects = res.json()["projects"]
        found = any(p["id"] == project_id for p in projects)
        if found:
            print("   ✅ 목록에 프로젝트 존재 확인\n")
        else:
            print("   ❌ 목록에서 프로젝트를 찾을 수 없음")
            sys.exit(1)
    except Exception as e:
        print(f"   ❌ 목록 조회 실패: {e}")
        sys.exit(1)

    # 3. 상세 로드 및 데이터 검증
    try:
        print("3️⃣ 불러오기(Load) 및 데이터 검증 중...")
        res = requests.get(f"{BASE_URL}/projects/{project_id}")
        content = res.json()["content"]
        
        # 검증 포인트
        checks = [
            content["resolution"] == "square",
            content["overlaySettings"]["profile_name"] == "Reviewer_Bot",
            content["overlaySettings"]["caption"] == "기능 점검 중입니다 #테스트"
        ]
        
        if all(checks):
            print("   ✅ 데이터 무결성 검증 완료 (해상도, 오버레이 설정 보존됨)\n")
        else:
            print(f"   ❌ 데이터 불일치: {content}")
            sys.exit(1)
            
    except Exception as e:
        print(f"   ❌ 로드 실패: {e}")
        sys.exit(1)

    # 4. 삭제 테스트
    try:
        print("4️⃣ 삭제(Delete) 테스트 중...")
        requests.delete(f"{BASE_URL}/projects/{project_id}")
        
        # 삭제 확인
        res = requests.get(f"{BASE_URL}/projects/{project_id}")
        if res.status_code == 404:
            print("   ✅ 삭제 성공 및 확인 완료 (404 Not Found)\n")
        else:
            print("   ❌ 삭제되었으나 여전히 접근 가능함")
    except Exception as e:
        print(f"   ❌ 삭제 요청 실패: {e}")

    print("🎉 [Test Complete] 모든 기능이 정상 작동합니다.")

if __name__ == "__main__":
    run_test()
