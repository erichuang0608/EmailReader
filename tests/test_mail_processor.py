import os
from src.mail_processor import MailProcessor

def test_parse_mail():
    # 假设有一个测试邮件文件tests/data/test.eml
    test_mail_path = 'tests/data/test.eml'
    if not os.path.exists(test_mail_path):
        return  # 跳过
    processor = MailProcessor('tests/data')
    mails = processor.process_all_mails()
    assert len(mails) > 0
    mail = mails[0]
    assert 'metadata' in mail
    assert 'body' in mail
    assert 'attachments' in mail 