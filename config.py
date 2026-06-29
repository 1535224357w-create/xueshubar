"""应用配置"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    raw_db_url = os.getenv('DATABASE_URL', '')
    if raw_db_url and raw_db_url.startswith('postgresql://'):
        raw_db_url = raw_db_url.replace('postgresql://', 'postgresql+pg8000://', 1)
    SQLALCHEMY_DATABASE_URI = raw_db_url or 'sqlite:///mathlearn.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AI API 配置（用于分析错题，目前使用 DeepSeek）
    # DeepSeek API: https://platform.deepseek.com/
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
    DEEPSEEK_MODEL = 'deepseek-chat'

    # 百度 OCR 配置（用于拍照识别数学题）
    # 从 https://console.bce.baidu.com/ai/#/ai/ocr/overview/index 获取
    BAIDU_OCR_APP_ID = os.getenv('BAIDU_OCR_APP_ID', '')
    BAIDU_OCR_API_KEY = os.getenv('BAIDU_OCR_API_KEY', '')
    BAIDU_OCR_SECRET_KEY = os.getenv('BAIDU_OCR_SECRET_KEY', '')

    # 智谱AI 视觉模型配置（拍照识别数学题，替代OCR）
    # 从 https://open.bigmodel.cn/ 获取
    ZHIPUAI_API_KEY = os.getenv('ZHIPUAI_API_KEY', '')
    ZHIPUAI_BASE_URL = 'https://open.bigmodel.cn/api/paas/v4/'
    ZHIPUAI_MODEL = 'glm-4v-flash'

    # 通义千问 Qwen-VL 视觉模型（阿里云 DashScope）
    # 从 https://dashscope.aliyun.com/ 获取
    QWEN_API_KEY = os.getenv('QWEN_API_KEY', '')
    QWEN_BASE_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    QWEN_MODEL = 'qwen-vl-plus'

    # Claude API（通过中转站，OpenAI 兼容格式）
    # 中转站地址和模型名根据实际配置
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    ANTHROPIC_BASE_URL = os.getenv('ANTHROPIC_BASE_URL', 'https://www.modelbridge.cloud/v1')
    CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-haiku-4-5')

    # PayJS 支付配置
    PAYJS_MCHID = os.getenv('PAYJS_MCHID', '')
    PAYJS_KEY = os.getenv('PAYJS_KEY', '')
    PAYJS_NOTIFY_URL = os.getenv('PAYJS_NOTIFY_URL', '')

    # SMTP 邮件配置（用于意见反馈）
    SMTP_HOST = os.getenv('SMTP_HOST', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASS = os.getenv('SMTP_PASS', '')
