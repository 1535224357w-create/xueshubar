"""
分析 张宇30讲 线代和概率 PDF 目录结构
"""
import base64, os, json
from io import BytesIO
from PIL import Image
from openai import OpenAI

API_KEY = 'sk-QdrDsblWyoRrcWhdSxGc145511DyXoYcu2a19tKoduboqDex'
BASE_URL = 'https://www.modelbridge.cloud/v1'
MODEL = 'claude-haiku-4-5'
PREVIEW = r'C:\Users\xbr\mathlearn\preview_30'
OUTPUT = r'C:\Users\xbr\mathlearn\xdgl_structure.json'


def img_to_b64(path, max_w=1000):
    img = Image.open(path)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    ratio = max_w / img.width
    if ratio < 1:
        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=80, optimize=True)
    return base64.b64encode(buf.getvalue()).decode('utf-8'), 'image/jpeg'


def analyze_toc(prefix, label, num_pages):
    """分析 PDF 目录"""
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    pages = [os.path.join(PREVIEW, f'{prefix}_page_{i+1:03d}.png') for i in range(num_pages)]

    parts = [{'type': 'text', 'text': f'这是《张宇基础30讲·{label}》的封面和目录页。请提取全部章节（讲）的名称。\n\n输出JSON格式：\n{{"lectures": [{{"lecture": 1, "name": "第1讲名称", "topics": ["知识点1","知识点2"]}}]}}'}]

    for p in pages:
        if os.path.exists(p):
            b64, mime = img_to_b64(p)
            parts.append({'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{b64}'}})

    print(f'  Sending {len(parts)-1} pages for {label}...')
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=3000, timeout=60,
        messages=[{'role': 'system', 'content': '你是教材分析专家，严格按JSON格式输出。'},
                   {'role': 'user', 'content': parts}]
    )
    return resp.choices[0].message.content


results = {}

print('=== 线性代数 ===')
results['线性代数'] = analyze_toc('xd', '线性代数', 10)

print('\n=== 概率论与数理统计 ===')
results['概率论与数理统计'] = analyze_toc('gl', '概率论与数理统计', 10)

json.dump(results, open(OUTPUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'\n结果保存到: {OUTPUT}')
