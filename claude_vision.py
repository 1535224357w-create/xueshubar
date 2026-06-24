"""
Claude 视觉模型（通过 OpenAI 兼容格式中转站调用）
"""
import base64
from openai import OpenAI


def recognize_math_problem(image_bytes, api_key, model='claude-haiku-4-5',
                            base_url='https://www.modelbridge.cloud/v1'):
    """
    使用 Claude 视觉模型识别图片中的数学题（通过中转站）

    :param image_bytes: 图片二进制数据
    :param api_key: 中转站 API Key
    :param model: 模型名
    :param base_url: 中转站 API 地址
    :return: (识别出的题目文本, 原始响应)
    """
    if not api_key:
        raise ValueError('请先配置 API Key')

    mime = _detect_mime(image_bytes)
    img_b64 = base64.b64encode(image_bytes).decode('utf-8')

    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        max_tokens=800,
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': '这张图片是一道数学题。请识别并用中文描述出来。'
                },
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:{mime};base64,{img_b64}'
                    }
                }
            ]
        }]
    )

    text = response.choices[0].message.content.strip()
    return text, response


def _detect_mime(image_bytes):
    if image_bytes[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    return 'image/jpeg'
