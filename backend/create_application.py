"""
Lambda function for creating a new loan application.

Handles POST /applications requests. Validates input data, stores the
application in DynamoDB, generates a presigned URL for document uploads,
and queues the application for eligibility processing via SQS.
"""

import json
from decimal import Decimal

from utils import (
    build_response,
    parse_body,
    generate_id,
    get_timestamp,
    table,
    send_to_sqs,
    send_sns_notification,
    generate_presigned_url,
    S3_BUCKET,
)


def convert_floats_to_decimal(obj):
    """Recursively convert float values to Decimal for DynamoDB storage."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(i) for i in obj]
    return obj


def handler(event, context):
    """
    Lambda handler for creating a new loan application.

    Expected request body:
    {
        "applicant_name": "John Doe",
        "applicant_email": "john@example.com",
        "age": 35,
        "annual_income": 75000,
        "employment_type": "salaried",
        "credit_score": 720,
        "existing_loans": 1,
        "monthly_expenses": 2000,
        "years_of_employment": 8,
        "has_collateral": true,
        "dependents": 2,
        "loan_type": "home",
        "loan_amount": 250000,
        "loan_term_months": 240,
        "purpose": "Purchase primary residence"
    }
    """
    try:
        body = parse_body(event)
    except (ValueError, json.JSONDecodeError) as e:
        return build_response(400, {"error": f"Invalid request body: {str(e)}"})

    # Validate required fields
    required_fields = [
        "applicant_name", "age", "annual_income", "employment_type",
        "credit_score", "loan_type", "loan_amount", "loan_term_months",
    ]
    missing = [f for f in required_fields if f not in body or body[f] is None]
    if missing:
        return build_response(400, {
            "error": f"Missing required fields: {', '.join(missing)}"
        })

    # Generate application ID and timestamp
    application_id = generate_id()
    timestamp = get_timestamp()

    # Build the application item for DynamoDB
    item = {
        "application_id": application_id,
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
        "created_at": timestamp,
        "updated_at": timestamp,
        "documents": [],
    }

    # Convert floats to Decimal for DynamoDB compatibility
    item = convert_floats_to_decimal(item)

    try:
        # Store in DynamoDB
        table.put_item(Item=item)

        # Generate presigned URL for document upload
        doc_key = f"documents/{application_id}/upload"
        upload_url = generate_presigned_url(doc_key)

        # Queue the application for eligibility processing
        send_to_sqs({
            "application_id": application_id,
            "action": "evaluate_eligibility",
        })

        # Send notification about new application
        send_sns_notification(
            subject="New Loan Application Submitted",
            message=(
                f"A new loan application has been submitted.\n"
                f"Application ID: {application_id}\n"
                f"Applicant: {body['applicant_name']}\n"
                f"Loan Type: {body['loan_type']}\n"
                f"Amount: {body['loan_amount']}\n"
                f"The application is being processed for eligibility."
            ),
        )

        return build_response(201, {
            "message": "Application created successfully",
            "application_id": application_id,
            "upload_url": upload_url,
            "status": "pending",
        })

    except Exception as e:
        print(f"Error creating application: {str(e)}")
        return build_response(500, {"error": "Failed to create application"})
