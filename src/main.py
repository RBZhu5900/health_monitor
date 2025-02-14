import logging
from services.mi_sport_service import MiSportService
from services.health_advisor_service import HealthAdvisorService
from services.scheduler_service import SchedulerService
from pathlib import Path
import json
from datetime import datetime
import signal
import sys

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

def health_monitor_task():
    """Health monitoring task"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting health monitoring process")
        
        # 1. Get health data
        service = MiSportService()
        health_data = service.get_health_data()
        logger.info("Successfully retrieved health data")
        
        # 2. Get health advice
        advisor = HealthAdvisorService()
        
        # Read detailed health data from file
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
        
        # Add notification email tasks
        scheduler.add_notification_jobs(advice["notifications"])
        
        # 3. Save advice to text file
        data_dir = Path("data_export")
        advice_file = data_dir / f"health_advice_{datetime.now().strftime('%Y%m%d')}.txt"
        
        with open(advice_file, 'w', encoding='utf-8') as f:
            f.write("=== Health Advice ===\n\n")
            f.write("Daily Reminders:\n")
            for notification in advice["notifications"]:
                f.write(f"[{notification['time']}] {notification['message']}\n")
            
            f.write("\nDaily Summary:\n")
            f.write(advice["daily_summary"])
            
            f.write("\n\nImprovement Suggestions:\n")
            for suggestion in advice["improvement_suggestions"]:
                f.write(f"- {suggestion}\n")
            
            f.write("\nAchievements:\n")
            for achievement in advice["achievements"]:
                f.write(f"- {achievement}\n")
            
            f.write("\n\n=== Raw Data ===\n")
            f.write(json.dumps(advice, ensure_ascii=False, indent=2))
            
        logger.info(f"Health advice saved to: {advice_file}")
        
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
        scheduler = SchedulerService(health_monitor_task)
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