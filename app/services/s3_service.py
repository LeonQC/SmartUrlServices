import boto3
import os
import io
from botocore.exceptions import ClientError
from fastapi import HTTPException


# Get S3 configuration from environment variables
def get_s3_config():
    return {
        "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "region_name": os.environ.get("AWS_REGION", "us-east-1"),
        "bucket_name": os.environ.get("S3_BUCKET_NAME")
    }


# Initialize S3 client
def get_s3_client():
    config = get_s3_config()
    return boto3.client(
        's3',
        aws_access_key_id=config["aws_access_key_id"],
        aws_secret_access_key=config["aws_secret_access_key"],
        region_name=config["region_name"]
    )


# Upload file to S3
def upload_file_to_s3(file_data, file_name, content_type):
    """
    Upload a file to S3

    Args:
        file_data: The binary data of the file to upload
        file_name: The name to give the file in S3 (including path)
        content_type: The MIME type of the file

    Returns:
        The URL of the uploaded file
    """
    try:
        s3_client = get_s3_client()
        bucket_name = get_s3_config()["bucket_name"]

        # Convert string data to bytes if needed
        if isinstance(file_data, str):
            file_data = file_data.encode('utf-8')

        # Create file-like object in memory
        file_obj = io.BytesIO(file_data)

        # Upload file to S3 - Removed ACL parameter
        s3_client.upload_fileobj(
            file_obj,
            bucket_name,
            file_name,
            ExtraArgs={
                'ContentType': content_type
                # Removed 'ACL': 'public-read' as it's not supported
            }
        )

        # Generate the URL for the uploaded file
        region = get_s3_config()["region_name"]
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_name}"
        return url

    except ClientError as e:
        print(f"Error uploading to S3: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file to S3")
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Check if file exists in S3
def file_exists_in_s3(file_name):
    """
    Check if a file exists in S3

    Args:
        file_name: The name of the file to check (including path)

    Returns:
        True if the file exists, False otherwise
    """
    try:
        s3_client = get_s3_client()
        bucket_name = get_s3_config()["bucket_name"]

        s3_client.head_object(
            Bucket=bucket_name,
            Key=file_name
        )
        return True
    except ClientError as e:
        # If error code is 404, file not found
        if e.response['Error']['Code'] == '404':
            return False
        # For other errors, log and return False
        print(f"Error checking file in S3: {e}")
        return False


# Get the URL for a file in S3
def get_s3_file_url(file_name):
    """
    Get the URL for a file in S3

    Args:
        file_name: The name of the file (including path)

    Returns:
        The URL of the file
    """
    bucket_name = get_s3_config()["bucket_name"]
    region = get_s3_config()["region_name"]
    return f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_name}"