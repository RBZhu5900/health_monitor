from openai import OpenAI
import json
from pathlib import Path
import logging
from datetime import datetime

class HealthAdvisorService:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_path = Path(__file__).parent.parent.parent / "data" / "config.json"
        self._load_config()
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def _load_config(self):
        """Load configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                deepseek_config = config.get("deepseek", {})
                self.api_key = deepseek_config.get("api_key")
                self.base_url = deepseek_config.get("base_url")
                self.model = deepseek_config.get("model")
                
                # Health goal configuration
                health_config = config.get("health", {})
                self.step_goal = health_config.get("step_goal", 8000)
                self.sleep_hours = health_config.get("sleep_hours", {"min": 7, "max": 8})
                self.deep_sleep_ratio = health_config.get("deep_sleep_ratio", 0.2)
                
                if not all([self.api_key, self.base_url, self.model]):
                    raise ValueError("DeepSeek configuration is incomplete")
                
        except Exception as e:
            self.logger.error(f"Configuration error: {str(e)}")
            raise RuntimeError("Failed to load configuration")

    def get_health_advice(self, health_data):
        """Get health advice"""
        try:
            # Build prompt
            prompt = self._build_prompt(health_data)
            
            # Call DeepSeek API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional health advisor. Based on the user's exercise and sleep data,
                         provide specific health advice. The advice should include:
                         1. What to do at specific times during the day
                         2. Improvement suggestions based on the data
                         3. Encouragement if health goals are met
                         Please output in JSON format with the following fields:
                         {
                             "notifications": [
                                 {
                                     "time": "HH:MM",
                                     "message": "Specific advice content"
                                 }
                             ],
                             "daily_summary": "Daily summary",
                             "improvement_suggestions": ["Suggestion 1", "Suggestion 2"],
                             "achievements": ["Achievement 1", "Achievement 2"]
                         }"""
                    },
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )
            
            advice = response.choices[0].message.content
            
            # Print full response to console
            self.logger.info("AI response content:\n" + advice)
            
            # Extract JSON part
            json_str = self._extract_json(advice)
            if not json_str:
                raise ValueError("Unable to extract valid JSON data from response")
            
            # Parse JSON
            advice_json = json.loads(json_str)
            
            # Save JSON advice
            self._save_advice(json_str)
            
            return advice_json
            
        except Exception as e:
            self.logger.error(f"Failed to get health advice: {str(e)}")
            raise

    def _extract_json(self, text):
        """Extract JSON part from response text"""
        try:
            # Find positions of first { and last }
            start = text.find('{')
            end = text.rfind('}')
            
            if start == -1 or end == -1:
                self.logger.error("No JSON format data found in response")
                return None
            
            json_str = text[start:end + 1]
            
            # Validate if JSON is valid
            json.loads(json_str)  # 测试是否可以解析
            return json_str
            
        except Exception as e:
            self.logger.error(f"Failed to extract JSON: {str(e)}")
            return None

    def _build_prompt(self, health_data):
        """Build prompt"""
        if isinstance(health_data, dict) and "details" in health_data:
            # Build prompt with detailed data
            return f"""
             Please analyze the following health data and provide advice. Data includes summary and details:

             Summary data:
             {json.dumps(health_data["summary"], ensure_ascii=False, indent=2)}

             Detailed data:
             {health_data["details"]}
             
             Please pay special attention to:
             1. Step count goal achievement (target: {self.step_goal} steps)
             2. Exercise time distribution
             3. Sleep duration adequacy (recommended: {self.sleep_hours['min']}-{self.sleep_hours['max']} hours)
             4. Deep sleep ratio (recommended: above {self.deep_sleep_ratio*100}% of total sleep)
             5. Exercise intensity distribution
             
             Based on this data, provide specific time-based recommendations and improvement plans.
             """
        else:
            # Build prompt with summary data
            return f"""
             Please analyze the following health data and provide advice:
             
             {json.dumps(health_data, ensure_ascii=False, indent=2)}
             
             Please pay special attention to:
             1. Step count goal achievement (target: {self.step_goal} steps)
             2. Exercise time distribution
             3. Sleep duration adequacy (recommended: {self.sleep_hours['min']}-{self.sleep_hours['max']} hours)
             4. Deep sleep ratio (recommended: above {self.deep_sleep_ratio*100}% of total sleep)
             
             Based on this data, provide specific time-based recommendations and improvement plans.
             """

    def _save_advice(self, advice_json):
        """Save advice to file"""
        try:
            advice_dir = Path("data_export/advice")
            advice_dir.mkdir(exist_ok=True, parents=True)
            
            date_str = datetime.now().strftime("%Y%m%d")
            filename = advice_dir / f"health_advice_{date_str}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(advice_json)
                
            self.logger.info(f"Health advice saved to: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save advice: {str(e)}") 