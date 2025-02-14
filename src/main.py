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
    """获取最新的健康数据文件内容"""
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
        logging.error(f"读取健康数据失败: {str(e)}")
        return None

def health_monitor_task():
    """健康监控任务"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("开始健康监控流程")
        
        # 1. 获取健康数据
        service = MiSportService()
        health_data = service.get_health_data()
        logger.info("成功获取健康数据")
        
        # 2. 获取健康建议
        advisor = HealthAdvisorService()
        
        # 从文件读取详细的健康数据
        detailed_data = get_latest_health_data()
        if detailed_data:
            combined_data = {
                "summary": health_data,
                "details": detailed_data
            }
        else:
            combined_data = health_data
            
        advice = advisor.get_health_advice(combined_data)
        logger.info("成功获取健康建议")
        
        # 添加提醒邮件任务
        scheduler.add_notification_jobs(advice["notifications"])
        
        # 3. 保存建议到文本文件
        data_dir = Path("data_export")
        advice_file = data_dir / f"health_advice_{datetime.now().strftime('%Y%m%d')}.txt"
        
        with open(advice_file, 'w', encoding='utf-8') as f:
            f.write("=== 健康建议 ===\n\n")
            f.write("每日提醒：\n")
            for notification in advice["notifications"]:
                f.write(f"[{notification['time']}] {notification['message']}\n")
            
            f.write("\n每日总结：\n")
            f.write(advice["daily_summary"])
            
            f.write("\n\n改进建议：\n")
            for suggestion in advice["improvement_suggestions"]:
                f.write(f"- {suggestion}\n")
            
            f.write("\n成就：\n")
            for achievement in advice["achievements"]:
                f.write(f"- {achievement}\n")
            
            f.write("\n\n=== 原始数据 ===\n")
            f.write(json.dumps(advice, ensure_ascii=False, indent=2))
            
        logger.info(f"健康建议已保存至：{advice_file}")
        
    except Exception as e:
        logger.error(f"任务执行失败: {str(e)}")

def signal_handler(signum, frame):
    """处理退出信号"""
    logger = logging.getLogger(__name__)
    logger.info("接收到退出信号，正在停止服务...")
    scheduler.stop()
    sys.exit(0)

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # 注册信号处理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 创建并启动调度器
        global scheduler
        scheduler = SchedulerService(health_monitor_task)
        scheduler.start()
        
        # 立即执行一次任务
        health_monitor_task()
        
        # 保持程序运行
        while True:
            signal.pause()
            
    except Exception as e:
        logger.error(f"程序运行失败: {str(e)}")
        raise

if __name__ == "__main__":
    main() 