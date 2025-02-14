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
        """加载邮件配置"""
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
                    raise ValueError("邮箱配置不完整")
                    
        except Exception as e:
            self.logger.error(f"加载邮件配置失败: {str(e)}")
            raise
            
    def send_notification(self, time, message):
        """发送提醒邮件"""
        subject = f"[健康提醒] {time} 的健康建议"
        self._send_email(subject, message)
        
    def send_daily_summary(self, advice_data):
        """发送每日总结"""
        try:
            subject = f"[健康报告] {datetime.now().strftime('%Y-%m-%d')} 健康数据总结"
            
            # 构建邮件内容
            content = "=== 每日健康报告 ===\n\n"
            
            content += "【每日总结】\n"
            content += advice_data["daily_summary"]
            content += "\n\n"
            
            content += "【改进建议】\n"
            for suggestion in advice_data["improvement_suggestions"]:
                content += f"- {suggestion}\n"
            content += "\n"
            
            content += "【今日成就】\n"
            for achievement in advice_data["achievements"]:
                content += f"- {achievement}\n"
                
            self._send_email(subject, content)
            
        except Exception as e:
            self.logger.error(f"发送每日总结失败: {str(e)}")
            raise
            
    def _send_email(self, subject, content):
        """发送邮件"""
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
                
            self.logger.info(f"邮件发送成功: {subject}")
            
        except Exception as e:
            self.logger.error(f"发送邮件失败: {str(e)}")
            raise 