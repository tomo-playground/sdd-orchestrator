import os

import boto3
from botocore.exceptions import ClientError


def test_minio_upload():
    # MinIO 설정 (로컬 환경 기준)
    MINIO_URL = "http://localhost:9000"
    ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
    SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
    BUCKET_NAME = "shorts-producer"

    # S3 호환 클라이언트 생성
    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1",  # MinIO는 region이 필수적이지 않지만 보통 기본값 사용
    )

    # 1. 버킷 존재 확인 및 생성
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' already exists.")
    except ClientError:
        print(f"Creating bucket '{BUCKET_NAME}'...")
        s3.create_bucket(Bucket=BUCKET_NAME)

    # 2. 테스트용 경로 구조 정의 (프로젝트 - 그룹 - 스토리보드)
    # 실제 환경에서는 DB ID를 사용하겠지만, 여기서는 'test'용으로 생성
    project_id = "p_test_channel"
    group_id = "g_test_series"
    storyboard_id = "s_test_content"

    # 3. 테스트 파일 생성 및 업로드
    test_files = [
        {"name": "test_image.txt", "content": "This is a fake image content.", "type": "images"},
        {"name": "test_video.txt", "content": "This is a fake video content.", "type": "videos"},
    ]

    for file_info in test_files:
        # Prefix 형식: projects/{p_id}/groups/{g_id}/storyboards/{s_id}/{type}/{filename}
        key = f"projects/{project_id}/groups/{group_id}/storyboards/{storyboard_id}/{file_info['type']}/{file_info['name']}"

        print(f"Uploading to: {key} ...")
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=file_info['content'],
            ContentType="text/plain"
        )
        print(f"Successfully uploaded {file_info['name']}")

if __name__ == "__main__":
    try:
        test_minio_upload()
    except Exception as e:
        print(f"Error during test upload: {e}")
