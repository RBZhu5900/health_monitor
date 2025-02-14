import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from pathlib import Path
import json
from datetime import datetime

class EmailService:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_path = Path(__file__).parent.parent.parent / "data" / "config.json"
        self._load_config()
        
    def _load_config(self):
        """Load email configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                smtp_config = config.get("smtp", {})
                self.smtp_server = smtp_config.get("server")
                self.smtp_port = smtp_config.get("port", 587)
                self.sender_email = smtp_config.get("sender_email")
                self.sender_password = smtp_config.get("sender_password")
                self.receiver_email = config.get("receiver_email")
                
                if not all([self.smtp_server, self.sender_email, 
                           self.sender_password, self.receiver_email]):
                    raise ValueError("Missing required email configuration")
                    
        except Exception as e:
            self.logger.error(f"Failed to load email configuration: {str(e)}")
            raise
            
    def send_notification(self, time, message):
        """Send notification email"""
        subject = f"Health Reminder: {time} Health Advice"
        self._send_email(subject, message)
        
    def send_daily_summary(self, advice_data):
        """Send daily summary"""
        try:
            subject = f"Health Report: {datetime.now().strftime('%Y-%m-%d')} Health Data Summary"
            
            # Build email content
            content = "Daily Health Report\n"
            content += "==================\n\n"
            
            content += "Daily Summary\n"
            content += "------------\n"
            content += advice_data["daily_summary"]
            content += "\n\n"
            
            content += "Improvement Suggestions\n"
            content += "----------------------\n"
            for suggestion in advice_data["improvement_suggestions"]:
                content += f"- {suggestion}\n"
            content += "\n"
            
            content += "Today's Achievements\n"
            content += "-------------------\n"
            for achievement in advice_data["achievements"]:
                content += f"- {achievement}\n"
                
            self._send_email(subject, content)
            
        except Exception as e:
            self.logger.error(f"Failed to send daily summary: {str(e)}")
            raise
            
    def _send_email(self, subject, content):
        """Send email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                
            self.logger.info(f"Email sent successfully: {subject}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            raise 