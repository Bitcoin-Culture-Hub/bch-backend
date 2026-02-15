import boto3
from botocore.exceptions import ClientError

def create_email_template():
    # Create SES client
    client = boto3.client(
        "ses",
        region_name="us-east-1"  # change if needed
    )

    try:
        response = client.create_template(
            Template={
                "TemplateName": "welcome_email",
                "SubjectPart": "Welcome to Our Platform!",
                "TextPart": "Hello {{name}},\n\nWelcome to our platform!",
                "HtmlPart": """
                <html>
                  <body>
                    <h1>Hello {{name}},</h1>
                    <p>Welcome to our platform!</p>
                  </body>
                </html>
                """
            }
        )

        print("Template created successfully!")
        print(response)

    except ClientError as e:
        print("Error creating template:", e.response["Error"]["Message"])


if __name__ == "__main__":
    create_email_template()
