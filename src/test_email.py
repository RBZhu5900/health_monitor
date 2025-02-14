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
    """获取最新的健康建议"""
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
        logging.error(f"读取健康建议失败: {str(e)}")
        return None

def test_email_service():
    """测试邮件服务"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("开始测试邮件服务")
        
        # 创建邮件服务实例
        email_service = EmailService()
        
        # 测试发送简单通知
        logger.info("测试发送通知邮件...")
        email_service.send_notification(
            "测试时间",
            "这是一条测试通知，用于验证邮件服务是否正常工作。"
        )
        
        # 获取最新的健康建议
        advice = get_latest_advice()
        if advice:
            logger.info("测试发送健康建议...")
            email_service.send_daily_summary(advice)
        else:
            logger.warning("未找到健康建议数据")
            
        logger.info("邮件服务测试完成")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        raise

if __name__ == "__main__":
    test_email_service() 