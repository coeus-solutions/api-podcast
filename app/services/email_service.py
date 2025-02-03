from mailjet_rest import Client
from app.config import settings

def send_reset_password_email(to_email: str, otp: str) -> bool:
    """
    Send password reset OTP email using Mailjet
    """
    try:
        mailjet = Client(
            auth=(settings.MAILJET_API_KEY, settings.MAILJET_SECRET_KEY),
            version='v3.1'
        )
        
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": settings.MAILJET_SENDER_EMAIL,
                        "Name": settings.MAILJET_SENDER_NAME
                    },
                    "To": [
                        {
                            "Email": to_email
                        }
                    ],
                    "Subject": "Password Reset OTP",
                    "TextPart": f"Your OTP for password reset is: {otp}. This OTP will expire in 10 minutes.",
                    "HTMLPart": f"""
                        <h3>Password Reset OTP</h3>
                        <p>Your OTP for password reset is: <strong>{otp}</strong></p>
                        <p>This OTP will expire in 10 minutes.</p>
                        <p>If you didn't request this password reset, please ignore this email.</p>
                    """
                }
            ]
        }
        
        result = mailjet.send.create(data=data)
        print(f"Mailjet response: {result.status_code}")
        return result.status_code == 200
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False 