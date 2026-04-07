import os
import asyncio
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client

load_dotenv()

def test_email():
    print("Testing Email...")
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    email_user = os.getenv('EMAIL_USER')
    email_password = os.getenv('EMAIL_PASSWORD')
    
    msg = MIMEText('Test email from Agniveer')
    msg['Subject'] = 'Test Alert'
    msg['From'] = email_user
    msg['To'] = email_user  # send to self
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(1)
        server.starttls()
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Email failed: {e}")

def test_sms():
    print("Testing SMS...")
    sid = os.getenv('TWILIO_ACCOUNT_SID')
    token = os.getenv('TWILIO_AUTH_TOKEN')
    phone_from = os.getenv('TWILIO_PHONE_NUMBER')
    
    # Try sending to the first emergency number
    emergency_numbers = os.getenv('EMERGENCY_PHONE_NUMBERS', '').split(',')
    if not emergency_numbers or not emergency_numbers[0]:
        print("No emergency number configured.")
        return
    phone_to = emergency_numbers[0].strip()
    
    try:
        client = Client(sid, token)
        msg = client.messages.create(
            body="Test SMS from Agniveer",
            from_=phone_from,
            to=phone_to
        )
        print(f"✅ SMS sent successfully. SID: {msg.sid}, Status: {msg.status}")
        if msg.error_message:
            print(f"Error: {msg.error_message}")
    except Exception as e:
        print(f"❌ SMS failed: {e}")

if __name__ == "__main__":
    test_email()
    print("-" * 40)
    test_sms()
