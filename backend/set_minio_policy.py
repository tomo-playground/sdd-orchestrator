import json

import boto3


def set_bucket_public_policy():
    MINIO_URL = "http://localhost:9000"
    ACCESS_KEY = "admin"
    SECRET_KEY = "password123"
    BUCKET_NAME = "shorts-producer"

    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1",
    )

    # Public Read Policy 정의
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{BUCKET_NAME}"],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{BUCKET_NAME}/*"],
            },
        ],
    }

    print(f"Setting public read policy for bucket '{BUCKET_NAME}'...")
    s3.put_bucket_policy(Bucket=BUCKET_NAME, Policy=json.dumps(policy))
    print("Policy set successfully.")


if __name__ == "__main__":
    try:
        set_bucket_public_policy()
    except Exception as e:
        print(f"Error setting policy: {e}")
