**目标**：开发一个基于Azure OpenAI的邮件分析工具，能够处理本地目录中的邮件文件（.eml格式）及其附件（PDF、Excel、Word、图片），提取关键信息、生成摘要并进行深度分析。

**功能需求**：
1. **邮件处理模块**：
   - 遍历指定目录中的所有.eml文件
   - 解析邮件元数据（发件人、收件人、主题、时间戳）
   - 提取邮件正文（处理HTML和纯文本格式）
   - 保存邮件结构（区分原始内容和回复历史）

2. **附件处理模块**：
   - 提取并分类附件（PDF/Excel/Word/图片）
   - 解析附件内容：
     - PDF：提取文本内容（PyMuPDF）
     - Excel：提取表格数据（pandas）
     - Word：提取文本内容（python-docx）
     - 图片：OCR识别文本（pytesseract）
   - 对大文件进行分块处理（如按PDF页数、Excel工作表）

3. **Azure OpenAI集成**：
   - 基于Azure OpenAI的GPT-4或GPT-3.5 Turbo模型进行分析
   - 支持配置文件管理Azure资源（端点、API密钥、部署名称）
   - 实现：
     - 文本摘要生成
     - 实体提取（人物、组织、日期、事件）
     - 行动项识别（负责人、任务、截止日期）
     - 情绪分析
     - 风险点检测
   - 批量处理优化和API速率限制管理

4. **输出与存储**：
   - 生成结构化JSON报告
   - 支持CSV/Excel导出关键分析结果
   - 保存处理日志和API调用记录

**技术约束**：
- 语言：Python 3.9+
- 邮件解析：`mail-parser`、`email`库
- Azure服务：
  - Azure OpenAI Service（必需）
  - Azure Form Recognizer（可选，用于复杂文档解析）
  - Azure Cognitive Search（可选，用于向量搜索）
- 异步处理：`asyncio`和`concurrent.futures`
- 配置管理：`python-dotenv`、JSON配置文件
- 错误处理：完善的异常捕获和重试机制（指数退避）

**代码结构要求**：
```
mail-analyzer/
├── main.py                    # 程序入口
├── config/                    # 配置文件
│   ├── azure_config.json      # Azure服务配置
│   └── app_config.json        # 应用配置
├── src/
│   ├── mail_processor.py      # 邮件解析器
│   ├── attachment_processor.py # 附件处理器
│   ├── azure_openai_client.py # Azure OpenAI客户端
│   ├── analyzer.py            # 内容分析器
│   ├── logger.py              # 日志记录器
│   └── utils.py               # 工具函数
├── tests/                     # 单元测试
├── requirements.txt           # 依赖列表
└── README.md                  # 使用说明
```

**核心类设计**：
```python
# src/mail_processor.py
class MailProcessor:
    def __init__(self, mail_dir: str):
        """初始化邮件处理器"""
        
    def process_all_mails(self) -> List[Dict]:
        """处理目录下所有邮件"""
        
    def parse_mail(self, file_path: str) -> Dict:
        """解析单个邮件文件"""

# src/attachment_processor.py
class AttachmentProcessor:
    def __init__(self, temp_dir: str = "temp_attachments"):
        """初始化附件处理器"""
        
    def extract_text_from_pdf(self, file_path: str) -> str:
        """从PDF提取文本"""
        
    def extract_text_from_excel(self, file_path: str) -> str:
        """从Excel提取文本"""
        
    def extract_text_from_image(self, file_path: str) -> str:
        """从图片OCR文本"""

# src/azure_openai_client.py
class AzureOpenAIClient:
    def __init__(self, config_path: str):
        """初始化Azure OpenAI客户端"""
        
    def generate_summary(self, text: str, max_tokens: int = 300) -> str:
        """生成文本摘要"""
        
    def extract_entities(self, text: str) -> Dict:
        """提取实体信息"""
        
    def analyze_action_items(self, text: str) -> List[Dict]:
        """分析行动项"""
        
    def detect_sentiment(self, text: str) -> str:
        """检测情绪"""
        
    def track_api_usage(self, response) -> None:
        """跟踪API使用情况和成本"""

# src/analyzer.py
class MailAnalyzer:
    def __init__(self, azure_client: AzureOpenAIClient):
        """初始化邮件分析器"""
        
    def analyze_mail(self, mail_data: Dict) -> Dict:
        """分析单个邮件"""
        
    def analyze_conversation(self, mail_thread: List[Dict]) -> Dict:
        """分析邮件对话链"""
```

**Azure配置文件示例**：
```json
// config/azure_config.json
{
  "azure_openai": {
    "endpoint": "https://your-resource-name.openai.azure.com/",
    "api_key": "your-api-key",
    "api_version": "2023-05-15",
    "deployment_name": "gpt-35-turbo"
  },
  "rate_limit": {
    "rpm": 300,  // 请求/分钟
    "max_retries": 5
  },
  "cost_tracking": {
    "enabled": true,
    "log_path": "azure_api_usage.log"
  }
}
```

