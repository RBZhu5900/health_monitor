from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
from pathlib import Path
from .email_service import EmailService
import json

class SchedulerService:
    def __init__(self, task_function):
        """Initialize scheduler"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.scheduler = BackgroundScheduler()
        self.task_function = task_function
        self.email_service = EmailService()
        
    def start(self):
        """Start scheduler"""
        try:
            # Add health monitoring task, execute at 3 AM daily
            self.scheduler.add_job(
                self.task_function,
                trigger=CronTrigger(hour=3, minute=0),
                id='health_monitor_task',
                name='Health Monitoring Task',
                replace_existing=True
            )
            
            # Add daily summary email task, execute at 8 AM daily
            self.scheduler.add_job(
                self._send_daily_summary,
                trigger=CronTrigger(hour=8, minute=0),
                id='daily_summary_task',
                name='Daily Summary Task',
                replace_existing=True
            )
            
            # Start scheduler
            self.scheduler.start()
            self.logger.info("Scheduler started")
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {str(e)}")
            raise
            
    def add_notification_jobs(self, notifications):
        """Add notification email tasks"""
        try:
            for notification in notifications:
                time = notification["time"]
                message = notification["message"]
                hour, minute = map(int, time.split(":"))
                
                self.scheduler.add_job(
                    self.email_service.send_notification,
                    trigger=CronTrigger(hour=hour, minute=minute),
                    args=[time, message],
                    id=f'notification_{time.replace(":", "_")}',
                    name=f'Notification Task {time}',
                    replace_existing=True
                )
                
            self.logger.info(f"Added {len(notifications)} notification tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to add notification tasks: {str(e)}")
            raise
            
    def _send_daily_summary(self):
        """Send daily summary"""
        try:
            # Read the latest advice data
            data_dir = Path("data_export/advice")
            if not data_dir.exists():
                return
                
            files = list(data_dir.glob("health_advice_*.json"))
            if not files:
                return
                
            latest_file = max(files, key=lambda x: x.stat().st_mtime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                advice_data = json.load(f)
                
            self.email_service.send_daily_summary(advice_data)
            
        except Exception as e:
            self.logger.error(f"Failed to send daily summary: {str(e)}")
            
    def stop(self):
        """Stop scheduler"""
        try:
            self.scheduler.shutdown()
            self.logger.info("Scheduler stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop scheduler: {str(e)}")
            raise 