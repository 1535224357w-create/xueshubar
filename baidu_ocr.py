"""
百度 OCR 文字识别 — 支持通用和公式专用两种方案

方案：
- general_basic: 通用文字识别（适合中英文混合题目）
- formula: 公式专用识别（适合纯数学公式）

文档：https://ai.baidu.com/ai-doc/OCR/Ek3h7xypm
"""
import base64
import requests
import time

TOKEN_URL = 'https://aip.baidubce.com/oauth/2.0/token'
# 通用文字识别（含位置信息版），比公式识别更适合整页题目
GENERAL_URL = 'https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic'
# 公式专用识别
FORMULA_URL = 'https://aip.baidubce.com/rest/2.0/ocr/v1/formula'

_token_cache = {'token': None, 'expires_at': 0}

def _get_access_token(api_key, secret_key):
    """获取 access_token（缓存）"""
    now = time.time()
    if _token_cache['token'] and now < _token_cache['expires_at']:
        return _token_cache['token']
    params = {
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': secret_key,
    }
    resp = requests.post(TOKEN_URL, params=params, timeout=10)
    data = resp.json()
    if 'access_token' not in data:
        err_msg = data.get('error_description', str(data))
        raise Exception(f"获取 token 失败：{err_msg}")
    _token_cache['token'] = data['access_token']
    _token_cache['expires_at'] = now + data.get('expires_in', 2592000) - 300
    return data['access_token']


def recognize_text(image_bytes, api_key, secret_key, endpoint='general_basic', preprocess=True):
    """
    百度 OCR 识别 — 支持通用文字和公式专用两种方案

    :param image_bytes: 图片二进制数据
    :param api_key: Baidu API Key
    :param secret_key: Baidu Secret Key
    :param endpoint: 'general_basic'（默认）| 'formula'
    :param preprocess: 是否自动进行图像预处理
    :return: (识别文本, 原始响应 JSON, 使用的端点)
    """
    # 预处理
    if preprocess:
        try:
            from image_utils import preprocess_for_baidu
            image_bytes = preprocess_for_baidu(image_bytes)
        except ImportError:
            pass  # 无法预处理就用原始图片

    access_token = _get_access_token(api_key, secret_key)
    img_b64 = base64.b64encode(image_bytes).decode('utf-8')

    if endpoint == 'formula':
        url = FORMULA_URL
    else:
        url = GENERAL_URL

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'image': img_b64}

    resp = requests.post(
        f'{url}?access_token={access_token}',
        headers=headers,
        data=data,
        timeout=30
    )
    result = resp.json()

    if 'error_code' in result:
        raise Exception(
            f"百度 OCR 错误 (代码{result['error_code']}): "
            f"{result.get('error_msg', '未知')} "
            f"[endpoint={endpoint}]"
        )

    if endpoint == 'formula':
        # 公式端点返回结果格式不同：forms_result
        formulas = result.get('forms_result', [])
        if not formulas:
            return '', result, endpoint
        text = '\n'.join([f.get('words', '') for f in formulas])
        return text, result, endpoint

    # 通用文字端点
    words = result.get('words_result', [])
    if not words:
        return '', result, endpoint
    text = '\n'.join([w.get('words', '') for w in words])
    return text, result, endpoint


def recognize_general(image_bytes, api_key, secret_key, preprocess=True):
    """通用文字识别（中英文混合）"""
    return recognize_text(image_bytes, api_key, secret_key, 'general_basic', preprocess)


def recognize_formula(image_bytes, api_key, secret_key, preprocess=True):
    """公式专用识别（纯数学公式）"""
    return recognize_text(image_bytes, api_key, secret_key, 'formula', preprocess)
