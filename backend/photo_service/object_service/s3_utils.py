import logging
import boto3
from botocore.exceptions import ClientError
import os
import logging
import constants

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s | %(levelname)-8s | "
                           "%(module)s:%(funcName)s:%(lineno)d - %(message)s")
logger = logging.getLogger(__name__)

AWS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "aws_secret_access_key")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "aws_access_key_id")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def upload_file(file_path: str, bucket_name: str, object_name: str = ""):

    # If S3 object_name was not specified, use file_name
    if object_name == "":
        object_name = os.path.basename(file_path)

    # Upload the file
    s3_client = boto3.client(
        's3',
        aws_secret_access_key=AWS_KEY,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        region_name=AWS_REGION
    )
    try:
        response = s3_client.upload_file(file_path, bucket_name, object_name)

    except ClientError as e:
        logging.error(e)
        return False

    return True


def create_presigned_url(bucket_name, object_name, expiration=3600):
    # expiration in secs

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client(
        's3',
        aws_secret_access_key=AWS_KEY,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        region_name=AWS_REGION
    )
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_name},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logger.warning(f"Error generating presigned URL: {e}")
        return None

    return response


def delete_file(bucket_name, object_name):
    s3_client = boto3.client(
        's3',
        aws_secret_access_key=AWS_KEY,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        region_name=AWS_REGION
    )

    try:
        s3_client.delete_object(Bucket=bucket_name, Key=object_name)
        return True
    except ClientError as e:
        logger.warning(f"Error deleting file: {e}")
        return False


def upload_file_object(file_bytes: bytes, bucket_name: str, object_name: str):
    """Upload file bytes directly to S3"""
    s3_client = boto3.client(
        's3',
        aws_secret_access_key=AWS_KEY,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        region_name=AWS_REGION
    )
    try:
        s3_client.put_object(
            Body=file_bytes, Bucket=bucket_name, Key=object_name)
        return True
    except ClientError as e:
        logging.error(e)
        return False
