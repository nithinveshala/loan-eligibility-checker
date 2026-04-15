"""
Unified Lambda handler for the Loan Eligibility Checker API.

This single Lambda function handles all CRUD operations via Lambda
Function URL. It routes requests based on HTTP method and path,
replacing the need for API Gateway.

Supports:
  GET    /applications          - List all applications
  GET    /applications/{id}     - Get single application
  POST   /applications          - Create new application
  PUT    /applications/{id}     - Update application
  DELETE /applications/{id}     - Delete application
"""

import json
import sys
import os
import uuid
import traceback
from decimal import Decimal
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

# Add the library to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from loan_eligibility_engine import (
    EligibilityCalculator,
    LoanApplication,
    Applicant,
)
from loan_eligibility_engine.models import LoanType, EmploymentType


# ------------------------------------------------------------------
# AWS Resource Configuration
# ------------------------------------------------------------------
REGION = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "lec-applications")
DOCUMENTS_BUCKET = os.environ.get("S3_BUCKET", "lec-documents")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
PROCESS_FUNCTION = os.environ.get("PROCESS_FUNCTION", "lec-process-application")

# AWS clients (reused across invocations)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
s3_client = boto3.client("s3", region_name=REGION)
sns_client = boto3.client("sns", region_name=REGION)
lambda_client = boto3.client("lambda", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)


# ------------------------------------------------------------------
# Utility Helpers
# ------------------------------------------------------------------
class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that converts DynamoDB Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def build_response(status_code, body):
    """Build an HTTP response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def to_decimal(obj):
    """Recursively convert floats to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_decimal(i) for i in obj]
    return obj


def parse_body(event):
    """Parse JSON body from the Lambda Function URL event."""
    body = event.get("body", "")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode("utf-8")
    return json.loads(body)


def extract_path_id(path):
    """Extract the application ID from the URL path."""
    # Path format: /applications/{id}
    parts = path.strip("/").split("/")
    if len(parts) >= 2:
        return parts[1]
    return None


def send_notification(subject, message):
    """Publish a notification to the SNS topic."""
    if not SNS_TOPIC_ARN:
        return
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject[:100],  # SNS subject max 100 chars
            Message=message,
        )
    except Exception as e:
        print(f"SNS notification failed: {e}")


def generate_presigned_url(key, expiration=3600):
    """Generate a presigned S3 URL for document upload."""
    try:
        return s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": DOCUMENTS_BUCKET, "Key": key},
            ExpiresIn=expiration,
        )
    except Exception as e:
        print(f"Presigned URL generation failed: {e}")
        return ""


# ------------------------------------------------------------------
# Eligibility Processing (uses the custom library)
# ------------------------------------------------------------------
def evaluate_eligibility(item):
    """
    Run the loan eligibility assessment using the custom library.

    Args:
        item: DynamoDB item dictionary with application data.

    Returns:
        Tuple of (result_dict, status_string).
    """
    emp_map = {
        "salaried": EmploymentType.SALARIED,
        "self_employed": EmploymentType.SELF_EMPLOYED,
        "freelancer": EmploymentType.FREELANCER,
        "unemployed": EmploymentType.UNEMPLOYED,
        "retired": EmploymentType.RETIRED,
    }
    loan_map = {
        "personal": LoanType.PERSONAL,
        "home": LoanType.HOME,
        "auto": LoanType.AUTO,
        "education": LoanType.EDUCATION,
    }

    # Build Applicant from DB record
    applicant = Applicant(
        name=item.get("applicant_name", ""),
        age=int(item.get("age", 30)),
        annual_income=float(item.get("annual_income", 0)),
        employment_type=emp_map.get(
            str(item.get("employment_type", "salaried")).lower(),
            EmploymentType.SALARIED,
        ),
        credit_score=int(item.get("credit_score", 500)),
        existing_loans=int(item.get("existing_loans", 0)),
        monthly_expenses=float(item.get("monthly_expenses", 0)),
        years_of_employment=float(item.get("years_of_employment", 0)),
        has_collateral=bool(item.get("has_collateral", False)),
        dependents=int(item.get("dependents", 0)),
    )

    # Build LoanApplication
    loan_app = LoanApplication(
        applicant=applicant,
        loan_type=loan_map.get(
            str(item.get("loan_type", "personal")).lower(),
            LoanType.PERSONAL,
        ),
        loan_amount=float(item.get("loan_amount", 0)),
        loan_term_months=int(item.get("loan_term_months", 12)),
        purpose=item.get("purpose", ""),
    )

    # Evaluate using the custom library
    calculator = EligibilityCalculator()
    decision = calculator.evaluate(loan_app)

    result = decision.to_dict()
    status_map = {
        "approved": "approved",
        "conditional": "conditional",
        "denied": "denied",
        "pending_review": "under_review",
    }
    new_status = status_map.get(decision.status.value, "under_review")

    return result, new_status


