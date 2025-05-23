from typing import Dict, List
from src.azure_openai_client import AzureOpenAIClient
import json
from datetime import datetime
import re
import html
import concurrent.futures

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

    def analyze_conversation(self, mail_thread: list) -> dict:
        def clean_text(s):
            if not s:
                return ""
            s = re.sub(r'<[^>]+>', '', str(s))
            s = html.unescape(s)
            return s.strip()
        def analyze_one(mail, idx):
            summary = self.azure_client.generate_summary(mail['body'])
            sentiment = self.azure_client.detect_sentiment(mail['body'])
            d = mail["date"]
            if isinstance(d, datetime):
                dt = d.strftime("%Y-%m-%d %H:%M:%S%z")
                time_short = d.strftime("%H:%M")
            elif isinstance(d, str) and d:
                dt = d
                m = re.search(r"(\d{1,2}:\d{2})", d)
                time_short = m.group(1) if m else d
            else:
                dt = ""
                time_short = ""
            from_name = ""
            if isinstance(mail["from"], list) and mail["from"]:
                if isinstance(mail["from"][0], tuple):
                    from_name = mail["from"][0][0] or mail["from"][0][1]
                else:
                    from_name = str(mail["from"][0])
            elif isinstance(mail["from"], str):
                from_name = mail["from"]
            dialogue_str = f"{from_name}，在{time_short}，邮件提到：{summary}"
            return {
                "idx": idx,
                "date": dt,
                "from": clean_text(mail["from"]),
                "to": clean_text(mail["to"]),
                "cc": clean_text(mail["cc"]),
                "subject": clean_text(mail["subject"]),
                "summary": summary,
                "sentiment": sentiment,
                "dialogue": dialogue_str
            }
        results = []
        dialogue = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(analyze_one, mail, idx) for idx, mail in enumerate(reversed(mail_thread), 1)]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                results.append(res)
        # 保证按idx倒序排列
        results = sorted(results, key=lambda x: x["idx"])
        dialogue = [r["dialogue"] for r in results]
        overall_summary = self.azure_client.generate_summary(
            "\n\n".join([m["body"] for m in mail_thread])
        )
        reply_suggestions = self.generate_reply_suggestions(overall_summary)
        return {
            "timeline": results,
            "dialogue": dialogue,
            "overall_summary": overall_summary,
            "reply_suggestions": reply_suggestions
        }

    def generate_reply_suggestions(self, summary: str) -> list:
        styles = ["正式", "中性", "友好"]
        suggestions = []
        for style in styles:
            prompt = f"请以{style}风格，基于以下内容，生成一段适合回复此邮件的建议：\n{summary}"
            resp = self.azure_client._call_openai(prompt, 200)
            suggestions.append(resp['choices'][0]['message']['content'])
        return suggestions

    def _detect_risks(self, summary, entities, action_items):
        # 简单用OpenAI再分析风险点
        prompt = f"请根据以下内容识别潜在风险点，返回JSON数组：\n摘要：{summary}\n实体：{entities}\n行动项：{action_items}"
        resp = self.azure_client._call_openai(prompt, 200)
        try:
            content = resp['choices'][0]['message']['content']
            return json.loads(content)
        except Exception:
            return [] 