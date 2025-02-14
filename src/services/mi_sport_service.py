import requests
import logging
import json
from pathlib import Path
import base64
from datetime import datetime, timedelta

class MiSportService:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_path = Path(__file__).parent.parent.parent / "data" / "config.json"
        self.user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 13_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/7.0.12(0x17000c2d) NetType/WIFI Language/zh_CN"
        self._load_config()
        self.session = requests.Session()

    def _load_config(self):
        """Load user credentials from config file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.username = config["username"]
                self.password = config["password"]
        except Exception as e:
            self.logger.error(f"Configuration error: {str(e)}")
            raise RuntimeError("Failed to load configuration")

    def _get_code(self):
        """获取access code"""
        self.logger.info("1. 获取access code")
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "User-Agent": "MiFit/4.6.0 (iPhone; iOS 14.0.1; Scale/2.00"
        }
        
        data = {
            "client_id": "HuaMi",
            "password": self.password,
            "redirect_uri": "https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html",
            "token": "access"
        }
        
        url = f"https://api-user.huami.com/registrations/+86{self.username}/tokens"
        
        try:
            # 不需要先GET请求，直接发送POST请求
            response = self.session.post(
                url,
                headers=headers,
                data=data,
                allow_redirects=False  # 不自动跟随重定向
            )
            
            self.logger.debug(f"响应状态码: {response.status_code}")
            self.logger.debug(f"响应Headers: {dict(response.headers)}")
            self.logger.debug(f"响应内容: {response.text[:500]}")
            
            # 检查状态码是否为302或303（重定向状态码）
            if response.status_code not in [302, 303]:
                self.logger.error(f"获取code失败，状态码: {response.status_code}")
                self.logger.error(f"响应内容: {response.text}")
                raise Exception(f"获取code失败，状态码: {response.status_code}")
            
            location = response.headers.get("Location", "")
            self.logger.debug(f"Location header: {location}")
            
            if "access=" not in location:
                self.logger.error("Location header中未找到access code")
                raise Exception("未找到access code")
            
            # 提取access参数
            access_param = location.split("access=")[1].split("&")[0]
            self.logger.info(f"获取到code: {access_param}")
            return access_param
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"请求异常: {str(e)}")
            raise Exception(f"请求异常: {str(e)}")

    def _login(self, code):
        """执行登录"""
        self.logger.info("2. 执行登录")
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "User-Agent": "MiFit/4.6.0 (iPhone; iOS 14.0.1; Scale/2.00"
        }
        
        data = {
            "app_name": "com.xiaomi.hm.health",
            "app_version": "4.6.0",
            "code": code,
            "country_code": "CN",
            "device_id": "2C8B4939-0CCD-4E94-8CBA-CB8EA6E613A1",
            "device_model": "phone",
            "grant_type": "access_token",
            "third_name": "huami_phone"
        }
        
        try:
            response = self.session.post(
                "https://account.huami.com/v2/client/login",
                headers=headers,
                data=data
            )
            
            self.logger.debug(f"登录响应状态码: {response.status_code}")
            self.logger.debug(f"完整的登录响应: {response.text}")
            
            login_data = response.json()
            
            # token_info 已经是一个字典，不需要额外的字符串处理
            token_info = login_data.get("token_info")
            
            if not token_info:
                self.logger.error("登录响应中未找到token_info")
                raise Exception("获取login_token失败, 请检查账户名或密码是否正确")
            
            self.logger.info(f"login_token: {token_info.get('login_token')}")
            
            return [
                str(token_info.get("user_id")),
                token_info.get("login_token"),
                token_info.get("app_token")
            ]
            
        except Exception as e:
            self.logger.error(f"登录请求失败: {str(e)}")
            raise Exception(f"登录失败: {str(e)}")

    def get_health_data(self) -> dict:
        """获取健康数据"""
        try:
            # 1. 获取access code
            code = self._get_code()
            
            # 2. 登录获取token
            login_res = self._login(code)
            user_id, login_token, app_token = login_res
            
            # 3. 获取数据
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            
            params = {
                "query_type": "summary",
                "device_type": "android_phone",
                "userid": user_id,
                "from_date": start_date,
                "to_date": end_date
            }
            
            headers = {
                "apptoken": app_token
            }
            
            response = self.session.get(
                "https://api-mifit.huami.com/v1/data/band_data.json",
                params=params,
                headers=headers
            )
            
            data = response.json()
            
            # 保存原始响应
            self._save_raw_response(response, start_date, end_date)
            
            # 处理数据
            self._process_data(data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"获取健康数据失败: {str(e)}")
            raise

    def _save_raw_response(self, response, start_date, end_date):
        """保存详细的健康数据"""
        # 清理旧文件
        data_dir = Path("data_export")
        data_dir.mkdir(exist_ok=True)
        for old_file in data_dir.glob("api_response_*.txt"):
            old_file.unlink()
            
        filename = data_dir / f"api_response_{start_date.replace('-', '')}_{end_date.replace('-', '')}.txt"
        
        try:
            data = response.json()
            if not data.get("data"):
                return
                
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"=== 小米运动健康数据 ===\n")
                f.write(f"统计周期: {start_date} 至 {end_date}\n")
                f.write(f"响应状态: {data.get('code')} - {data.get('message')}\n\n")
                
                for item in data["data"]:
                    f.write(f"日期: {item['date_time']}\n")
                    f.write("-" * 50 + "\n")
                    f.write(f"用户ID: {item['uid']}\n")
                    f.write(f"数据类型: {item['data_type']}\n")
                    f.write(f"数据来源: {item['source']}\n")
                    f.write(f"设备ID: {item['device_id']}\n")
                    f.write(f"UUID: {item['uuid']}\n\n")
                    
                    try:
                        summary = base64.b64decode(item["summary"]).decode('utf-8')
                        summary_json = json.loads(summary)
                        
                        f.write("数据版本: v" + str(summary_json.get('v', '未知')) + "\n\n")
                        
                        # 睡眠数据详情
                        if "slp" in summary_json:
                            slp = summary_json["slp"]
                            f.write("睡眠数据详情:\n")
                            f.write(f"  开始时间戳: {slp.get('st')} ({datetime.fromtimestamp(slp.get('st', 0)).strftime('%Y-%m-%d %H:%M:%S')})\n")
                            f.write(f"  结束时间戳: {slp.get('ed')} ({datetime.fromtimestamp(slp.get('ed', 0)).strftime('%Y-%m-%d %H:%M:%S')})\n")
                            f.write(f"  深睡时长: {slp.get('dp')} 分钟\n")
                            f.write(f"  浅睡时长: {slp.get('lt')} 分钟\n")
                            f.write(f"  清醒次数: {slp.get('wk')} 次\n")
                            f.write(f"  用户设置开始时间: {slp.get('usrSt')} 分钟\n")
                            f.write(f"  用户设置结束时间: {slp.get('usrEd')} 分钟\n")
                            f.write(f"  清醒持续: {slp.get('wc')} 分钟\n")
                            f.write(f"  入睡状态: {slp.get('is')}\n")
                            f.write(f"  睡眠评分: {slp.get('lb')}\n")
                            f.write(f"  睡眠目标: {slp.get('to')} 分钟\n")
                            f.write(f"  睡眠偏差: {slp.get('dt')} 分钟\n")
                            f.write(f"  静息心率: {slp.get('rhr')} bpm\n")
                            f.write(f"  睡眠得分: {slp.get('ss')}\n\n")
                        
                        # 步数数据详情
                        if "stp" in summary_json:
                            stp = summary_json["stp"]
                            f.write("步数数据详情:\n")
                            f.write(f"  总步数: {stp.get('ttl', 0):,} 步\n")
                            f.write(f"  总距离: {stp.get('dis', 0):,} 米\n")
                            f.write(f"  消耗卡路里: {stp.get('cal', 0):,} 千卡\n")
                            f.write(f"  步行时间: {stp.get('wk', 0)} 分钟\n")
                            f.write(f"  跑步次数: {stp.get('rn', 0)} 次\n")
                            f.write(f"  跑步距离: {stp.get('runDist', 0):,} 米\n")
                            f.write(f"  跑步消耗: {stp.get('runCal', 0):,} 千卡\n\n")
                            
                            # 运动阶段详情
                            if "stage" in stp:
                                f.write("运动阶段详情:\n")
                                for i, stage in enumerate(stp["stage"], 1):
                                    f.write(f"  阶段 {i}:\n")
                                    f.write(f"    开始时间点: {stage.get('start')} 分钟\n")
                                    f.write(f"    结束时间点: {stage.get('stop')} 分钟\n")
                                    f.write(f"    运动模式: {self._get_mode_description(stage.get('mode'))}\n")
                                    f.write(f"    距离: {stage.get('dis', 0):,} 米\n")
                                    f.write(f"    消耗: {stage.get('cal', 0)} 千卡\n")
                                    f.write(f"    步数: {stage.get('step', 0):,} 步\n\n")
                        
                        # 其他数据
                        f.write("其他数据:\n")
                        f.write(f"  目标步数: {summary_json.get('goal', 0):,} 步\n")
                        f.write(f"  时区: {summary_json.get('tz')} 秒\n")
                        f.write(f"  数据长度: {summary_json.get('byteLength')} 字节\n")
                        f.write(f"  同步时间戳: {summary_json.get('sync')} ({datetime.fromtimestamp(summary_json.get('sync', 0)/1000).strftime('%Y-%m-%d %H:%M:%S')})\n")
                        
                        f.write("\n" + "=" * 50 + "\n\n")
                        
                    except Exception as e:
                        f.write(f"数据解析错误: {str(e)}\n\n")
                
            self.logger.info(f"详细健康数据报告已保存至：{filename}")
            
        except Exception as e:
            self.logger.error(f"保存数据失败: {str(e)}")

    def _get_mode_description(self, mode):
        """获取运动模式描述"""
        modes = {
            1: "步行",
            3: "快走",
            4: "跑步",
            5: "骑行"
        }
        return modes.get(mode, f"未知模式({mode})")

    def _process_data(self, data):
        """处理数据"""
        if not data.get("data"):
            return
            
        for item in data["data"]:
            if "summary" not in item:
                continue
                
            try:
                summary = base64.b64decode(item["summary"]).decode('utf-8')
                summary_json = json.loads(summary)
                item["summary_decoded"] = summary_json
                
                if "stp" in summary_json:
                    stp = summary_json["stp"]
                    item["total_steps"] = stp.get("ttl", 0)
                    item["distance"] = stp.get("dis", 0)
                    item["calories"] = stp.get("cal", 0)
                
                if "slp" in summary_json:
                    slp = summary_json["slp"]
                    item["deep_sleep"] = slp.get("dp", 0)
                    item["light_sleep"] = slp.get("lt", 0)
                    
            except Exception as e:
                self.logger.error(f"处理数据失败: {str(e)}")
                item["parse_error"] = str(e) 