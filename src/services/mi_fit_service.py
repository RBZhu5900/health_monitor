import requests
import logging
import json
from pathlib import Path
import base64
from datetime import datetime, timedelta

class MiFitService:
    """Service for interacting with Zepp(Mi Fit) API"""
    def __init__(self, proxies=None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_path = Path(__file__).parent.parent.parent / "data" / "config.json"
        self.user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 13_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/7.0.12(0x17000c2d) NetType/WIFI Language/zh_CN"
        self.session = requests.Session()
        self.proxies = proxies
        self._load_config()

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
        """Get access code"""
        self.logger.info("1. Getting access code")
        
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
        
        url = f"https://api-user.huami.com/registrations/{self.username}/tokens"
        
        try:
            # No need for GET request first, directly send POST request
            response = self.session.post(
                url,
                headers=headers,
                data=data,
                allow_redirects=False,  # Don't follow redirects automatically
                proxies=self.proxies
            )
            
            self.logger.debug(f"Response status code: {response.status_code}")
            self.logger.debug(f"Response Headers: {dict(response.headers)}")
            self.logger.debug(f"Response content: {response.text[:500]}")
            
            # Check if status code is 302 or 303 (redirect status codes)
            if response.status_code not in [302, 303]:
                self.logger.error(f"Failed to get code, status code: {response.status_code}")
                self.logger.error(f"Response content: {response.text}")
                raise Exception(f"Failed to get code, status code: {response.status_code}")
            
            location = response.headers.get("Location", "")
            self.logger.debug(f"Location header: {location}")
            
            if "access=" not in location:
                self.logger.error("Access code not found in Location header")
                raise Exception("Access code not found")
            
            # Extract access parameter
            access_param = location.split("access=")[1].split("&")[0]
            self.logger.info(f"Got code: {access_param}")
            return access_param
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {str(e)}")
            raise Exception(f"Request error: {str(e)}")

    def _login(self, code):
        """Perform login"""
        self.logger.info("2. Performing login")
        
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
            
            self.logger.debug(f"Login response status code: {response.status_code}")
            self.logger.debug(f"Complete login response: {response.text}")
            
            login_data = response.json()
            
            # token_info is already a dictionary, no extra string processing needed
            token_info = login_data.get("token_info")
            
            if not token_info:
                self.logger.error("token_info not found in login response")
                raise Exception("Failed to get login_token, please check username and password")
            
            self.logger.info(f"Got login_token: {token_info.get('login_token')}")
            
            return [
                str(token_info.get("user_id")),
                token_info.get("login_token"),
                token_info.get("app_token")
            ]
            
        except Exception as e:
            self.logger.error(f"Login request failed: {str(e)}")
            raise Exception(f"Login failed: {str(e)}")

    def get_health_data(self) -> dict:
        """Get health data"""
        try:
            # 1. Get access code
            code = self._get_code()
            
            # 2. Get access token
            login_res = self._login(code)
            user_id, login_token, app_token = login_res
            
            # 3. Get activity data
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
            
            # Save raw response
            self._save_raw_response(response, start_date, end_date)
            
            # Process data
            self._process_data(data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to get health data: {str(e)}")
            raise

    def _save_raw_response(self, response, start_date, end_date):
        """Save detailed health data"""
        # Clean up old files
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
                f.write(f"=== Zepp Health Data ===\n")
                f.write(f"Statistics Period: {start_date} to {end_date}\n")
                f.write(f"Response Status: {data.get('code')} - {data.get('message')}\n\n")
                
                for item in data["data"]:
                    f.write(f"Date: {item['date_time']}\n")
                    f.write("-" * 50 + "\n")
                    f.write(f"User ID: {item['uid']}\n")
                    f.write(f"Data Type: {item['data_type']}\n")
                    f.write(f"Data Source: {item['source']}\n")
                    f.write(f"Device ID: {item['device_id']}\n")
                    f.write(f"UUID: {item['uuid']}\n\n")
                    
                    try:
                        summary = base64.b64decode(item["summary"]).decode('utf-8')
                        summary_json = json.loads(summary)
                        
                        f.write("Data Version: v" + str(summary_json.get('v', 'Unknown')) + "\n\n")
                        
                        # Sleep data details
                        if "slp" in summary_json:
                            slp = summary_json["slp"]
                            f.write("Sleep Data Details:\n")
                            f.write(f"  Start Timestamp: {slp.get('st')}\n")
                            f.write(f"  End Timestamp: {slp.get('ed')}\n")
                            f.write(f"  Deep Sleep Duration: {slp.get('dp')} minutes\n")
                            f.write(f"  Light Sleep Duration: {slp.get('lt')} minutes\n")
                            f.write(f"  Wake Count: {slp.get('wk')} times\n")
                            f.write(f"  User Set Start Time: {slp.get('usrSt')} minutes\n")
                            f.write(f"  User Set End Time: {slp.get('usrEd')} minutes\n")
                            f.write(f"  Wake Duration: {slp.get('wc')} minutes\n")
                            f.write(f"  Sleep State: {slp.get('is')}\n")
                            f.write(f"  Sleep Score: {slp.get('lb')}\n")
                            f.write(f"  Sleep Goal: {slp.get('to')} minutes\n")
                            f.write(f"  Sleep Deviation: {slp.get('dt')} minutes\n")
                            f.write(f"  Resting Heart Rate: {slp.get('rhr')} bpm\n")
                            f.write(f"  Sleep Score: {slp.get('ss')}\n\n")
                        
                        # Step data details
                        if "stp" in summary_json:
                            stp = summary_json["stp"]
                            f.write("Step Data Details:\n")
                            f.write(f"  Total Steps: {stp.get('ttl', 0):,} steps\n")
                            f.write(f"  Total Distance: {stp.get('dis', 0):,} meters\n")
                            f.write(f"  Calories Burned: {stp.get('cal', 0):,} kcal\n")
                            f.write(f"  Walking Duration: {stp.get('wk', 0)} minutes\n")
                            f.write(f"  Running Count: {stp.get('rn', 0)} times\n")
                            f.write(f"  Running Distance: {stp.get('runDist', 0):,} meters\n")
                            f.write(f"  Running Calories: {stp.get('runCal', 0):,} kcal\n\n")
                            
                            # Activity stage details
                            if "stage" in stp:
                                f.write("Activity Stage Details:\n")
                                for i, stage in enumerate(stp["stage"], 1):
                                    f.write(f"  Stage {i}:\n")
                                    f.write(f"    Start Time: {stage.get('start')} minutes\n")
                                    f.write(f"    End Time: {stage.get('stop')} minutes\n")
                                    f.write(f"    Activity Mode: {self._get_mode_description(stage.get('mode'))}\n")
                                    f.write(f"    Distance: {stage.get('dis', 0):,} meters\n")
                                    f.write(f"    Calories: {stage.get('cal', 0)} kcal\n")
                                    f.write(f"    Steps: {stage.get('step', 0):,} steps\n\n")
                        
                        # Other data
                        f.write("Other Data:\n")
                        f.write(f"  Step Goal: {summary_json.get('goal', 0):,} steps\n")
                        f.write(f"  Timezone: {summary_json.get('tz')} seconds\n")
                        f.write(f"  Data Length: {summary_json.get('byteLength')} bytes\n")
                        f.write(f"  Sync Timestamp: {summary_json.get('sync')} ({datetime.fromtimestamp(summary_json.get('sync', 0)/1000).strftime('%Y-%m-%d %H:%M:%S')})\n")
                        
                        f.write("\n" + "=" * 50 + "\n\n")
                        
                    except Exception as e:
                        f.write(f"Data parsing error: {str(e)}\n\n")
                
            self.logger.info(f"Detailed health data report saved to: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save data: {str(e)}")

    def _get_mode_description(self, mode):
        """Get activity mode description"""
        modes = {
            1: "Walking",
            3: "Fast Walking",
            4: "Running",
            5: "Cycling"
        }
        return modes.get(mode, f"Unknown mode({mode})")

    def _process_data(self, data):
        """Process data"""
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
                self.logger.error(f"Failed to process data: {str(e)}")
                item["parse_error"] = str(e) 