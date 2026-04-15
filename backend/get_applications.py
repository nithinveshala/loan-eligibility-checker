"""
Lambda function for listing all loan applications.

Handles GET /applications requests. Performs a DynamoDB scan to retrieve
all applications and returns them sorted by creation date in descending order.
"""

from utils import build_response, table


def handler(event, context):
    """
    Lambda handler for retrieving all loan applications.

    Supports optional query parameters:
    - status: Filter by application status (pending, approved, denied, etc.)
    - loan_type: Filter by loan type (personal, home, auto, education)
    """
    try:
        # Parse optional query parameters for filtering
        params = event.get("queryStringParameters") or {}
        status_filter = params.get("status")
        loan_type_filter = params.get("loan_type")

        # Build scan parameters with optional filters
        scan_kwargs = {}
        filter_expressions = []
        expression_values = {}
        expression_names = {}

        if status_filter:
            filter_expressions.append("#s = :status")
            expression_values[":status"] = status_filter
            expression_names["#s"] = "status"

        if loan_type_filter:
            filter_expressions.append("loan_type = :loan_type")
            expression_values[":loan_type"] = loan_type_filter

        if filter_expressions:
            scan_kwargs["FilterExpression"] = " AND ".join(filter_expressions)
            scan_kwargs["ExpressionAttributeValues"] = expression_values
            if expression_names:
                scan_kwargs["ExpressionAttributeNames"] = expression_names

        # Perform the scan
        response = table.scan(**scan_kwargs)
        applications = response.get("Items", [])

        # Handle pagination if there are more results
        while "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = table.scan(**scan_kwargs)
            applications.extend(response.get("Items", []))

        # Sort by creation date (newest first)
        applications.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return build_response(200, {
            "applications": applications,
            "count": len(applications),
        })

    except Exception as e:
        print(f"Error fetching applications: {str(e)}")
        return build_response(500, {"error": "Failed to fetch applications"})
