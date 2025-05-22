import requests
import time
import json
from typing import Dict, List
from loguru import logger
from src.utils import load_json

class AzureOpenAIClient:
    def __init__(self, config_path: str):
        self.config = load_json(config_path)
        self.endpoint = self.config['azure_openai']['endpoint']
        self.api_key = self.config['azure_openai']['api_key']
        self.api_version = self.config['azure_openai']['api_version']
        self.deployment = self.config['azure_openai']['deployment_name']
        self.rpm = self.config['rate_limit']['rpm']
        self.max_retries = self.config['rate_limit']['max_retries']
        self.usage_log = self.config['cost_tracking']['log_path']
        self.last_request_time = 0
        self.interval = 60.0 / self.rpm

    def _call_openai(self, prompt: str, max_tokens: int = 300) -> Dict:
        url = f"{self.endpoint}openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2
        }
        for attempt in range(self.max_retries):
            now = time.time()
            if now - self.last_request_time < self.interval:
                time.sleep(self.interval - (now - self.last_request_time))
            self.last_request_time = time.time()
            try:
                resp = requests.post(url, headers=headers, json=data, timeout=30)
                if resp.status_code == 200:
                    self.track_api_usage(resp)
                    return resp.json()
                else:
                    logger.warning(f"OpenAI API error: {resp.status_code} {resp.text}")
            except Exception as e:
                logger.error(f"OpenAI API call failed: {e}")
            time.sleep(2 ** attempt)
        raise RuntimeError("OpenAI API调用失败")

    def generate_summary(self, text: str, max_tokens: int = 300) -> str:
        prompt = f"请用中文对以下内容生成简明摘要：\n{text}"
        resp = self._call_openai(prompt, max_tokens)
        return resp['choices'][0]['message']['content'].strip()

    def extract_entities(self, text: str) -> Dict:
        prompt = f"请从以下内容中提取人物、组织、日期、事件、地点等实体，返回JSON：\n{text}"
        resp = self._call_openai(prompt, 400)
        try:
            return json.loads(resp['choices'][0]['message']['content'])
        except Exception:
            return {"raw": resp['choices'][0]['message']['content']}

    def analyze_action_items(self, text: str) -> List[Dict]:
        prompt = f"请识别以下内容中的行动项，列出负责人、任务、截止日期、优先级，返回JSON数组：\n{text}"
        resp = self._call_openai(prompt, 400)
        try:
            return json.loads(resp['choices'][0]['message']['content'])
        except Exception:
            return [{"raw": resp['choices'][0]['message']['content']}]

    def detect_sentiment(self, text: str) -> str:
        prompt = f"请判断以下内容的情绪（积极、消极、中性）：\n{text}"
        resp = self._call_openai(prompt, 50)
        return resp['choices'][0]['message']['content'].strip()

    def track_api_usage(self, response) -> None:
        if not self.config['cost_tracking']['enabled']:
            return
        try:
            usage = response.json().get('usage', {})
            with open(self.usage_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "prompt_tokens": usage.get('prompt_tokens'),
                    "completion_tokens": usage.get('completion_tokens'),
                    "total_tokens": usage.get('total_tokens'),
                    "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }) + '\n')
        except Exception as e:
            logger.warning(f"API用量记录失败: {e}") 