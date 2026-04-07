import asyncio
from typing import List, Dict
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from firebase_admin import messaging
from datetime import datetime

load_dotenv()

class NotificationService:
    def __init__(self):
        # Twilio for SMS
        self.twilio_client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        self.twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')
        
        # Email settings
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
    
    async def send_alerts(self, detection: Dict, nearby_stations: List[Dict]):
        """Send alerts through multiple channels"""
        tasks = []
        
        # Send SMS to top 3 nearest stations
        for station in nearby_stations[:3]:
            if station.get('phone'):
                tasks.append(self.send_sms(station['phone'], detection))
        
        # Send emails to all stations with email
        for station in nearby_stations:
            if station.get('email'):
                tasks.append(self.send_email(station['email'], detection))
        
        # Send push notifications
        tasks.append(self.send_push_notification(detection))
        
        # Execute all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Notification {i} failed: {result}")
    
    async def send_sms(self, to: str, detection: Dict):
        """Send SMS alert using Twilio"""
        try:
            message = self._format_sms_message(detection)
            
            # Truncate if too long (Twilio limit is 1600 chars)
            if len(message) > 1600:
                message = message[:1597] + "..."
            
            self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_phone,
                to=to
            )
            print(f"✅ SMS sent to {to}")
            return True
            
        except Exception as e:
            print(f"❌ SMS failed to {to}: {e}")
            return False
    
    async def send_email(self, to: str, detection: Dict):
        """Send email alert with HTML formatting"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_user
            msg['To'] = to
            msg['Subject'] = f"🚨 WILDFIRE ALERT - {detection['severity'].upper()}"
            
            # Create both plain text and HTML versions
            text_body = self._format_text_email(detection)
            html_body = self._format_html_email(detection)
            
            # Attach parts
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email sent to {to}")
            return True
            
        except Exception as e:
            print(f"❌ Email failed to {to}: {e}")
            return False
    
    async def send_push_notification(self, detection: Dict):
        """Send push notification via FCM HTTP v1 using Firebase Admin SDK"""
        try:
            # Determine notification priority based on severity
            priority = 'high' if detection['severity'] in ['critical', 'high'] else 'normal'
            
            # Create message for the topic
            message = messaging.Message(
                topic='wildfire_alerts',
                notification=messaging.Notification(
                    title='🔥 Wildfire Detected',
                    body=f"{detection['severity'].upper()} severity at {detection.get('address', 'unknown location')}",
                ),
                data={
                    'detection_id': detection['id'],
                    'latitude': str(detection['latitude']),
                    'longitude': str(detection['longitude']),
                    'severity': detection['severity'],
                    'confidence': str(detection['confidence']),
                    'image_url': str(detection.get('image_url') or ''),
                    'timestamp': detection['timestamp'].isoformat() if isinstance(detection['timestamp'], datetime) else str(detection['timestamp']),
                    'click_action': 'OPEN_DETECTION'
                },
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        channel_id='wildfire_alerts',
                        sound='default',
                        icon='ic_notification',
                        color=self._get_severity_color(detection['severity'])
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1,
                        ),
                    ),
                ),
            )

            # Send the message
            response = messaging.send(message)
            print(f"✅ Push notification sent successfully: {response}")
            return True
            
        except Exception as e:
            print(f"❌ Push notification error: {e}")
            return False
            
    async def send_verified_alert(self, detection: Dict):
        """Send additional alerts when fire is verified"""
        try:
            # Send to emergency services
            emergency_numbers = os.getenv('EMERGENCY_PHONE_NUMBERS', '').split(',')
            for number in emergency_numbers:
                if number.strip():
                    await self.send_sms(number.strip(), {**detection, '_verified': True})
            
            # Broadcast to all users
            await self.send_push_notification({
                **detection,
                'title': '🚨 VERIFIED WILDFIRE ALERT'
            })
            
        except Exception as e:
            print(f"Error sending verified alert: {e}")
    
    def _format_sms_message(self, detection: Dict, verified: bool = False) -> str:
        """Format SMS alert message"""
        prefix = "🚨 VERIFIED " if verified else "🔥 "
        image_str = f"🖼️ Image: {detection['image_url']}" if detection.get('image_url') else "🖼️ Image: No image available"
        
        lines = [
            f"{prefix}WILDFIRE DETECTED!",
            f"Severity: {detection['severity'].upper()}",
            f"Location: {detection.get('address', 'Unknown')}",
            f"Confidence: {detection['confidence']*100:.0f}%",
            f"Time: {detection['timestamp'].strftime('%H:%M %d/%m/%Y') if isinstance(detection['timestamp'], datetime) else str(detection['timestamp'])}",
            "",
            f"📍 Map: https://maps.google.com/?q={detection['latitude']},{detection['longitude']}",
            image_str,
            "",
            "🚒 Fire department has been notified."
        ]
        
        return "\n".join(lines)
    
    def _format_text_email(self, detection: Dict) -> str:
        """Format plain text email"""
        image_str = f"Detection Image: {detection['image_url']}" if detection.get('image_url') else "Detection Image: Not available"
        lines = [
            "WILDFIRE DETECTION ALERT",
            "=" * 40,
            "",
            f"Severity: {detection['severity'].upper()}",
            f"Confidence: {detection['confidence']*100:.0f}%",
            f"Time: {detection['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(detection['timestamp'], datetime) else str(detection['timestamp'])}",
            "",
            "LOCATION DETAILS:",
            f"Address: {detection.get('address', 'Unknown')}",
            f"City: {detection.get('city', 'Unknown')}",
            f"State: {detection.get('state', 'Unknown')}",
            f"Country: {detection.get('country', 'Unknown')}",
            f"Coordinates: {detection['latitude']}, {detection['longitude']}",
            "",
            "LINKS:",
            f"Google Maps: https://maps.google.com/?q={detection['latitude']},{detection['longitude']}",
            image_str,
            "",
            "=" * 40,
            "This is an automated alert from the Wildfire Detection System"
        ]
        
        return "\n".join(lines)
    
    def _format_html_email(self, detection: Dict) -> str:
        """Format HTML email"""
        severity_colors = {
            'critical': '#8b0000',
            'high': '#dc3545',
            'medium': '#ffc107',
            'low': '#28a745'
        }
        
        severity_color = severity_colors.get(detection['severity'], '#000000')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {severity_color}; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; }}
                .severity-badge {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; text-transform: uppercase; }}
                .detail-row {{ margin: 10px 0; padding: 10px; background-color: white; border-radius: 3px; }}
                .label {{ font-weight: bold; color: #666; }}
                .value {{ color: #333; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: {severity_color}; color: white; text-decoration: none; border-radius: 3px; margin: 5px; }}
                .footer {{ margin-top: 20px; text-align: center; color: #999; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 WILDFIRE ALERT</h1>
                    <div class="severity-badge">Severity: {detection['severity'].upper()}</div>
                </div>
                
                <div class="content">
                    <div class="detail-row">
                        <div class="label">📍 Location</div>
                        <div class="value">{detection.get('address', 'Unknown')}</div>
                        <div class="value">{detection.get('city', '')}, {detection.get('state', '')}</div>
                        <div class="value">{detection.get('country', '')}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">📊 Detection Details</div>
                        <div class="value">Confidence: {detection['confidence']*100:.1f}%</div>
                        <div class="value">Time: {detection['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(detection['timestamp'], datetime) else str(detection['timestamp'])}</div>
                        <div class="value">Status: {detection.get('status', 'pending').upper()}</div>
                    </div>
                    
                    <div class="detail-row">
                        <div class="label">🌍 Coordinates</div>
                        <div class="value">Latitude: {detection['latitude']}</div>
                        <div class="value">Longitude: {detection['longitude']}</div>
                    </div>
                    
                    <div style="text-align: center; margin: 20px 0;">
                        <a href="https://maps.google.com/?q={detection['latitude']},{detection['longitude']}" class="button">📍 View on Map</a>
                        {f'<a href="{detection["image_url"]}" class="button">🖼️ View Image</a>' if detection.get("image_url") else ""}
                    </div>
                    
                    {f'<div style="text-align: center;"><img src="{detection["image_url"]}" alt="Fire detection" style="max-width: 100%; border-radius: 5px;"></div>' if detection.get("image_url") else '<div style="text-align: center; color: #666; font-style: italic;">No image available for this report</div>'}
                </div>
                
                <div class="footer">
                    <p>This is an automated alert from the Wildfire Detection System</p>
                    <p>© 2024 Wildfire Detection System. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_severity_color(self, severity: str) -> str:
        colors = {
            'critical': '#FF0000',
            'high': '#FF4444',
            'medium': '#FFAA00',
            'low': '#00FF00'
        }
        return colors.get(severity, '#000000')