"""
分析 张宇基础30讲（高数）PDF 的目录结构
"""
import base64, os, json
from io import BytesIO
from PIL import Image
from openai import OpenAI

PDF_DIR = r'C:\Users\xbr\Desktop\高数\preview'
API_KEY = 'sk-QdrDsblWyoRrcWhdSxGc145511DyXoYcu2a19tKoduboqDex'
BASE_URL = 'https://www.modelbridge.cloud/v1'
MODEL = 'claude-haiku-4-5'
OUTPUT = r'C:\Users\xbr\mathlearn\30lectures_structure.json'


def compress(img_path, max_w=800):
    """压缩图片并base64"""
    img = Image.open(img_path)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    ratio = max_w / img.width
    if ratio < 1:
        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=80, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return b64, 'image/jpeg'


def analyze_pages(page_nums, system_prompt, user_prompt):
    """发送页面给 Claude Vision"""
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    parts = [{'type': 'text', 'text': user_prompt}]

    for pn in page_nums:
        path = os.path.join(PDF_DIR, f'page_{pn:04d}.png')
        if not os.path.exists(path):
            print(f'  skip page {pn}')
            continue
        b64, mime = compress(path)
        parts.append({'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{b64}'}})

    resp = client.chat.completions.create(
        model=MODEL, max_tokens=3000,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': parts}
        ]
    )
    return resp.choices[0].message.content


# Step 1: 分析目录（前10页）
print('=== 分析目录结构 ===')
toc = analyze_pages(
    list(range(1, 11)),
    '你是教材分析专家。严格按JSON格式输出。',
    '''这是《张宇基础30讲·高等数学》的封面和目录页。
    请分析全部章节（讲）的名称和对应的知识点范围。

    输出JSON格式：
    {
      "book_name": "书名",
      "total_lectures": 30,
      "lectures": [
        {
          "lecture": 1,
          "name": "第1讲名称",
          "topics": ["核心知识点1", "核心知识点2"]
        }
      ]
    }'''
)
print(toc[:2000])

# Step 2: 看几页典型例题+习题页面
print('\n=== 分析典型内容页 ===')
sample_pages = [21, 51, 81, 111, 141]
content = analyze_pages(
    sample_pages,
    '你是数学教材分析专家。',
    '''这些是《张宇基础30讲·高等数学》的一些内容页。
    请识别：
    1. 每页包含什么类型的内容（知识点讲解/例题/习题/答案）
    2. 每页的题号范围和对应的知识点
    3. 习题的格式（选择题/填空题/解答题？）'''
)
print(content[:2000])

# 保存
json.dump({'toc_analysis': toc, 'content_analysis': content,
           'total_pages': 586, 'sample_pages': sample_pages},
          open(OUTPUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'\n结果保存在: {OUTPUT}')
