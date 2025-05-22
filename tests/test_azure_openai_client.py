import os
from src.azure_openai_client import AzureOpenAIClient

def test_generate_summary():
    if not os.path.exists('config/azure_config.json'):
        return
    client = AzureOpenAIClient('config/azure_config.json')
    text = "项目X第一阶段已完成，预算使用60%。"
    summary = client.generate_summary(text)
    assert isinstance(summary, str)
    assert len(summary) > 0 