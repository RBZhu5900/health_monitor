from flask import Flask, render_template, jsonify, request, send_from_directory
import json
from pathlib import Path
import logging
from services.mi_sport_service import MiSportService
import os
from flask_cors import CORS
from services.health_advisor_service import HealthAdvisorService

# 创建Flask应用
app = Flask(__name__)
# 添加CORS支持
CORS(app)

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('health_monitor.log'),
            logging.StreamHandler()
        ]
    )

@app.route('/')
def index():
    try:
        config_path = Path(__file__).parent.parent / "data" / "config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
            username = config.get("username", "")
            password = "*" * len(config.get("password", ""))
            receiver_email = config.get("receiver_email", "")
            return render_template('index.html', 
                                username=username, 
                                password=password,
                                receiver_email=receiver_email)
    except Exception as e:
        return render_template('index.html', error=str(e))

@app.route('/update_credentials', methods=['POST'])
def update_credentials():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"success": False, "message": "用户名和密码不能为空"})
        
        config_path = Path(__file__).parent.parent / "data" / "config.json"
        with open(config_path, 'w') as f:
            json.dump({"username": username, "password": password}, f, indent=2)
            
        return jsonify({"success": True, "message": "更新成功"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/get_health_data')
def get_health_data():
    try:
        service = MiSportService()
        data = service.get_health_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/download_report')
def download_report():
    try:
        data_dir = Path("data_export")
        app.logger.debug(f"检查目录: {data_dir.absolute()}")
        
        if not data_dir.exists():
            app.logger.error("目录不存在")
            return jsonify({"success": False, "message": "没有可下载的报告"})
            
        files = list(data_dir.glob("api_response_*.txt"))
        app.logger.debug(f"找到文件: {[f.name for f in files]}")
        
        if not files:
            app.logger.error("目录为空")
            return jsonify({"success": False, "message": "没有可下载的报告"})
            
        latest_file = max(files, key=lambda x: x.stat().st_mtime)
        app.logger.debug(f"准备下载文件: {latest_file.name}")
        
        # 读取文件内容
        with open(latest_file, 'rb') as f:
            file_content = f.read()
            
        # 创建响应
        response = app.make_response(file_content)
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        response.headers["Content-Disposition"] = f"attachment; filename={latest_file.name}"
        response.headers["Content-Length"] = len(file_content)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        app.logger.debug(f"响应头: {dict(response.headers)}")
        return response
        
    except Exception as e:
        app.logger.error(f"下载失败: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/get_health_advice')
def get_health_advice():
    try:
        # 获取健康数据
        service = MiSportService()
        health_data = service.get_health_data()
        
        # 获取健康建议
        advisor = HealthAdvisorService()
        advice = advisor.get_health_advice(health_data)
        
        return jsonify({"success": True, "data": advice})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/update_email', methods=['POST'])
def update_email():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({"success": False, "message": "邮箱不能为空"})
            
        config_path = Path(__file__).parent.parent / "data" / "config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        config['receiver_email'] = email
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        return jsonify({"success": True, "message": "邮箱更新成功"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

if __name__ == '__main__':
    setup_logging()
    # 修改host参数，允许外部访问
    app.run(debug=True, port=5050, host='0.0.0.0')