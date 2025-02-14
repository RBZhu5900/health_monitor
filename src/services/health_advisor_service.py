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
        """加载配置"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                deepseek_config = config.get("deepseek", {})
                self.api_key = deepseek_config.get("api_key")
                self.base_url = deepseek_config.get("base_url")
                self.model = deepseek_config.get("model")
                
                # 健康目标配置
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
        """获取健康建议"""
        try:
            # 构建提示信息
            prompt = self._build_prompt(health_data)
            
            # 调用 DeepSeek API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """你是一个专业的健康顾问。请根据用户的运动和睡眠数据，
                        提供具体的健康建议。建议应该包括：
                        1. 在一天中的具体时间点应该做什么
                        2. 针对数据显示的问题提出改进建议
                        3. 如果达到了健康目标，给予鼓励
                        请用JSON格式输出，包含以下字段：
                        {
                            "notifications": [
                                {
                                    "time": "HH:MM",
                                    "message": "具体建议内容"
                                }
                            ],
                            "daily_summary": "当天总结",
                            "improvement_suggestions": ["改进建议1", "改进建议2"],
                            "achievements": ["达成的成就1", "达成的成就2"]
                        }"""
                    },
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )
            
            advice = response.choices[0].message.content
            
            # 打印完整响应到控制台
            self.logger.info("AI响应内容：\n" + advice)
            
            # 提取JSON部分
            json_str = self._extract_json(advice)
            if not json_str:
                raise ValueError("无法从响应中提取有效的JSON数据")
            
            # 解析JSON
            advice_json = json.loads(json_str)
            
            # 保存JSON建议
            self._save_advice(json_str)
            
            return advice_json
            
        except Exception as e:
            self.logger.error(f"获取健康建议失败: {str(e)}")
            raise

    def _extract_json(self, text):
        """从响应文本中提取JSON部分"""
        try:
            # 查找第一个 { 和最后一个 } 的位置
            start = text.find('{')
            end = text.rfind('}')
            
            if start == -1 or end == -1:
                self.logger.error("响应中未找到JSON格式数据")
                return None
            
            json_str = text[start:end + 1]
            
            # 验证是否为有效的JSON
            json.loads(json_str)  # 测试是否可以解析
            return json_str
            
        except Exception as e:
            self.logger.error(f"提取JSON失败: {str(e)}")
            return None

    def _build_prompt(self, health_data):
        """构建提示信息"""
        if isinstance(health_data, dict) and "details" in health_data:
            # 使用详细数据构建提示
            return f"""
            请分析以下健康数据并提供建议。数据包含概要和详细信息：

            概要数据：
            {json.dumps(health_data["summary"], ensure_ascii=False, indent=2)}

            详细数据：
            {health_data["details"]}
            
            请特别关注：
            1. 步数是否达标（目标{self.step_goal}步）
            2. 运动时间分布是否合理
            3. 睡眠时间是否充足（建议{self.sleep_hours['min']}-{self.sleep_hours['max']}小时）
            4. 深睡眠比例是否合适（建议占总睡眠时间的{self.deep_sleep_ratio*100}%以上）
            5. 运动强度的分布情况
            
            请根据这些数据，提供具体的时间点建议和改进方案。
            """
        else:
            # 使用简要数据构建提示
            return f"""
            请分析以下健康数据并提供建议：
            
            {json.dumps(health_data, ensure_ascii=False, indent=2)}
            
            请特别关注：
            1. 步数是否达标（目标{self.step_goal}步）
            2. 运动时间分布是否合理
            3. 睡眠时间是否充足（建议{self.sleep_hours['min']}-{self.sleep_hours['max']}小时）
            4. 深睡眠比例是否合适（建议占总睡眠时间的{self.deep_sleep_ratio*100}%以上）
            
            请根据这些数据，提供具体的时间点建议和改进方案。
            """

    def _save_advice(self, advice_json):
        """保存建议到文件"""
        try:
            advice_dir = Path("data_export/advice")
            advice_dir.mkdir(exist_ok=True, parents=True)
            
            date_str = datetime.now().strftime("%Y%m%d")
            filename = advice_dir / f"health_advice_{date_str}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(advice_json)
                
            self.logger.info(f"健康建议已保存至：{filename}")
            
        except Exception as e:
            self.logger.error(f"保存建议失败: {str(e)}") 