# ------------------------------------------------------------------
# CRUD Handlers
# ------------------------------------------------------------------
def handle_create(event):
    """Handle POST /applications - Create a new loan application."""
    try:
        body = parse_body(event)
    except (json.JSONDecodeError, ValueError) as e:
        return build_response(400, {"error": f"Invalid JSON: {e}"})

    # Validate required fields
    required = [
        "applicant_name", "age", "annual_income", "employment_type",
        "credit_score", "loan_type", "loan_amount", "loan_term_months",
    ]
    missing = [f for f in required if f not in body or body[f] is None]
    if missing:
        return build_response(400, {
            "error": f"Missing required fields: {', '.join(missing)}"
        })

    app_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    item = {
        "application_id": app_id,
        "applicant_name": body["applicant_name"],
        "applicant_email": body.get("applicant_email", ""),
        "age": body["age"],
        "annual_income": body["annual_income"],
        "employment_type": body["employment_type"],
        "credit_score": body["credit_score"],
        "existing_loans": body.get("existing_loans", 0),
        "monthly_expenses": body.get("monthly_expenses", 0),
        "years_of_employment": body.get("years_of_employment", 0),
        "has_collateral": body.get("has_collateral", False),
        "dependents": body.get("dependents", 0),
        "loan_type": body["loan_type"],
        "loan_amount": body["loan_amount"],
        "loan_term_months": body["loan_term_months"],
        "purpose": body.get("purpose", ""),
        "status": "pending",
        "eligibility_result": None,
        "created_at": now,
        "updated_at": now,
    }

    item = to_decimal(item)
    table.put_item(Item=item)

    # Run eligibility evaluation immediately using the custom library
    try:
        result, new_status = evaluate_eligibility(item)
        result = to_decimal(result)

        table.update_item(
            Key={"application_id": app_id},
            UpdateExpression="SET eligibility_result = :r, #s = :st, updated_at = :ts",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":r": result,
                ":st": new_status,
                ":ts": datetime.now(timezone.utc).isoformat(),
            },
        )
        item["eligibility_result"] = result
        item["status"] = new_status
    except Exception as eval_err:
        print(f"Eligibility evaluation error: {eval_err}")
        traceback.print_exc()

    # Generate presigned URL for document upload to S3
    doc_key = f"documents/{app_id}/upload"
    upload_url = generate_presigned_url(doc_key)

    # Send SNS notification
    send_notification(
        subject=f"New Loan Application - {app_id[:8]}",
        message=(
            f"New loan application submitted.\n"
            f"ID: {app_id}\n"
            f"Applicant: {body['applicant_name']}\n"
            f"Type: {body['loan_type']}\n"
            f"Amount: {body['loan_amount']}\n"
            f"Status: {item.get('status', 'pending')}"
        ),
    )

    return build_response(201, {
        "message": "Application created successfully",
        "application_id": app_id,
        "upload_url": upload_url,
        "status": item.get("status", "pending"),
    })


def handle_list(event):
    """Handle GET /applications - List all applications."""
    params = event.get("queryStringParameters") or {}
    status_filter = params.get("status")
    type_filter = params.get("loan_type")

    scan_kwargs = {}
    filters = []
    expr_values = {}
    expr_names = {}

    if status_filter:
        filters.append("#s = :status")
        expr_values[":status"] = status_filter
        expr_names["#s"] = "status"

    if type_filter:
        filters.append("loan_type = :lt")
        expr_values[":lt"] = type_filter

    if filters:
        scan_kwargs["FilterExpression"] = " AND ".join(filters)
        scan_kwargs["ExpressionAttributeValues"] = expr_values
        if expr_names:
            scan_kwargs["ExpressionAttributeNames"] = expr_names

    response = table.scan(**scan_kwargs)
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return build_response(200, {
        "applications": items,
        "count": len(items),
    })


def handle_get(event, app_id):
    """Handle GET /applications/{id} - Get a single application."""
    response = table.get_item(Key={"application_id": app_id})
    item = response.get("Item")

    if not item:
        return build_response(404, {"error": f"Application {app_id} not found"})

    # List associated S3 documents
    try:
        prefix = f"documents/{app_id}/"
        s3_resp = s3_client.list_objects_v2(Bucket=DOCUMENTS_BUCKET, Prefix=prefix)
        docs = []
        for obj in s3_resp.get("Contents", []):
            url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": DOCUMENTS_BUCKET, "Key": obj["Key"]},
                ExpiresIn=3600,
            )
            docs.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "url": url,
            })
        item["documents"] = docs
    except Exception:
        item["documents"] = []

    return build_response(200, {"application": item})


