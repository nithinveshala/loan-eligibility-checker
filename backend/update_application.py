"""
Lambda function for updating an existing loan application.

Handles PUT /applications/{id} requests. Allows updating application
fields and triggers re-evaluation of eligibility when financial data changes.
"""

import json
from decimal import Decimal

from utils import (
    build_response,
    parse_body,
    get_path_param,
    get_timestamp,
    table,
    send_to_sqs,
    send_sns_notification,
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


# Fields that are allowed to be updated by the client
UPDATABLE_FIELDS = [
    "applicant_name", "applicant_email", "age", "annual_income",
    "employment_type", "credit_score", "existing_loans", "monthly_expenses",
    "years_of_employment", "has_collateral", "dependents", "loan_type",
    "loan_amount", "loan_term_months", "purpose", "status",
]

# Fields that trigger a re-evaluation of eligibility when changed
FINANCIAL_FIELDS = [
    "annual_income", "credit_score", "existing_loans", "monthly_expenses",
    "years_of_employment", "has_collateral", "loan_amount", "loan_term_months",
    "loan_type", "employment_type",
]


def handler(event, context):
    """
    Lambda handler for updating a loan application.

    Path parameters:
    - id: The application ID to update.

    Request body: A JSON object with fields to update.
    """
    try:
        application_id = get_path_param(event, "id")
    except ValueError as e:
        return build_response(400, {"error": str(e)})

    try:
        body = parse_body(event)
    except (ValueError, json.JSONDecodeError) as e:
        return build_response(400, {"error": f"Invalid request body: {str(e)}"})

    # Verify the application exists
    try:
        existing = table.get_item(Key={"application_id": application_id})
        if "Item" not in existing:
            return build_response(404, {
                "error": f"Application {application_id} not found"
            })
    except Exception as e:
        return build_response(500, {"error": "Failed to verify application"})

    # Filter to only updatable fields and track financial changes
    updates = {}
    financial_changed = False
    for field in UPDATABLE_FIELDS:
        if field in body:
            updates[field] = body[field]
            if field in FINANCIAL_FIELDS:
                financial_changed = True

    if not updates:
        return build_response(400, {"error": "No valid fields to update"})

    # Add the updated timestamp
    updates["updated_at"] = get_timestamp()

    # If financial data changed, reset status to pending for re-evaluation
    if financial_changed and updates.get("status") != "withdrawn":
        updates["status"] = "pending"
        updates["eligibility_result"] = None

    # Convert floats to Decimal
    updates = convert_floats_to_decimal(updates)

    # Build the DynamoDB update expression
    update_parts = []
    expression_values = {}
    expression_names = {}

    for i, (key, value) in enumerate(updates.items()):
        attr_name = f"#attr{i}"
        attr_value = f":val{i}"
        update_parts.append(f"{attr_name} = {attr_value}")
        expression_names[attr_name] = key
        expression_values[attr_value] = value

    update_expression = "SET " + ", ".join(update_parts)

    try:
        response = table.update_item(
            Key={"application_id": application_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW",
        )

        updated_item = response.get("Attributes", {})

        # If financial data changed, queue for re-evaluation
        if financial_changed and updates.get("status") != "withdrawn":
            send_to_sqs({
                "application_id": application_id,
                "action": "evaluate_eligibility",
            })

        # Notify about status changes
        if "status" in body:
            send_sns_notification(
                subject=f"Loan Application Status Updated",
                message=(
                    f"Loan application {application_id} status has been "
                    f"updated to: {body['status']}.\n"
                    f"Applicant: {updated_item.get('applicant_name', 'N/A')}"
                ),
            )

        return build_response(200, {
            "message": "Application updated successfully",
            "application": updated_item,
        })

    except Exception as e:
        print(f"Error updating application: {str(e)}")
        return build_response(500, {"error": "Failed to update application"})
