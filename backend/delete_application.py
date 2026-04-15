"""
Lambda function for deleting a loan application.

Handles DELETE /applications/{id} requests. Removes the application
from DynamoDB and cleans up associated documents from S3.
"""

from utils import (
    build_response,
    get_path_param,
    table,
    s3_client,
    S3_BUCKET,
    send_sns_notification,
)


def handler(event, context):
    """
    Lambda handler for deleting a loan application.

    Path parameters:
    - id: The application ID to delete.
    """
    try:
        application_id = get_path_param(event, "id")
    except ValueError as e:
        return build_response(400, {"error": str(e)})

    try:
        # Verify the application exists and get its details
        existing = table.get_item(Key={"application_id": application_id})
        item = existing.get("Item")

        if not item:
            return build_response(404, {
                "error": f"Application {application_id} not found"
            })

        applicant_name = item.get("applicant_name", "Unknown")

        # Delete associated documents from S3
        try:
            doc_prefix = f"documents/{application_id}/"
            s3_response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET, Prefix=doc_prefix
            )
            objects = s3_response.get("Contents", [])
            if objects:
                delete_keys = [{"Key": obj["Key"]} for obj in objects]
                s3_client.delete_objects(
                    Bucket=S3_BUCKET,
                    Delete={"Objects": delete_keys},
                )
                print(f"Deleted {len(delete_keys)} documents from S3")
        except Exception as s3_error:
            # S3 cleanup is non-critical; log and continue
            print(f"Warning: Could not clean up S3 documents: {str(s3_error)}")

        # Delete the application from DynamoDB
        table.delete_item(Key={"application_id": application_id})

        # Send notification about deletion
        send_sns_notification(
            subject="Loan Application Withdrawn",
            message=(
                f"Loan application {application_id} has been withdrawn "
                f"and deleted.\nApplicant: {applicant_name}"
            ),
        )

        return build_response(200, {
            "message": f"Application {application_id} deleted successfully",
        })

    except Exception as e:
        print(f"Error deleting application: {str(e)}")
        return build_response(500, {"error": "Failed to delete application"})