def handle_update(event, app_id):
    """Handle PUT /applications/{id} - Update an application."""
    try:
        body = parse_body(event)
    except (json.JSONDecodeError, ValueError) as e:
        return build_response(400, {"error": f"Invalid JSON: {e}"})

    # Verify the application exists
    existing = table.get_item(Key={"application_id": app_id})
    if "Item" not in existing:
        return build_response(404, {"error": f"Application {app_id} not found"})

    allowed_fields = [
        "applicant_name", "applicant_email", "age", "annual_income",
        "employment_type", "credit_score", "existing_loans",
        "monthly_expenses", "years_of_employment", "has_collateral",
        "dependents", "loan_type", "loan_amount", "loan_term_months",
        "purpose", "status",
    ]
    financial_fields = [
        "annual_income", "credit_score", "existing_loans",
        "monthly_expenses", "years_of_employment", "has_collateral",
        "loan_amount", "loan_term_months", "loan_type", "employment_type",
    ]

    updates = {}
    financial_changed = False
    for field in allowed_fields:
        if field in body:
            updates[field] = body[field]
            if field in financial_fields:
                financial_changed = True

    if not updates:
        return build_response(400, {"error": "No valid fields to update"})

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    if financial_changed and updates.get("status") != "withdrawn":
        updates["status"] = "pending"
        updates["eligibility_result"] = None

    updates = to_decimal(updates)

    # Build update expression
    parts, expr_vals, expr_names = [], {}, {}
    for i, (k, v) in enumerate(updates.items()):
        parts.append(f"#a{i} = :v{i}")
        expr_names[f"#a{i}"] = k
        expr_vals[f":v{i}"] = v

    response = table.update_item(
        Key={"application_id": app_id},
        UpdateExpression="SET " + ", ".join(parts),
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_vals,
        ReturnValues="ALL_NEW",
    )
    updated = response.get("Attributes", {})

    # Re-evaluate eligibility if financial data changed
    if financial_changed and updates.get("status") != "withdrawn":
        try:
            result, new_status = evaluate_eligibility(updated)
            result = to_decimal(result)
            table.update_item(
                Key={"application_id": app_id},
                UpdateExpression="SET eligibility_result = :r, #s = :st, updated_at = :ts",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":r": result,
                    ":st": new_status,
                    ":ts": datetime.now(timezone.utc).isoformat(),
                },
            )
            updated["eligibility_result"] = result
            updated["status"] = new_status
        except Exception as eval_err:
            print(f"Re-evaluation error: {eval_err}")

    # Notify about status changes
    if "status" in body:
        send_notification(
            subject=f"Application Updated - {app_id[:8]}",
            message=f"Application {app_id} status: {updated.get('status')}",
        )

    return build_response(200, {
        "message": "Application updated successfully",
        "application": updated,
    })


def handle_delete(event, app_id):
    """Handle DELETE /applications/{id} - Delete an application."""
    existing = table.get_item(Key={"application_id": app_id})
    item = existing.get("Item")
    if not item:
        return build_response(404, {"error": f"Application {app_id} not found"})

    # Clean up S3 documents
    try:
        prefix = f"documents/{app_id}/"
        s3_resp = s3_client.list_objects_v2(Bucket=DOCUMENTS_BUCKET, Prefix=prefix)
        objects = s3_resp.get("Contents", [])
        if objects:
            s3_client.delete_objects(
                Bucket=DOCUMENTS_BUCKET,
                Delete={"Objects": [{"Key": o["Key"]} for o in objects]},
            )
    except Exception as e:
        print(f"S3 cleanup warning: {e}")

    table.delete_item(Key={"application_id": app_id})

    send_notification(
        subject=f"Application Deleted - {app_id[:8]}",
        message=f"Application {app_id} ({item.get('applicant_name')}) deleted.",
    )

    return build_response(200, {
        "message": f"Application {app_id} deleted successfully",
    })


# ------------------------------------------------------------------
# Main Router
# ------------------------------------------------------------------
def handler(event, context):
    """
    Main Lambda handler for Function URL requests.

    Routes requests based on HTTP method and path to the appropriate
    CRUD handler function.
    """
    # Handle Lambda Function URL event format
    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})
    method = http.get("method", event.get("httpMethod", "GET"))
    path = http.get("path", event.get("rawPath", "/"))

    print(f"Request: {method} {path}")

    # Handle CORS preflight
    if method == "OPTIONS":
        return build_response(200, {"message": "OK"})

    try:
        app_id = extract_path_id(path)

        if method == "POST" and not app_id:
            return handle_create(event)
        elif method == "GET" and not app_id:
            return handle_list(event)
        elif method == "GET" and app_id:
            return handle_get(event, app_id)
        elif method == "PUT" and app_id:
            return handle_update(event, app_id)
        elif method == "DELETE" and app_id:
            return handle_delete(event, app_id)
        else:
            return build_response(400, {"error": f"Unsupported: {method} {path}"})

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return build_response(500, {"error": "Internal server error"})
