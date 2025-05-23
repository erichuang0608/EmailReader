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
            m = re.search(r'^(?:时间|Date|Sent)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                try:
                    meta['date'] = parsedate_to_datetime(clean(m.group(1)))
                except Exception:
                    meta['date'] = clean(m.group(1))
            m = re.search(r'^(?:发件人|From)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['from'] = extract_name_email(clean(m.group(1)))
            m = re.search(r'^(?:收件人|To)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['to'] = extract_name_email(clean(m.group(1)))
            m = re.search(r'^(?:抄送|Cc)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['cc'] = extract_name_email(clean(m.group(1)))
            m = re.search(r'^(?:主题|Subject)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['subject'] = clean(m.group(1))
            return meta
        def llm_extract_metadata(text):
            if not self.azure_client:
                return {}
            prompt = (
                "请从以下邮件内容中提取元数据，返回JSON，字段包括：时间、发件人（姓名和邮箱）、收件人（姓名和邮箱）、抄送（姓名和邮箱）、主题。"
                "格式示例：{\"date\": \"...\", \"from\": [[\"姓名\", \"邮箱\"]], \"to\": [[\"姓名\", \"邮箱\"]], \"cc\": [[\"姓名\", \"邮箱\"]], \"subject\": \"...\"}\n"
                "邮件内容：\n" + text
            )
            resp = self.azure_client._call_openai(prompt, 300)
            import json
            try:
                return json.loads(resp['choices'][0]['message']['content'])
            except Exception:
                return {}
        for h in history:
            meta = _extract_metadata_from_history(h)
            if not all([meta.get("date"), meta.get("from"), meta.get("to"), meta.get("subject")]):
                llm_meta = llm_extract_metadata(h)
                for k in ["date", "from", "to", "cc", "subject"]:
                    if not meta.get(k) and llm_meta.get(k):
                        meta[k] = llm_meta[k]
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
        return thread

    def _split_mail_history(self, body: str) -> list:
        import re
        # 匹配所有以From:或发件人：开头的历史邮件块，保留头部
        pattern = r'((?:From:|发件人：)[\s\S]+?)(?=(?:From:|发件人：|$))'
        matches = re.findall(pattern, body)
        return [m.strip() for m in matches] if matches else [] 