import os
import fitz  # PyMuPDF
import pandas as pd
import pytesseract
from PIL import Image
from docx import Document

class AttachmentProcessor:
    def __init__(self, temp_dir: str = "temp_attachments"):
        self.temp_dir = temp_dir
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

    def extract_text_from_pdf(self, file_path: str) -> str:
        text = ""
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        return text

    def extract_text_from_excel(self, file_path: str) -> str:
        df = pd.read_excel(file_path, None)  # 读取所有sheet
        text = ""
        for sheet, data in df.items():
            text += f"[Sheet: {sheet}]\n"
            text += data.to_csv(index=False)
        return text

    def extract_text_from_word(self, file_path: str) -> str:
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])

    def extract_text_from_image(self, file_path: str) -> str:
        img = Image.open(file_path)
        return pytesseract.image_to_string(img, lang='chi_sim+eng') 