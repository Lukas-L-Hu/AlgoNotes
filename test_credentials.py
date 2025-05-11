import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_session_token = os.getenv("AWS_SESSION_TOKEN")
region = os.getenv("AWS_REGION", "us-east-1")  # Default to us-east-1 if not specified

# Print credential lengths (not the actual values for security)
print(f"AWS Access Key length: {len(aws_access_key) if aws_access_key else 'Not found'}")
print(f"AWS Secret Key length: {len(aws_secret_key) if aws_secret_key else 'Not found'}")
print(f"AWS Session Token length: {len(aws_session_token) if aws_session_token else 'None or not found'}")
print(f"AWS Region: {region}")

# Try creating a boto3 session
print("\nTesting boto3 session creation...")
try:
    session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        aws_session_token=aws_session_token,
        region_name=region
    )
    print("Session created successfully")
    
    # Test S3 access
    print("\nTesting S3 access...")
    s3 = session.client('s3')
    response = s3.list_buckets()
    print(f"S3 access successful. Found {len(response['Buckets'])} buckets:")
    for bucket in response['Buckets']:
        print(f"- {bucket['Name']}")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nPossible issues:")
    print("1. Incorrect AWS credentials")
    print("2. Missing or expired session token (if using temporary credentials)")
    print("3. IAM permissions issue")
    print("4. Network connectivity issue")

print("\nSuggestions if credentials aren't working:")
print("1. For AWS Studio/SageMaker: Make sure to include the AWS_SESSION_TOKEN")
print("2. Verify that you've copied the exact credentials without extra spaces")
print("3. Check if your credentials have expired (temporary credentials last ~1 hour)")
print("4. Try getting fresh credentials from the AWS Console or CLI")