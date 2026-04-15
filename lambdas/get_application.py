"""
Lambda function for retrieving a single loan application by ID.

Handles GET /applications/{id} requests. Fetches the application
from DynamoDB and returns its full details including eligibility results.
"""

from utils import build_response, get_path_param, table, s3_client, S3_BUCKET


def handler(event, context):
    """
    Lambda handler for retrieving a specific loan application.

    Path parameters:
    - id: The unique application ID to retrieve.
    """
    try:
        application_id = get_path_param(event, "id")
    except ValueError as e:
        return build_response(400, {"error": str(e)})

    try:
        # Fetch the application from DynamoDB
        response = table.get_item(Key={"application_id": application_id})
        item = response.get("Item")

        if not item:
            return build_response(404, {
                "error": f"Application {application_id} not found"
            })

        # Check for associated documents in S3
        try:
            doc_prefix = f"documents/{application_id}/"
            s3_response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET, Prefix=doc_prefix
            )
            documents = []
            for obj in s3_response.get("Contents", []):
                # Generate a presigned URL for each document (read access)
                url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": S3_BUCKET, "Key": obj["Key"]},
                    ExpiresIn=3600,
                )
                documents.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                    "url": url,
                })
            item["documents"] = documents
        except Exception as doc_error:
            # S3 document listing is non-critical; proceed without it
            print(f"Could not list documents: {str(doc_error)}")
            item["documents"] = []

        return build_response(200, {"application": item})

    except Exception as e:
        print(f"Error fetching application: {str(e)}")
        return build_response(500, {"error": "Failed to fetch application"})
