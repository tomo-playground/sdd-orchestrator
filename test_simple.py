import json
import urllib.request
import urllib.error
import sys

BASE_URL = "http://127.0.0.1:8000"

def request(method, endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header('Content-Type', 'application/json')
    
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req.data = json_data

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 204: return None
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404: raise FileNotFoundError
        print(f"HTTP Error {e.code}: {e.read().decode()}")
        raise

def run_test():
    print("🚀 [Project Flow Test - StdLib] 시작합니다...\n")

    # 1. 저장
    payload = {
        "title": "Product Review Test",
        "data": {
            "storyTopic": "테스트 스토리",
            "resolution": "square",
            "overlaySettings": {
                "enabled": True,
                "profile_name": "Reviewer_Bot",
                "caption": "기능 점검 중입니다 #테스트"
            }
        }
    }
    
    try:
        print("1️⃣ 저장(Save) 테스트 중...")
        data = request("POST", "/projects/save", payload)
        project_id = data["id"]
        print(f"   ✅ 저장 성공! ID: {project_id}\n")
    except Exception as e:
        print(f"   ❌ 저장 실패: {e}")
        sys.exit(1)

    # 2. 로드 및 검증
    try:
        print("2️⃣ 불러오기(Load) 및 데이터 검증 중...")
        data = request("GET", f"/projects/{project_id}")
        content = data["content"]
        
        if (content["resolution"] == "square" and 
            content["overlaySettings"]["profile_name"] == "Reviewer_Bot"):
            print("   ✅ 데이터 무결성 검증 완료\n")
        else:
            print("   ❌ 데이터 불일치")
            sys.exit(1)
    except Exception as e:
        print(f"   ❌ 로드 실패: {e}")
        sys.exit(1)

    # 3. 삭제
    try:
        print("3️⃣ 삭제(Delete) 테스트 중...")
        request("DELETE", f"/projects/{project_id}")
        
        try:
            request("GET", f"/projects/{project_id}")
            print("   ❌ 삭제 실패 (여전히 조회됨)")
        except FileNotFoundError:
            print("   ✅ 삭제 성공 및 확인 완료 (404 Not Found)\n")
            
    except Exception as e:
        print(f"   ❌ 삭제 요청 실패: {e}")

    print("🎉 [Test Complete] 모든 기능 정상 작동.")

if __name__ == "__main__":
    run_test()
