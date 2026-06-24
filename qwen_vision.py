"""
通义千问 Qwen-VL 视觉模型 - 识别数学题图片
文档：https://help.aliyun.com/zh/model-studio/
"""
import base64
from openai import OpenAI


def recognize_math_problem(image_bytes, api_key,
                            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
                            model='qwen-vl-plus'):
    """
    使用通义千问 Qwen-VL 识别图片中的数学题

    :param image_bytes: 图片二进制数据
    :param api_key: DashScope API Key
    :param base_url: API 地址
    :param model: 模型名 (qwen-vl-plus 或 qwen-vl-max)
    :return: (识别的题目文本, 原始响应文本)
    """
    if not api_key:
        raise ValueError('请先配置 QWEN_API_KEY')

    img_b64 = base64.b64encode(image_bytes).decode('utf-8')
    mime = _detect_mime(image_bytes)

    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': '识别这张图片中的数学题。规则：'
                            '1. 不要用 markdown 代码块（不要用 ```）'
                            '2. 用 $$...$$ 包裹 LaTeX 公式'
                            '3. 只输出题目本身，不要任何解释'
                },
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:{mime};base64,{img_b64}'
                    }
                }
            ]
        }],
        max_tokens=1000,
    )

    text = response.choices[0].message.content.strip()

    # 去掉 markdown 代码块（如 ```latex ... ```）
    import re
    text = re.sub(r'^```\w*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    text = text.strip()

    # 去掉 \[ \] 或 \( \) 包裹
    text = text.replace('\\[', '').replace('\\]', '')
    text = text.replace('\\(', '').replace('\\)', '')

    # 确保有 $$ 包裹（兼容已有 $ 但可能没有 $$ 的情况）
    if text.startswith('$') and not text.startswith('$$'):
        text = '$' + text + '$'  # 单个$保持
    elif not text.startswith('$'):
        text = '$$' + text + '$$'

    return text, response.choices[0].message.content


def _detect_mime(image_bytes):
    if image_bytes[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    return 'image/jpeg'
