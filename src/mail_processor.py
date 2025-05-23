import os
from typing import List, Dict
import mailparser
from datetime import datetime
from email.utils import parsedate_to_datetime
import html

class MailProcessor:
    def __init__(self, mail_dir: str, azure_client=None):
        self.mail_dir = mail_dir
        self.azure_client = azure_client

    def process_all_mails(self) -> List[Dict]:
        mails = []
        for root, _, files in os.walk(self.mail_dir):
            for file in files:
                if file.lower().endswith('.eml'):
                    path = os.path.join(root, file)
                    try:
                        mail = self.parse_mail(path)
                        mails.append(mail)
                    except Exception as e:
                        print(f"Failed to parse {path}: {e}")
        return mails

    def parse_mail(self, file_path: str) -> Dict:
        mail = mailparser.parse_from_file(file_path)
        metadata = {
            "subject": mail.subject,
            "from": mail.from_[0][1] if mail.from_ else None,
            "to": [addr[1] for addr in mail.to] if mail.to else [],
            "date": mail.date.isoformat() if mail.date else None
        }
        body = mail.body or mail.text_plain[0] if mail.text_plain else ''
        attachments = []
        for att in mail.attachments:
            attachments.append({
                "filename": att.get("filename"),
                "payload": att.get("payload"),
                "mail_content_type": att.get("mail_content_type")
            })
        return {
            "mail_path": file_path,
            "metadata": metadata,
            "body": body,
            "attachments": attachments
        }

    def parse_mail_thread(self, file_path: str) -> list:
        import re
        mail = mailparser.parse_from_file(file_path)
        body = mail.body or (mail.text_plain[0] if mail.text_plain else '')
        history = self._split_mail_history(body)
        thread = []
        def extract_name_email(s):
            matches = re.findall(r'([\w\s\.\'\-]+)?\s*<([\w\.-]+@[\w\.-]+)>', s)
            if matches:
                return [(name.strip(), email) for name, email in matches]
            emails = re.findall(r'[\w\.-]+@[\w\.-]+', s)
            return [('', email) for email in emails] if emails else [(s, '')]
        def _extract_metadata_from_history(text):
            meta = {}
            def clean(s):
                if not s:
                    return ""
                s = re.sub(r'<[^>]+>', '', str(s))
                s = html.unescape(s)
                return s.strip()
            # 新增：去除每行前后空白
            lines = [line.strip() for line in text.splitlines()]
            text = "\n".join(lines)
            m = re.search(r'^\s*(?:时间|Date|Sent)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                try:
                    meta['date'] = parsedate_to_datetime(clean(m.group(1)))
                except Exception:
                    meta['date'] = clean(m.group(1))
            m = re.search(r'^\s*(?:发件人|From)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['from'] = extract_name_email(clean(m.group(1)))
            m = re.search(r'^\s*(?:收件人|To)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['to'] = extract_name_email(clean(m.group(1)))
            m = re.search(r'^\s*(?:抄送|Cc)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['cc'] = extract_name_email(clean(m.group(1)))
            m = re.search(r'^\s*(?:主题|Subject)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['subject'] = clean(m.group(1))
            return meta
        def llm_extract_metadata(text):
            if not self.azure_client:
                return {}
            prompt = (
                "请从以下邮件内容中提取元数据，只返回JSON，字段包括：date, from, to, cc, subject。"
                "格式示例：{\"date\": \"...\", \"from\": [[\"姓名\", \"邮箱\"]], \"to\": [[\"姓名\", \"邮箱\"]], \"cc\": [[\"姓名\", \"邮箱\"]], \"subject\": \"...\"}\n"
                "邮件内容：\n" + text
            )
            resp = self.azure_client._call_openai(prompt, 300)
            import json, re
            try:
                content = resp['choices'][0]['message']['content']
                print("LLM元数据返回：", content)
                # 尝试只提取第一个大括号包裹的 JSON
                match = re.search(r'\{[\s\S]*\}', content)
                if match:
                    content = match.group(0)
                data = json.loads(content)
                # 字段名中英文自动映射
                field_map = {
                    '时间': 'date', '发件人': 'from', '收件人': 'to', '抄送': 'cc', '主题': 'subject',
                    'date': 'date', 'from': 'from', 'to': 'to', 'cc': 'cc', 'subject': 'subject'
                }
                mapped = {}
                for k, v in data.items():
                    std_k = field_map.get(k, k)
                    mapped[std_k] = v
                return mapped
            except Exception as e:
                print("LLM元数据解析失败：", e)
                return {}
        for h in history:
            meta = llm_extract_metadata(h)
            # 如果 LLM 失败或返回不全，再用正则兜底补全
            if not all([meta.get("date"), meta.get("from"), meta.get("to"), meta.get("subject")]):
                regex_meta = _extract_metadata_from_history(h)
                for k in ["date", "from", "to", "cc", "subject"]:
                    if not meta.get(k) and regex_meta.get(k):
                        meta[k] = regex_meta[k]
            thread.append({
                "subject": meta.get("subject", "未知"),
                "from": meta.get("from", "未知"),
                "to": meta.get("to", "未知"),
                "cc": meta.get("cc", "未知"),
                "date": meta.get("date", "未知"),
                "body": h,
                "attachments": []
            })
        for idx, mail in enumerate(thread, 1):
            mail['idx'] = idx
        # 去重：按发件人+时间+主题唯一性
        seen = set()
        unique_thread = []
        for mail in thread:
            key = (str(mail['from']), str(mail['date']), str(mail['subject']))
            if key not in seen:
                seen.add(key)
                unique_thread.append(mail)
        # 兜底：如果thread为空，则用主邮件整体内容填充
        if not unique_thread:
            meta = {
                "subject": mail.subject,
                "from": mail.from_,
                "to": mail.to,
                "cc": mail.cc,
                "date": mail.date,
            }
            unique_thread = [{
                "subject": meta.get("subject", "未知"),
                "from": meta.get("from", "未知"),
                "to": meta.get("to", "未知"),
                "cc": meta.get("cc", "未知"),
                "date": meta.get("date", "未知"),
                "body": body,
                "attachments": mail.attachments,
                "idx": 1
            }]
        return unique_thread

    def _split_mail_history(self, body: str) -> list:
        import re
        # 1. 尝试From/发件人
        pattern1 = r'((?:From:|发件人：)[\s\S]+?)(?=(?:From:|发件人：|$))'
        matches = re.findall(pattern1, body)
        if matches:
            return [m.strip() for m in matches if m.strip()]
        # 2. 尝试Original Message
        pattern2 = r'(-----Original Message-----[\s\S]+?)(?=(-----Original Message-----|$))'
        matches = re.findall(pattern2, body)
        if matches:
            return [m[0].strip() for m in matches if m[0].strip()]
        # 3. 尝试On ... wrote:
        pattern3 = r'(On .+?wrote:[\s\S]+?)(?=(On .+?wrote:|$))'
        matches = re.findall(pattern3, body)
        if matches:
            return [m[0].strip() for m in matches if m[0].strip()]
        return [] 