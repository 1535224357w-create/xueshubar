"""
支付宝当面付 - 直接 API 调用，不依赖 SDK
"""
import json, time, requests, base64
from urllib.parse import urlencode


def sign_rsa256(private_key_pem, data):
    """RSA-SHA256 签名"""
    from cryptography.hazmat.primitives import hashes, serialization, padding
    from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
    from cryptography.hazmat.backends import default_backend

    key = serialization.load_pem_private_key(
        private_key_pem.encode() if isinstance(private_key_pem, str) else private_key_pem,
        password=None,
        backend=default_backend()
    )
    signature = key.sign(
        data.encode('utf-8'),
        asym_padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode()


def create_qr_code(app_id, private_key, out_trade_no, total_amount, subject='学数 bar VIP', notify_url=''):
    """生成支付宝当面付二维码"""
    params = {
        'app_id': app_id,
        'method': 'alipay.trade.precreate',
        'format': 'JSON',
        'charset': 'utf-8',
        'sign_type': 'RSA2',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0',
        'biz_content': json.dumps({
            'out_trade_no': out_trade_no,
            'total_amount': f'{total_amount:.2f}',
            'subject': subject,
        }, ensure_ascii=False),
    }
    if notify_url:
        params['notify_url'] = notify_url

    # 计算签名
    sign_str = '&'.join(f'{k}={v}' for k, v in sorted(params.items()))
    params['sign'] = sign_rsa256(private_key, sign_str)

    # 发送请求
    resp = requests.post(
        'https://openapi.alipay.com/gateway.do',
        params=params,
        timeout=15
    )

    # 解析响应
    text = resp.text
    if not text:
        return None, '支付宝返回空响应'

    try:
        result = json.loads(text)
    except:
        return None, f'解析响应失败: {text[:200]}'

    response_key = 'alipay_trade_precreate_response'
    resp_data = result.get(response_key, {})

    code = resp_data.get('code', '')
    if code == '10000':
        return resp_data.get('qr_code', ''), None
    else:
        sub_msg = resp_data.get('sub_msg', resp_data.get('msg', '未知错误'))
        return None, f'支付宝错误(code={code}): {sub_msg}'
