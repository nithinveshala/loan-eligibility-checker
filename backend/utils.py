"""
Shared utilities for Lambda functions.

Provides common helpers for DynamoDB interactions, API Gateway response
formatting, input parsing, and AWS service client initialization.
"""

import json
import os
import uuid
import decimal
from datetime import datetime, timezone

import boto3


# Environment variables for AWS resource names
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "LoanApplications")
S3_BUCKET = os.environ.get("S3_BUCKET", "loan-eligibility-documents")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "")

# AWS service clients (reused across invocations for connection pooling)
dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")
sns_client = boto3.client("sns")
sqs_client = boto3.client("sqs")
table = dynamodb.Table(DYNAMODB_TABLE)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal types from DynamoDB."""

    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            # Convert to int if there is no fractional part, else to float
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


def generate_id() -> str:
    """Generate a unique application ID using UUID4."""
    return str(uuid.uuid4())


def get_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def build_response(status_code: int, body: dict) -> dict:
    """
    Build a properly formatted API Gateway response.

    Args:
        status_code: HTTP status code (200, 400, 404, 500, etc.).
        body: Dictionary to be serialized as the response body.

    Returns:
        A dictionary with statusCode, headers (including CORS), and body.
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def parse_body(event: dict) -> dict:
    """
    Parse the request body from an API Gateway event.

    Handles both direct dictionary bodies and JSON string bodies.

    Args:
        event: The Lambda event object from API Gateway.

    Returns:
        A dictionary parsed from the request body.

    Raises:
        ValueError: If the body is missing or contains invalid JSON.
    """
    body = event.get("body")
    if body is None:
        raise ValueError("Request body is missing")
    if isinstance(body, str):
        return json.loads(body)
    return body


def get_path_param(event: dict, param: str) -> str:
    """
    Extract a path parameter from the API Gateway event.

    Args:
        event: The Lambda event object.
        param: The name of the path parameter to extract.

    Returns:
        The string value of the path parameter.

    Raises:
        ValueError: If the path parameter is missing.
    """
    params = event.get("pathParameters") or {}
    value = params.get(param)
    if not value:
        raise ValueError(f"Missing path parameter: {param}")
    return value


def send_sns_notification(subject: str, message: str, email: str = None) -> None:
    """
    Publish a notification to the SNS topic.

    Args:
        subject: The subject line of the notification.
        message: The body text of the notification.
        email: Optional specific email to target (uses topic default if None).
    """
    if not SNS_TOPIC_ARN:
        print("SNS_TOPIC_ARN not configured, skipping notification")
        return

    try:
        params = {
            "TopicArn": SNS_TOPIC_ARN,
            "Subject": subject,
            "Message": message,
        }
        sns_client.publish(**params)
        print(f"SNS notification sent: {subject}")
    except Exception as e:
        # Log but do not fail the main operation if notification fails
        print(f"Failed to send SNS notification: {str(e)}")


def send_to_sqs(message_body: dict) -> None:
    """
    Send a message to the SQS processing queue.

    Args:
        message_body: Dictionary to be sent as the message body.
    """
    if not SQS_QUEUE_URL:
        print("SQS_QUEUE_URL not configured, skipping queue message")
        return

    try:
        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message_body, cls=DecimalEncoder),
        )
        print("Message sent to SQS queue")
    except Exception as e:
        print(f"Failed to send SQS message: {str(e)}")


def generate_presigned_url(object_key: str, expiration: int = 3600) -> str:
    """
    Generate a presigned URL for uploading a document to S3.

    Args:
        object_key: The S3 object key for the upload target.
        expiration: URL expiration time in seconds (default 1 hour).

    Returns:
        A presigned URL string for PUT upload.
    """
    try:
        url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": S3_BUCKET, "Key": object_key},
            ExpiresIn=expiration,
        )
        return url
    except Exception as e:
        print(f"Failed to generate presigned URL: {str(e)}")
        return ""
