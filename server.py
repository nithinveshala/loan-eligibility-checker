"""
Flask server for the Loan Eligibility Checker application.

This server provides the REST API endpoints and serves the React
frontend as static files. It integrates with AWS services including
DynamoDB, S3, SNS, SSM Parameter Store, and CloudWatch.

AWS Services used:
1. DynamoDB - Application database
2. S3 - Document storage
3. SNS - Notifications
4. SSM Parameter Store - Configuration management
5. CloudWatch - Logging via CloudWatch agent
6. EC2 - Hosting this server
7. Lambda - Background eligibility processing
"""

import json
import os
import sys
import uuid
import traceback
import logging
from decimal import Decimal
from datetime import datetime, timezone

# Add the library to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "library"))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError

from loan_eligibility_engine import (
    EligibilityCalculator,
    LoanApplication,
    Applicant,
)
from loan_eligibility_engine.models import LoanType, EmploymentType

# ------------------------------------------------------------------
# Configuration - loaded from SSM Parameter Store
# ------------------------------------------------------------------
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

ssm_client = boto3.client("ssm", region_name=REGION)

def get_ssm_param(name, default=""):
    """Retrieve a configuration value from SSM Parameter Store."""
    try:
        resp = ssm_client.get_parameter(Name=name)
        return resp["Parameter"]["Value"]
    except Exception:
        return default

# Load config from SSM Parameter Store (AWS Service #5)
DYNAMODB_TABLE = get_ssm_param("lec-dynamodb-table", "lec-applications")
DOCUMENTS_BUCKET = get_ssm_param("lec-documents-bucket", "lec-documents-905418")
SNS_TOPIC_ARN = get_ssm_param("lec-sns-topic", "")

# AWS service clients
dynamodb = boto3.resource("dynamodb", region_name=REGION)
s3_client = boto3.client("s3", region_name=REGION)
sns_client = boto3.client("sns", region_name=REGION)
logs_client = boto3.client("logs", region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

# ------------------------------------------------------------------
# CloudWatch Logging Setup (AWS Service #7)
# ------------------------------------------------------------------
LOG_GROUP = "/lec/application-server"
LOG_STREAM = f"server-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

def setup_cloudwatch_logging():
    """Set up CloudWatch Logs log group and stream for application logging."""
    try:
        logs_client.create_log_group(logGroupName=LOG_GROUP)
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceAlreadyExistsException":
            print(f"Could not create log group: {e}")

    try:
        logs_client.create_log_stream(
            logGroupName=LOG_GROUP, logStreamName=LOG_STREAM
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceAlreadyExistsException":
            print(f"Could not create log stream: {e}")

def log_to_cloudwatch(message):
    """Send a log event to CloudWatch Logs."""
    try:
        logs_client.put_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            logEvents=[{
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                "message": message,
            }],
        )
    except Exception:
        pass  # Non-critical: don't fail if logging fails

# ------------------------------------------------------------------
# Flask Application Setup
# ------------------------------------------------------------------
app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "frontend", "build"),
    static_url_path="",
)
CORS(app)

# Configure Python logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Utility Helpers
# ------------------------------------------------------------------
class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that converts DynamoDB Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)

app.json_encoder = DecimalEncoder


def to_decimal(obj):
    """Recursively convert floats to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_decimal(i) for i in obj]
    return obj


def serialize(obj):
    """Serialize an object handling Decimal types."""
    return json.loads(json.dumps(obj, cls=DecimalEncoder))


def send_notification(subject, message):
    """Publish a notification to the SNS topic (AWS Service #3)."""
    if not SNS_TOPIC_ARN:
        return
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject[:100],
            Message=message,
        )
        logger.info(f"SNS notification sent: {subject}")
    except Exception as e:
        logger.warning(f"SNS notification failed: {e}")


