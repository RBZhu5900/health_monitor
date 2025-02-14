import logging
from services.email_service import EmailService
from pathlib import Path
import json
from datetime import datetime

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('email_test.log'),
            logging.StreamHandler()
        ]
    )

def get_latest_advice():
    """Get the latest health advice"""
    try:
        data_dir = Path("data_export/advice")
        if not data_dir.exists():
            return None
            
        files = list(data_dir.glob("health_advice_*.json"))
        if not files:
            return None
            
        latest_file = max(files, key=lambda x: x.stat().st_mtime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read health advice: {str(e)}")
        return None

def test_email_service():
    """Test email service"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting email service test")
        
        # Create email service instance
        email_service = EmailService()
        
        # Test sending simple notification
        logger.info("Testing notification email...")
        email_service.send_notification(
            "Test Time",
            "This is a test notification to verify email service functionality."
        )
        
        # Get latest health advice
        advice = get_latest_advice()
        if advice:
            logger.info("Testing health advice email...")
            email_service.send_daily_summary(advice)
        else:
            logger.warning("No health advice data found")
            
        logger.info("Email service test completed")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    test_email_service() 