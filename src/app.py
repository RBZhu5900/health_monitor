import threading
from web_app import create_app
from main import run_monitor
import logging
from pathlib import Path
import signal
import sys

def setup_logging():
    """Set up logging configuration"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'health_monitor.log'),
            logging.StreamHandler()
        ]
    )

def signal_handler(signum, frame):
    """Handle exit signals"""
    logger = logging.getLogger(__name__)
    logger.info("Received exit signal, stopping services...")
    sys.exit(0)

def start_monitor():
    """Start background monitoring service"""
    try:
        run_monitor(daemon=True)
    except Exception as e:
        logging.error(f"Monitor service error: {str(e)}")

def start_web():
    """Start web service"""
    try:
        app = create_app()
        app.run(host='0.0.0.0', port=5050, ssl_context=None)  # NO SSL
    except Exception as e:
        logging.error(f"Web service error: {str(e)}")

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Register signal handlers in main thread
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create background monitoring thread
        monitor_thread = threading.Thread(target=start_monitor, daemon=True)
        monitor_thread.start()
        logger.info("Background monitoring service started")
        
        # Start web service (main thread)
        logger.info("Starting web service...")
        start_web()
        
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        raise
    finally:
        logger.info("Application shutdown")

if __name__ == "__main__":
    main() 