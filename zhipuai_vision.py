"""
智谱AI GLM-4V 视觉模型 - 直接识别图片中的数学题
文档：https://open.bigmodel.cn/dev/api/glm-4v
"""
import base64
from openai import OpenAI


def recognize_math_problem(image_bytes, api_key, base_url='https://open.bigmodel.cn/api/paas/v4/'):
    """
    使用智谱AI GLM-4V 视觉模型识别图片中的数学题

    :param image_bytes: 图片二进制数据
    :param api_key: 智谱AI API Key
    :param base_url: API 地址
    :return: (识别的题目文本, 原始响应文本)
    """
    if not api_key:
        raise ValueError('请先配置 ZHIPUAI_API_KEY')

    # 图片转 base64
    img_b64 = base64.b64encode(image_bytes).decode('utf-8')
    mime_type = _detect_mime(image_bytes)

    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model='glm-4v-flash',
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': '请识别这张图片中的数学题，用 LaTeX 格式输出题目本身。'
                            '注意：只输出题目，不要任何解释、不要多余文字。'
                            '如果是中文题目，保留中文。'
                },
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:{mime_type};base64,{img_b64}'
                    }
                }
            ]
        }],
        max_tokens=1000,
    )

    text = response.choices[0].message.content
    return text.strip(), text


def _detect_mime(image_bytes):
    """检测图片 MIME 类型"""
    if image_bytes[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if image_bytes[:4] == b'GIF8':
        return 'image/gif'
    if image_bytes[:4] == b'RIFF':
        return 'image/webp'
    return 'image/jpeg'  # 默认
