import os
from typing import List, Dict
import mailparser

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