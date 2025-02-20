import logging
from services.mi_fit_service import MiFitService
from services.health_advisor_service import HealthAdvisorService
from services.scheduler_service import SchedulerService
from pathlib import Path
import json
from datetime import datetime
import signal
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from services.email_service import EmailService

logger = logging.getLogger(__name__)

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('health_monitor.log'),
            logging.StreamHandler()
        ]
    )

def get_latest_health_data():
    """Get the latest health data file content"""
    try:
        data_dir = Path("data_export")
        if not data_dir.exists():
            return None
            
        files = list(data_dir.glob("api_response_*.txt"))
        if not files:
            return None
            
        latest_file = max(files, key=lambda x: x.stat().st_mtime)
        with open(latest_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to read health data: {str(e)}")
        return None

def send_notification(time, message):
    """Send notification email"""
    try:
        email_service = EmailService()
        email_service.send_notification(time, message)
        logger.info(f"Sent notification for {time}: {message}")
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")

def health_monitor_task():
    """Health monitoring task"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting health monitoring process")
        
        # 1. Get health data
        service = MiFitService()
        health_data = service.get_health_data()
        logger.info("Successfully retrieved health data")
        
        # 2. Get health advice
        advisor = HealthAdvisorService()
        detailed_data = get_latest_health_data()
        if detailed_data:
            combined_data = {
                "summary": health_data,
                "details": detailed_data
            }
        else:
            combined_data = health_data
            
        advice = advisor.get_health_advice(combined_data)
        logger.info("Successfully generated health advice")
        
        # Schedule notification emails
        for notification in advice.get("notifications", []):
            scheduler.add_job(
                send_notification,
                'cron',
                hour=notification['time'].split(':')[0],
                minute=notification['time'].split(':')[1],
                args=[notification['time'], notification['message']],
                id=f'notification_{notification["time"].replace(":", "_")}',
                replace_existing=True
            )
        
        # 3. Save advice using advisor service
        advisor._save_advice(json.dumps(advice, ensure_ascii=False, indent=2))
        logger.info("Health advice saved")
        
    except Exception as e:
        logger.error(f"Task execution failed: {str(e)}")

def signal_handler(signum, frame):
    """Handle exit signals"""
    logger = logging.getLogger(__name__)
    logger.info("Received exit signal, stopping services...")
    scheduler.stop()
    sys.exit(0)

def run_monitor(daemon=False):
    """Run monitoring service"""
    logger = logging.getLogger(__name__)
    
    try:
        # Only register signals if not running as daemon
        if not daemon:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        
        # Create and start scheduler
        global scheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            health_monitor_task,
            'cron',
            hour=3,
            kwargs={}  # 明确指定不传入额外参数
        )
        scheduler.start()
        
        # Execute task immediately
        health_monitor_task()
        
        # Keep program running if not daemon
        if not daemon:
            while True:
                signal.pause()
            
    except Exception as e:
        logger.error(f"Monitor service failed: {str(e)}")
        raise

if __name__ == "__main__":
    run_monitor() 