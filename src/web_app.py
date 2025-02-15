from flask import Flask, render_template, jsonify, request, send_from_directory, redirect
import json
from pathlib import Path
import logging
from services.mi_fit_service import MiFitService
import os
from flask_cors import CORS
from services.health_advisor_service import HealthAdvisorService
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app():
    """Create Flask application"""
    app = Flask(__name__)
    CORS(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
    
    def setup_logging():
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('health_monitor.log'),
                logging.StreamHandler()
            ]
        )

    @app.before_request
    def before_request():
        # 如果不是 HTTPS，重定向到 HTTPS
        if not request.is_secure and not request.headers.get('X-Forwarded-Proto', 'http') == 'https':
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

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
                return jsonify({"success": False, "message": "Username and password cannot be empty"})
            
            config_path = Path(__file__).parent.parent / "data" / "config.json"
            with open(config_path, 'w') as f:
                json.dump({"username": username, "password": password}, f, indent=2)
                
            return jsonify({"success": True, "message": "Credentials updated successfully"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})

    @app.route('/get_health_data')
    def get_health_data():
        try:
            service = MiFitService()
            data = service.get_health_data()
            return jsonify(data)
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})

    @app.route('/download_report')
    def download_report():
        try:
            data_dir = Path("data_export")
            app.logger.debug(f"Checking directory: {data_dir.absolute()}")
            
            if not data_dir.exists():
                app.logger.error("Directory does not exist")
                return jsonify({"success": False, "message": "No reports available for download"})
                
            files = list(data_dir.glob("api_response_*.txt"))
            app.logger.debug(f"Found files: {[f.name for f in files]}")
            
            if not files:
                app.logger.error("Directory is empty")
                return jsonify({"success": False, "message": "No reports available for download"})
                
            latest_file = max(files, key=lambda x: x.stat().st_mtime)
            app.logger.debug(f"Preparing to download file: {latest_file.name}")
            
            # Read file content
            with open(latest_file, 'rb') as f:
                file_content = f.read()
                
            # Create response
            response = app.make_response(file_content)
            response.headers["Content-Type"] = "text/plain; charset=utf-8"
            response.headers["Content-Disposition"] = f"attachment; filename={latest_file.name}"
            response.headers["Content-Length"] = len(file_content)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            
            app.logger.debug(f"Response headers: {dict(response.headers)}")
            return response
            
        except Exception as e:
            app.logger.error(f"Download failed: {str(e)}")
            return jsonify({"success": False, "message": str(e)})

    @app.route('/get_health_advice')
    def get_health_advice():
        try:
            # Get health data
            service = MiFitService()
            health_data = service.get_health_data()
            
            # Get health advice
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
                return jsonify({"success": False, "message": "Email cannot be empty"})
                
            config_path = Path(__file__).parent.parent / "data" / "config.json"
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            config['receiver_email'] = email
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            return jsonify({"success": True, "message": "Email updated successfully"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5050, host='0.0.0.0')