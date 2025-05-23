import os
from typing import List, Dict
import mailparser
from datetime import datetime
from email.utils import parsedate_to_datetime
import html

class MailProcessor:
    def __init__(self, mail_dir: str):
        self.mail_dir = mail_dir

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
        """
        解析单个eml文件中的主邮件和历史邮件，返回按时间顺序的邮件链。
        """
        import re
        mail = mailparser.parse_from_file(file_path)
        thread = [{
            "subject": mail.subject,
            "from": mail.from_,
            "to": mail.to,
            "cc": mail.cc,
            "date": mail.date,
            "body": mail.body or (mail.text_plain[0] if mail.text_plain else ''),
            "attachments": mail.attachments
        }]
        body = thread[0]["body"]
        history = self._split_mail_history(body)
        def _extract_metadata_from_history(text):
            meta = {}
            def clean(s):
                if not s:
                    return ""
                s = re.sub(r'<[^>]+>', '', str(s))
                s = html.unescape(s)
                return s.strip()
            # 支持换行、冒号后有空格、大小写、分号分隔
            m = re.search(r'^(?:时间|Date)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                try:
                    meta['date'] = parsedate_to_datetime(clean(m.group(1)))
                except Exception:
                    meta['date'] = clean(m.group(1))
            m = re.search(r'^(?:发件人|From)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['from'] = clean(m.group(1))
            m = re.search(r'^(?:收件人|To)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['to'] = clean(m.group(1))
            m = re.search(r'^(?:抄送|Cc)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['cc'] = clean(m.group(1))
            m = re.search(r'^(?:主题|Subject)\s*[:：]?\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
            if m:
                meta['subject'] = clean(m.group(1))
            return meta
        for h in history:
            meta = _extract_metadata_from_history(h)
            thread.append({
                "subject": meta.get("subject", ""),
                "from": meta.get("from", ""),
                "to": meta.get("to", ""),
                "cc": meta.get("cc", ""),
                "date": meta.get("date", ""),
                "body": h,
                "attachments": []
            })
        def _date_key(x):
            d = x["date"]
            if isinstance(d, datetime):
                # 转为offset-naive
                if d.tzinfo is not None:
                    return d.replace(tzinfo=None)
                return d
            if isinstance(d, str) and d:
                try:
                    return datetime.fromisoformat(d)
                except Exception:
                    return datetime.min
            return datetime.min
        thread = sorted(thread, key=_date_key)
        return thread

    def _split_mail_history(self, body: str) -> list:
        import re
        parts = re.split(r'-----Original Message-----|发件人：|From:', body)
        return [p.strip() for p in parts[1:]] if len(parts) > 1 else [] 