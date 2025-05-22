# Mail Analyzer

基于Azure OpenAI的本地邮件分析工具，支持.eml邮件及常见附件（PDF/Excel/Word/图片）解析、关键信息提取、AI分析和结构化输出。

## 功能
- 批量解析本地.eml邮件及附件
- 调用Azure OpenAI生成摘要、实体、行动项、情绪、风险点
- 支持JSON/CSV导出
- 日志与API用量追踪

## 安装依赖
```bash
pip install -r requirements.txt
```

## 配置
1. 复制`config/azure_config.json`和`config/app_config.json`，填写Azure OpenAI等信息。
2. 参考`req.md`中的配置示例。

## 运行
```bash
python main.py --input /path/to/mails --output results.json
```

## 目录结构
详见`req.md`。

## 测试
```bash
pytest tests/
``` 