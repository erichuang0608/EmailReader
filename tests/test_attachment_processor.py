import os
from src.attachment_processor import AttachmentProcessor

def test_extract_text_from_pdf():
    test_pdf = 'tests/data/test.pdf'
    if not os.path.exists(test_pdf):
        return
    ap = AttachmentProcessor()
    text = ap.extract_text_from_pdf(test_pdf)
    assert isinstance(text, str) 