import boto3
from botocore.exceptions import ClientError
from app.config import settings


def send_email_ses(to_email: str, subject: str, html_body: str):
    ses_client = boto3.client(
        "ses",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    try:
        response = ses_client.send_email(
            Source=settings.SES_SENDER_EMAIL,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        print("SES Email sent:", response)
        return True
    except ClientError as e:
        print("❌ SES ERROR:", e.response["Error"]["Message"])
        return False
