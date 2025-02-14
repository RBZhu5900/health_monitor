from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
from pathlib import Path
from .email_service import EmailService
import json

class SchedulerService:
    def __init__(self, task_function):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.scheduler = BackgroundScheduler()
        self.task_function = task_function
        self.email_service = EmailService()
        
    def start(self):
        """启动调度器"""
        try:
            # 添加健康监控任务，每天凌晨3点执行
            self.scheduler.add_job(
                self.task_function,
                trigger=CronTrigger(hour=3, minute=0),
                id='health_monitor_task',
                name='健康监控任务',
                replace_existing=True
            )
            
            # 添加每日总结邮件任务，每天早上8点执行
            self.scheduler.add_job(
                self._send_daily_summary,
                trigger=CronTrigger(hour=8, minute=0),
                id='daily_summary_task',
                name='每日总结任务',
                replace_existing=True
            )
            
            # 启动调度器
            self.scheduler.start()
            self.logger.info("调度器已启动")
            
        except Exception as e:
            self.logger.error(f"启动调度器失败: {str(e)}")
            raise
            
    def add_notification_jobs(self, notifications):
        """添加提醒邮件任务"""
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
                    name=f'提醒任务 {time}',
                    replace_existing=True
                )
                
            self.logger.info(f"已添加 {len(notifications)} 个提醒任务")
            
        except Exception as e:
            self.logger.error(f"添加提醒任务失败: {str(e)}")
            raise
            
    def _send_daily_summary(self):
        """发送每日总结"""
        try:
            # 读取最新的建议数据
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
            self.logger.error(f"发送每日总结失败: {str(e)}")
            
    def stop(self):
        """停止调度器"""
        try:
            self.scheduler.shutdown()
            self.logger.info("调度器已停止")
        except Exception as e:
            self.logger.error(f"停止调度器失败: {str(e)}")
            raise 