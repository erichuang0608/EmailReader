import os
import shutil
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from src.mail_processor import MailProcessor
from src.attachment_processor import AttachmentProcessor
from src.azure_openai_client import AzureOpenAIClient
from src.analyzer import MailAnalyzer
from src.utils import load_json

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_DIR = "uploaded_eml"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 初始化分析器
azure_client = AzureOpenAIClient('config/azure_config.json')
attachment_processor = AttachmentProcessor()
analyzer = MailAnalyzer(azure_client)

@app.get("/", response_class=HTMLResponse)
def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/analyze", response_class=HTMLResponse)
async def analyze_eml(request: Request, file: UploadFile = File(...)):
    # 保存上传文件
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    # 解析邮件
    mail_processor = MailProcessor(UPLOAD_DIR, azure_client=azure_client)
    mails = mail_processor.process_all_mails()
    if not mails:
        return templates.TemplateResponse("result.html", {"request": request, "error": "邮件解析失败"})
    mail = mails[-1]  # 只分析最新上传的
    # 解析邮件链
    try:
        mail_thread = mail_processor.parse_mail_thread(file_path)
    except Exception as e:
        return templates.TemplateResponse("result.html", {"request": request, "error": f"邮件解析失败: {e}"})
    conversation = analyzer.analyze_conversation(mail_thread)
    # 附件处理（只处理主邮件的附件）
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
            content = f"附件解析失败: {e}"
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
        },
        "timeline": conversation["timeline"],
        "dialogue": conversation["dialogue"],
        "overall_summary": conversation["overall_summary"],
        "reply_suggestions": conversation["reply_suggestions"]
    }
    return templates.TemplateResponse("result.html", {"request": request, "result": result}) 