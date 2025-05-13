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

        # Upload file to S3
        s3_client.upload_fileobj(
            file_obj,
            bucket_name,
            file_name,
            ExtraArgs={
                'ContentType': content_type
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


def get_s3_file_url(file_name, expires_in=3600):
    """
    Get a pre-signed URL for a file in S3 that expires after a set time

    Args:
        file_name: The name of the file (including path)
        expires_in: Number of seconds until the pre-signed URL expires

    Returns:
        The pre-signed URL of the file
    """
    try:
        s3_client = get_s3_client()
        bucket_name = get_s3_config()["bucket_name"]

        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_name
            },
            ExpiresIn=expires_in
        )
        return url
    except Exception as e:
        print(f"Error generating pre-signed URL: {e}")
        return None

def delete_user_files(user_id):
    """
    Delete all S3 files associated with a user

    Args:
        user_id: The ID of the user whose files to delete

    Returns:
        bool: True if files were deleted successfully, False otherwise
    """
    try:
        s3_client = get_s3_client()
        bucket_name = get_s3_config()["bucket_name"]

        # Define prefixes for each type of user resource
        prefixes = [
            f"qrcodes/user_{user_id}/",
            f"barcodes/user_{user_id}/"
        ]

        deleted_count = 0

        # Check each prefix and delete matching objects
        for prefix in prefixes:
            # List objects with this prefix
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )

            # If objects found, delete them
            if 'Contents' in response and response['Contents']:
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]

                if objects_to_delete:
                    s3_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={'Objects': objects_to_delete}
                    )
                    deleted_count += len(objects_to_delete)
                    print(f"Deleted {len(objects_to_delete)} objects with prefix {prefix}")

        # Now find and delete specific QR code and barcode files by querying the database
        # This handles files that don't follow the prefix pattern
        from app.database import url_db
        conn = url_db.get_db()
        cursor = conn.cursor()

        # Get QR codes created by this user
        cursor.execute("SELECT qr_code_id FROM qrcodes WHERE user_id = %s", (user_id,))
        qr_codes = cursor.fetchall()
        qr_objects = []
        for qr_code in qr_codes:
            qr_objects.append({'Key': f"qrcodes/{qr_code[0]}.png"})

        # Get barcodes created by this user
        cursor.execute("SELECT barcode_id FROM barcodes WHERE user_id = %s", (user_id,))
        barcodes = cursor.fetchall()
        barcode_objects = []
        for barcode in barcodes:
            barcode_objects.append({'Key': f"barcodes/{barcode[0]}.png"})

        cursor.close()
        conn.close()

        # Delete the QR code files
        if qr_objects:
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': qr_objects}
            )
            deleted_count += len(qr_objects)
            print(f"Deleted {len(qr_objects)} QR code files")

        # Delete the barcode files
        if barcode_objects:
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': barcode_objects}
            )
            deleted_count += len(barcode_objects)
            print(f"Deleted {len(barcode_objects)} barcode files")

        print(f"Total deleted files for user {user_id}: {deleted_count}")
        return True

    except Exception as e:
        print(f"Error deleting user files from S3: {e}")
        return False