def evaluate_eligibility(item):
    """
    Run the loan eligibility assessment using the custom library.

    This function demonstrates the integration of the custom
    loan-eligibility-engine library with the application.
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
# API Routes - CRUD Operations
# ------------------------------------------------------------------

@app.route("/api/applications", methods=["POST"])
def create_application():
    """Create a new loan application (CREATE operation)."""
    body = request.get_json()
    if not body:
        return jsonify({"error": "Request body is required"}), 400

    required = [
        "applicant_name", "age", "annual_income", "employment_type",
        "credit_score", "loan_type", "loan_amount", "loan_term_months",
    ]
    missing = [f for f in required if f not in body or body[f] is None]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

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

    # Store in DynamoDB (AWS Service #1)
    table.put_item(Item=item)

    # Evaluate eligibility using the custom library
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
    except Exception as e:
        logger.error(f"Eligibility evaluation error: {e}")

    # Generate presigned URL for document upload to S3 (AWS Service #2)
    upload_url = ""
    try:
        upload_url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": DOCUMENTS_BUCKET, "Key": f"documents/{app_id}/upload"},
            ExpiresIn=3600,
        )
    except Exception as e:
        logger.warning(f"Presigned URL error: {e}")

    # Send SNS notification (AWS Service #3)
    send_notification(
        subject=f"New Loan Application - {app_id[:8]}",
        message=(
            f"New loan application submitted.\n"
            f"ID: {app_id}\nApplicant: {body['applicant_name']}\n"
            f"Type: {body['loan_type']}\nAmount: {body['loan_amount']}\n"
            f"Status: {item.get('status', 'pending')}"
        ),
    )

    # Log to CloudWatch (AWS Service #7)
    log_to_cloudwatch(f"CREATE application {app_id} by {body['applicant_name']}")

    return jsonify(serialize({
        "message": "Application created successfully",
        "application_id": app_id,
        "upload_url": upload_url,
        "status": item.get("status", "pending"),
    })), 201


@app.route("/api/applications", methods=["GET"])
def list_applications():
    """List all loan applications (READ operation - list)."""
    status_filter = request.args.get("status")
    type_filter = request.args.get("loan_type")

    scan_kwargs = {}
    filters, expr_values, expr_names = [], {}, {}

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

    return jsonify(serialize({"applications": items, "count": len(items)}))


@app.route("/api/applications/<app_id>", methods=["GET"])
def get_application(app_id):
    """Get a single loan application by ID (READ operation - detail)."""
    response = table.get_item(Key={"application_id": app_id})
    item = response.get("Item")

    if not item:
        return jsonify({"error": f"Application {app_id} not found"}), 404

    # List S3 documents (AWS Service #2)
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
            docs.append({"key": obj["Key"], "size": obj["Size"], "url": url})
        item["documents"] = docs
    except Exception:
        item["documents"] = []

    return jsonify(serialize({"application": item}))


@app.route("/api/applications/<app_id>", methods=["PUT"])
def update_application(app_id):
    """Update an existing loan application (UPDATE operation)."""
    body = request.get_json()
    if not body:
        return jsonify({"error": "Request body is required"}), 400

    existing = table.get_item(Key={"application_id": app_id})
    if "Item" not in existing:
        return jsonify({"error": f"Application {app_id} not found"}), 404

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

    updates, financial_changed = {}, False
    for f in allowed_fields:
        if f in body:
            updates[f] = body[f]
            if f in financial_fields:
                financial_changed = True

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    if financial_changed and updates.get("status") != "withdrawn":
        updates["status"] = "pending"
        updates["eligibility_result"] = None

    updates = to_decimal(updates)

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

    if financial_changed and updates.get("status") != "withdrawn":
        try:
            result, new_status = evaluate_eligibility(updated)
            result = to_decimal(result)
            table.update_item(
                Key={"application_id": app_id},
                UpdateExpression="SET eligibility_result = :r, #s = :st, updated_at = :ts",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":r": result, ":st": new_status,
                    ":ts": datetime.now(timezone.utc).isoformat(),
                },
            )
            updated["eligibility_result"] = result
            updated["status"] = new_status
        except Exception as e:
            logger.error(f"Re-evaluation error: {e}")

    send_notification(
        subject=f"Application Updated - {app_id[:8]}",
        message=f"Application {app_id} updated. Status: {updated.get('status')}",
    )
    log_to_cloudwatch(f"UPDATE application {app_id}")

    return jsonify(serialize({"message": "Application updated", "application": updated}))


@app.route("/api/applications/<app_id>", methods=["DELETE"])
def delete_application(app_id):
    """Delete a loan application (DELETE operation)."""
    existing = table.get_item(Key={"application_id": app_id})
    item = existing.get("Item")
    if not item:
        return jsonify({"error": f"Application {app_id} not found"}), 404

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
        logger.warning(f"S3 cleanup: {e}")

    table.delete_item(Key={"application_id": app_id})

    send_notification(
        subject=f"Application Deleted - {app_id[:8]}",
        message=f"Application {app_id} ({item.get('applicant_name')}) deleted.",
    )
    log_to_cloudwatch(f"DELETE application {app_id}")

    return jsonify({"message": f"Application {app_id} deleted successfully"})


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "Loan Eligibility Checker"})


# ------------------------------------------------------------------
# Serve React Frontend
# ------------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serve the React frontend static files."""
    static_folder = app.static_folder
    if path and os.path.exists(os.path.join(static_folder, path)):
        return send_from_directory(static_folder, path)
    return send_from_directory(static_folder, "index.html")


# ------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------
if __name__ == "__main__":
    setup_cloudwatch_logging()
    log_to_cloudwatch("Server starting")
    logger.info(f"DynamoDB Table: {DYNAMODB_TABLE}")
    logger.info(f"S3 Bucket: {DOCUMENTS_BUCKET}")
    logger.info(f"SNS Topic: {SNS_TOPIC_ARN}")
    app.run(host="0.0.0.0", port=8080, debug=False)
