from typing import Dict, List
from src.azure_openai_client import AzureOpenAIClient
import json

class MailAnalyzer:
    def __init__(self, azure_client: AzureOpenAIClient):
        self.azure_client = azure_client

    def analyze_mail(self, mail_data: Dict) -> Dict:
        text = mail_data.get('body', '')
        summary = self.azure_client.generate_summary(text)
        entities = self.azure_client.extract_entities(text)
        action_items = self.azure_client.analyze_action_items(text)
        sentiment = self.azure_client.detect_sentiment(text)
        # 风险点检测可用实体/摘要等再分析
        risk_points = self._detect_risks(summary, entities, action_items)
        return {
            "summary": summary,
            "entities": entities,
            "action_items": action_items,
            "sentiment": sentiment,
            "risk_points": risk_points
        }

    def analyze_conversation(self, mail_thread: List[Dict]) -> Dict:
        # 合并对话内容，整体分析
        all_text = "\n\n".join([m.get('body', '') for m in mail_thread])
        return self.analyze_mail({'body': all_text})

    def _detect_risks(self, summary, entities, action_items):
        # 简单用OpenAI再分析风险点
        prompt = f"请根据以下内容识别潜在风险点，返回JSON数组：\n摘要：{summary}\n实体：{entities}\n行动项：{action_items}"
        resp = self.azure_client._call_openai(prompt, 200)
        try:
            content = resp['choices'][0]['message']['content']
            return json.loads(content)
        except Exception:
            return [] 