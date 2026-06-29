"""应用配置"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    # PostgreSQL 数据库（Render 上必须用 Dockerfile 部署）
    raw_url = os.getenv('DATABASE_URL')
    if raw_url:
        # Render 提供的 DATABASE_URL 先用 replace 转换
        raw_url = raw_url.replace('postgres://', 'postgresql+psycopg2://')
        raw_url = raw_url.replace('postgresql://', 'postgresql+psycopg2://')
    SQLALCHEMY_DATABASE_URI = raw_url or 'sqlite:///mathlearn.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AI API 配置
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
    DEEPSEEK_MODEL = 'deepseek-chat'

    # 百度 OCR
    BAIDU_OCR_APP_ID = os.getenv('BAIDU_OCR_APP_ID', '')
    BAIDU_OCR_API_KEY = os.getenv('BAIDU_OCR_API_KEY', '')
    BAIDU_OCR_SECRET_KEY = os.getenv('BAIDU_OCR_SECRET_KEY', '')

    # 智谱AI
    ZHIPUAI_API_KEY = os.getenv('ZHIPUAI_API_KEY', '')
    ZHIPUAI_BASE_URL = 'https://open.bigmodel.cn/api/paas/v4/'
    ZHIPUAI_MODEL = 'glm-4v-flash'

    # 通义千问
    QWEN_API_KEY = os.getenv('QWEN_API_KEY', '')
    QWEN_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    QWEN_MODEL = 'qwen-vl-plus'

    # Claude API（通过中转站）
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    ANTHROPIC_BASE_URL = os.getenv('ANTHROPIC_BASE_URL', 'https://www.modelbridge.cloud/v1')
    CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-haiku-4-5')

    # SMTP 邮件
    SMTP_HOST = os.getenv('SMTP_HOST', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASS = os.getenv('SMTP_PASS', '')
