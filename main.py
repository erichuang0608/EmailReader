import argparse
import os
from src.utils import load_json, save_json
from src.logger import setup_logger
from src.mail_processor import MailProcessor
from src.attachment_processor import AttachmentProcessor
from src.azure_openai_client import AzureOpenAIClient
from src.analyzer import MailAnalyzer


def main():
    parser = argparse.ArgumentParser(description="Mail Analyzer")
    parser.add_argument('--input', type=str, help='邮件目录', required=False)
    parser.add_argument('--output', type=str, help='输出JSON文件', required=False)
    args = parser.parse_args()

    app_conf = load_json('config/app_config.json')
    mail_dir = args.input or app_conf['mail_dir']
    output_json = args.output or app_conf['output_json']
    log_path = app_conf.get('log_path', 'app.log')

    logger = setup_logger(log_path)
    logger.info(f"开始处理目录: {mail_dir}")

    mail_processor = MailProcessor(mail_dir)
    attachment_processor = AttachmentProcessor()
    azure_client = AzureOpenAIClient('config/azure_config.json')
    analyzer = MailAnalyzer(azure_client)

    results = []
    mails = mail_processor.process_all_mails()
    for mail in mails:
        logger.info(f"分析邮件: {mail['mail_path']}")
        # 处理附件
        attachments = []
        for att in mail['attachments']:
            fname = att['filename']
            payload = att['payload']
            if not fname or not payload:
                continue
            fpath = os.path.join(attachment_processor.temp_dir, fname)
            with open(fpath, 'wb') as f:
                if isinstance(payload, str):
                    f.write(payload.encode('utf-8'))
                else:
                    f.write(payload)
            ext = fname.split('.')[-1].lower()
            content = ""
            try:
                if ext == 'pdf':
                    content = attachment_processor.extract_text_from_pdf(fpath)
                elif ext in ['xls', 'xlsx']:
                    content = attachment_processor.extract_text_from_excel(fpath)
                elif ext in ['doc', 'docx']:
                    content = attachment_processor.extract_text_from_word(fpath)
                elif ext in ['png', 'jpg', 'jpeg', 'bmp']:
                    content = attachment_processor.extract_text_from_image(fpath)
            except Exception as e:
                logger.warning(f"附件解析失败: {fname} {e}")
            att_result = {
                "filename": fname,
                "type": ext,
                "content": content,
                "summary": azure_client.generate_summary(content) if content else ""
            }
            attachments.append(att_result)
        # 邮件正文分析
        analysis = analyzer.analyze_mail(mail)
        result = {
            "mail_path": mail['mail_path'],
            "metadata": mail['metadata'],
            "body": {
                "raw_text": mail['body'],
                "summary": analysis['summary']
            },
            "attachments": attachments,
            "analysis": {
                "entities": analysis['entities'],
                "action_items": analysis['action_items'],
                "sentiment": analysis['sentiment'],
                "risk_points": analysis['risk_points']
            }
        }
        results.append(result)
    save_json(results, output_json)
    logger.info(f"处理完成，结果已保存到: {output_json}")

if __name__ == '__main__':
    main() 