**输出格式**：
```json
{
  "mail_path": "/path/to/mail.eml",
  "metadata": {
    "subject": "项目X进度更新",
    "from": "alice@example.com",
    "to": ["bob@example.com", "charlie@example.com"],
    "date": "2023-10-15T09:30:00Z"
  },
  "body": {
    "raw_text": "嗨团队，项目X第一阶段已完成...",
    "summary": "Alice报告项目X第一阶段完成，预算使用60%，下周提交初步报告。需要安排演示会议。"
  },
  "attachments": [
    {
      "filename": "progress_report.pdf",
      "type": "pdf",
      "content": "项目X进度报告\n1. 引言\n项目X于2023年9月启动...",
      "summary": "报告详细说明了项目X的技术实现和里程碑完成情况"
    }
  ],
  "analysis": {
    "entities": {
      "persons": ["Alice", "Bob", "Charlie"],
      "organizations": ["Example Corp"],
      "dates": ["2023-10-15", "2023-10-20"],
      "locations": ["上海"]
    },
    "action_items": [
      {
        "description": "提交初步报告",
        "assignee": "Alice",
        "due_date": "2023-10-20",
        "priority": "高"
      },
      {
        "description": "安排演示会议",
        "assignee": "Bob",
        "due_date": "",
        "priority": "中"
      }
    ],
    "sentiment": "积极",
    "risk_points": ["预算超支风险", "资源不足"]
  },
  "azure_usage": {
    "prompt_tokens": 1254,
    "completion_tokens": 328,
    "total_cost": 0.0246,
    "request_time": "2023-10-15T12:45:10Z"
  }
}
```

**测试要求**：
- 编写单元测试验证邮件解析、附件处理和Azure OpenAI集成
- 提供示例邮件和附件用于测试
- 测试API错误处理和重试机制

**使用说明**：
1. 配置Azure OpenAI服务并获取API密钥
2. 修改`config/azure_config.json`填入配置信息
3. 安装依赖：`pip install -r requirements.txt`
4. 运行程序：`python main.py --input /path/to/mails --output results.json`


### **使用Cursor的建议**
1. 先让Cursor生成基础框架，再逐步细化各个模块
2. 重点关注`azure_openai_client.py`和`analyzer.py`的实现
3. 对于复杂功能（如邮件对话分析），可以分多次生成
4. 生成代码后，使用Cursor的重构功能优化结构
5. 遇到依赖安装问题时，添加`requirements.txt`文件

这个prompt提供了详细的功能描述、代码结构和技术要求，Cursor应该能够生成一个完整的邮件分析工具基础版本。你可以根据实际需求调整细节，或在生成代码后提出进一步的修改要求。


增加一个需求：
创建一个Web页面，让用户上传.eml邮件，然后将分析结果显示页面上。

增加一个需求，
请增强页面显示，将输出的结果展示为用户可以谈懂的内容，而不是JSON结构

有分析完成邮件的输出中，增加以下需求：
1. 如果邮件中包含历史邮件，请按时间轴的顺序汇总每一封邮件。
2. 每封邮件解析中包含：发件人，收件人，抄送人，邮件主题，以及汇总后的邮件内容。
3. 解析邮件中附件，如PDF或图片中的内容，理解并汇总附件中的内容。
4. 以对话的形式，显示整个邮件链路中的各个邮件的内容。
5. 汇总邮件中的总体内容，并将内容展示出来，逻列中邮件要的的问题和关键数据，如invocie number, 之前的主要的数据。
6. 要保留情续分析部分
7. 最后，增加一个部分，给出回复这封邮件的建议。如果你是邮件接收人，如何回复。

邮件链时间轴分析：
自动识别邮件中的历史回复（通过In-Reply-To头或文本模式）
按时间顺序（最早到最新）重建邮件对话链
生成时间轴视图，显示每封邮件的发送时间和参与者
邮件元数据解析增强：
完整提取发件人、收件人、抄送人的姓名和邮箱地址
保留邮件主题和原始时间戳
区分主邮件和引用的历史邮件
附件内容深度分析：
解析 PDF 中的表格、图表和文本段落
从图片中 OCR 文本并识别关键信息（如发票号码、金额）
对 Excel 文件进行数据摘要（统计关键指标、识别趋势）
生成附件内容的结构化摘要（如 "报告显示 Q3 收入增长 12%"）
对话式邮件链展示：
以对话格式呈现邮件往来，清晰显示发言顺序
标记每封邮件的关键动作和决策点
支持缩进显示嵌套回复
关键信息提取与汇总：
自动识别并提取关键数据：
发票号、订单号、金额
日期、截止日期、时间点
项目名称、产品编号
生成结构化的 "问题清单" 和 "决策摘要"
计算关键数值指标（如金额总计、时间间隔）
情绪分析增强：
分析每封邮件的情绪倾向（积极 / 消极 / 中性）
检测情绪变化趋势（如对话是否从紧张转为积极）
识别关键情绪转折点及其触发因素
智能回复建议：
基于邮件内容生成 3 种不同风格的回复建议（正式 / 中性 / 友好）
针对关键问题提供具体回应策略
自动填充需要确认的信息（如日期、数据）
标记需要跟进的行动项和责任分配