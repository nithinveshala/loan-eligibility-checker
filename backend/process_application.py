"""
Lambda function for processing loan eligibility.

This function is triggered by SQS messages when a new application is
submitted or an existing application is updated. It uses the custom
loan-eligibility-engine library to evaluate the application and stores
the result back in DynamoDB.
"""

import json
import sys
import os
from decimal import Decimal

# Add the library to the path (packaged in the Lambda layer or deployment package)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from loan_eligibility_engine import (
    EligibilityCalculator,
    LoanApplication,
    Applicant,
)
from loan_eligibility_engine.models import LoanType, EmploymentType

from utils import (
    table,
    get_timestamp,
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


def map_employment_type(type_str: str) -> EmploymentType:
    """Map a string employment type to the EmploymentType enum."""
    mapping = {
        "salaried": EmploymentType.SALARIED,
        "self_employed": EmploymentType.SELF_EMPLOYED,
        "freelancer": EmploymentType.FREELANCER,
        "unemployed": EmploymentType.UNEMPLOYED,
        "retired": EmploymentType.RETIRED,
    }
    return mapping.get(type_str.lower(), EmploymentType.SALARIED)


def map_loan_type(type_str: str) -> LoanType:
    """Map a string loan type to the LoanType enum."""
    mapping = {
        "personal": LoanType.PERSONAL,
        "home": LoanType.HOME,
        "auto": LoanType.AUTO,
        "education": LoanType.EDUCATION,
    }
    return mapping.get(type_str.lower(), LoanType.PERSONAL)


def evaluate_application(application_id: str) -> None:
    """
    Fetch an application from DynamoDB, run eligibility evaluation
    using the loan-eligibility-engine library, and store the result.

    Args:
        application_id: The unique ID of the application to evaluate.
    """
    # Fetch the application from DynamoDB
    response = table.get_item(Key={"application_id": application_id})
    item = response.get("Item")

    if not item:
        print(f"Application {application_id} not found in DynamoDB")
        return

    # Build the Applicant object from DynamoDB data
    applicant = Applicant(
        name=item.get("applicant_name", ""),
        age=int(item.get("age", 30)),
        annual_income=float(item.get("annual_income", 0)),
        employment_type=map_employment_type(item.get("employment_type", "salaried")),
        credit_score=int(item.get("credit_score", 500)),
        existing_loans=int(item.get("existing_loans", 0)),
        monthly_expenses=float(item.get("monthly_expenses", 0)),
        years_of_employment=float(item.get("years_of_employment", 0)),
        has_collateral=bool(item.get("has_collateral", False)),
        dependents=int(item.get("dependents", 0)),
    )

    # Build the LoanApplication object
    loan_app = LoanApplication(
        applicant=applicant,
        loan_type=map_loan_type(item.get("loan_type", "personal")),
        loan_amount=float(item.get("loan_amount", 0)),
        loan_term_months=int(item.get("loan_term_months", 12)),
        purpose=item.get("purpose", ""),
        application_id=application_id,
    )

    # Run the eligibility evaluation using the custom library
    calculator = EligibilityCalculator()
    decision = calculator.evaluate(loan_app)

    # Convert the decision to a storable format
    result = decision.to_dict()
    result = convert_floats_to_decimal(result)

    # Determine the application status based on the decision
    status_mapping = {
        "approved": "approved",
        "conditional": "conditional",
        "denied": "denied",
        "pending_review": "under_review",
    }
    new_status = status_mapping.get(decision.status.value, "under_review")

    # Update the application in DynamoDB with the eligibility result
    table.update_item(
        Key={"application_id": application_id},
        UpdateExpression=(
            "SET eligibility_result = :result, #s = :status, updated_at = :ts"
        ),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":result": result,
            ":status": new_status,
            ":ts": get_timestamp(),
        },
    )

    print(
        f"Application {application_id} evaluated: "
        f"status={new_status}, score={decision.eligibility_score:.1f}"
    )

    # Send notification about the eligibility decision
    send_sns_notification(
        subject=f"Loan Application {new_status.upper()} - {application_id[:8]}",
        message=(
            f"Loan application for {item.get('applicant_name', 'N/A')} "
            f"has been evaluated.\n\n"
            f"Decision: {new_status.upper()}\n"
            f"Eligibility Score: {decision.eligibility_score:.1f}/100\n"
            f"Risk Level: {decision.risk_level.value}\n"
            f"Max Eligible Amount: {decision.max_eligible_amount:,.2f}\n"
            f"Recommended Rate: {decision.recommended_interest_rate:.2%}\n\n"
            f"Reasons:\n" + "\n".join(f"- {r}" for r in decision.reasons)
        ),
    )


def handler(event, context):
    """
    Lambda handler triggered by SQS messages.

    Processes each message in the batch, evaluating the loan application
    referenced by the application_id in the message body.

    Args:
        event: SQS event containing one or more messages.
        context: Lambda context object.
    """
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            application_id = body.get("application_id")
            action = body.get("action", "evaluate_eligibility")

            if not application_id:
                print("Missing application_id in SQS message")
                continue

            if action == "evaluate_eligibility":
                evaluate_application(application_id)
            else:
                print(f"Unknown action: {action}")

        except Exception as e:
            print(f"Error processing SQS message: {str(e)}")
            # Re-raise to allow SQS retry mechanism
            raise
