"""
使用 Claude Vision 分析 660 题 PDF 页面，提取知识点结构
"""
import base64, os, json, sys
from io import BytesIO
from PIL import Image
from openai import OpenAI

# 配置
PDF_DIR = r'C:\Users\xbr\mathlearn\pdf_pages'
API_KEY = 'sk-QdrDsblWyoRrcWhdSxGc145511DyXoYcu2a19tKoduboqDex'
BASE_URL = 'https://www.modelbridge.cloud/v1'
MODEL = 'claude-haiku-4-5'
OUTPUT = r'C:\Users\xbr\mathlearn\pdf_knowledge_structure.json'


def compress_image(img_path, max_size=(1200, 1200), quality=80):
    """压缩图片到合适大小"""
    img = Image.open(img_path)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img.thumbnail(max_size, Image.LANCZOS)
    out = BytesIO()
    img.save(out, format='JPEG', quality=quality, optimize=True)
    b64 = base64.b64encode(out.getvalue()).decode('utf-8')
    return b64, 'image/jpeg', img.size


def analyze_pages(page_nums, system_prompt, user_prompt):
    """发送多张页面图片给 Claude Vision 分析"""
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    content_parts = [{'type': 'text', 'text': user_prompt}]

    for pn in page_nums:
        img_path = os.path.join(PDF_DIR, f'page_{pn:02d}.png')
        if not os.path.exists(img_path):
            print(f'  ⚠ 第{pn}页不存在，跳过')
            continue
        b64, mime, size = compress_image(img_path)
        b64_size_kb = len(b64) / 1024
        print(f'  第{pn}页: {size[0]}x{size[1]}, base64={b64_size_kb:.0f}KB')
        content_parts.append({
            'type': 'image_url',
            'image_url': {'url': f'data:{mime};base64,{b64}'}
        })

    print(f'  共 {len(content_parts)-1} 张图片，发送请求...')

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=2000,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': content_parts}
        ]
    )

    return response.choices[0].message.content


# ============ Step 1: 先看第1页标题 ============
print('=== Step 1: 分析封面 ===')
result1 = analyze_pages(
    [1],
    '你是数学教材分析专家。',
    '这是考研数学660题（数一）的封面页。请告诉我这本书包含哪些部分（高等数学、线性代数、概率论与数理统计），以及任何关于章节结构的信息。'
)
print(f'结果:\n{result1}\n')

# ============ Step 2: 分析高等数学部分 ============
print('=== Step 2: 分析高等数学题目结构 ===')
result2 = analyze_pages(
    [2, 3, 4, 5, 6, 7, 8, 9],
    '''你是数学教材分析专家。请仔细分析这些图片并提取知识点结构。

要求输出格式（严格按此JSON格式）：
{
  "category": "高等数学",
  "chapters": [
    {
      "name": "章节名",
      "description": "简短描述",
      "problem_count": 数量,
      "sub_topics": ["子知识点1", "子知识点2"]
    }
  ]
}

注意：
- 仔细看每道题所属的章节/知识点
- 按题目序号推断章节划分
- 尽可能精确到每个子知识点''',
    '这是2025考研数学660题（数一）的高等数学部分题目页面。请分析每页中出现的题目所属的知识点/章节，提取完整的章节结构和知识点体系。注意看题目前的章节标题和题号范围。'
)
print(f'结果:\n{result2}\n')

# ============ Step 3: 分析线代和概率部分 ============
print('=== Step 3: 分析线性代数+概率论部分 ===')
result3 = analyze_pages(
    [10, 11, 12, 13, 14, 15, 16],
    '''你是数学教材分析专家。请仔细分析这些图片并提取知识点结构。

要求输出格式（严格按此JSON格式）：
{
  "category": "线性代数 或 概率论与数理统计",
  "chapters": [
    {
      "name": "章节名",
      "description": "简短描述",
      "problem_count": 数量,
      "sub_topics": ["子知识点1", "子知识点2"]
    }
  ]
}

注意：
- 仔细看每道题所属的章节/知识点
- 按题目序号推断章节划分
- 尽可能精确到每个子知识点''',
    '这是2025考研数学660题（数一）的线性代数与概率论部分题目页面。请分析每页中出现的题目所属的知识点/章节，提取完整的章节结构和知识点体系。注意看题目前的章节标题和题号范围。'
)
print(f'结果:\n{result3}\n')

# ============ Step 4: 汇总保存 ============
print('=== 汇总保存 ===')
print(f'\n完整分析结果已保存到: {OUTPUT}')

import datetime
summary = {
    'source': '25年660数一.pdf',
    'analysis_date': datetime.datetime.now().isoformat(),
    'pages_analyzed': list(range(1, 17)),
    'cover_analysis': result1,
    'gaoshu_analysis': result2,
    'linear_prob_analysis': result3,
}

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print('完成!')
