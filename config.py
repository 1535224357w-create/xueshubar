"""应用配置"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 数据库连接
    @staticmethod
    def _get_db_url():
        import sys
        raw = os.environ.get('DATABASE_URL', '').strip()
        print(f'[DB] DATABASE_URL raw: {repr(raw)}', file=sys.stderr)
        print(f'[DB] DATABASE_URL len: {len(raw)}', file=sys.stderr)
        if not raw:
            print('[DB] 未设置DATABASE_URL，使用SQLite', file=sys.stderr)
            return 'sqlite:///mathlearn.db'
        if 'ostgresql' in raw and 'postgresql' not in raw:
            print(f'[DB] 警告：URL缺少p！原始值={repr(raw[:30])}', file=sys.stderr)
            return 'sqlite:///mathlearn.db'
        from urllib.parse import urlparse
        try:
            p = urlparse(raw)
            if p.scheme and p.netloc:
                print(f'[DB] 使用PostgreSQL: {p.scheme}', file=sys.stderr)
                return raw
        except: pass
        print('[DB] URL无效，回退SQLite', file=sys.stderr)
        return 'sqlite:///mathlearn.db'

    SQLALCHEMY_DATABASE_URI = _get_db_url()

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
