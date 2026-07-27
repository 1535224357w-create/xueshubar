"""
提取 2027张宇1000题 全部剩余章节的题目并导入
"""
import base64, os, json, time, sys
from io import BytesIO
from PIL import Image
from openai import OpenAI

SHEET = r'C:\Users\xbr\Desktop\高数\2027张宇1000题 数一\27张宇1000题数一【试题册】.pdf'
API_KEY = 'sk-QdrDsblWyoRrcWhdSxGc145511DyXoYcu2a19tKoduboqDex'
BASE_URL = 'https://www.modelbridge.cloud/v1'
MODEL = 'claude-haiku-4-5'
OUTPUT = r'C:\Users\xbr\mathlearn\1000_problems_extracted.json'
BATCH_SIZE = 4


def page_to_b64(pdf_path, page_num, scale=1.2):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(pdf_path)
    bitmap = pdf[page_num].render(scale=scale)
    img = bitmap.to_pil()
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=75, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return b64, 'image/jpeg'


def extract_batch(pdf_path, page_indices, label):
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    parts = [{'type': 'text', 'text': '''Extract ALL math exam problems from these images.
Output ONLY valid JSON: {"problems": [{"id": "...", "type": "选择题/填空题/解答题", "content": "...(include LaTeX)", "options": "...(if multiple choice)", "answer": "...(if visible)", "knowledge_point": "..."}]}
Extract EVERY problem completely - do not skip any.'''}]

    for i in page_indices:
        try:
            b64, mime = page_to_b64(pdf_path, i)
            parts.append({'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{b64}'}})
        except Exception as e:
            print(f'  Error page {i+1}: {e}')

    print(f'  [{label}] Sending {len(page_indices)} pages...')
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=8000, timeout=120,
        messages=[{'role': 'user', 'content': parts}]
    )
    return resp.choices[0].message.content


def process_section(name, page_start, page_end):
    """处理一个章节"""
    pages = list(range(page_start, min(page_end + 1, 200)))
    batches = [pages[i:i+BATCH_SIZE] for i in range(0, len(pages), BATCH_SIZE)]

    print(f'\n=== {name}（第{page_start+1}-{page_end+1}页，{len(pages)}页，{len(batches)}批）===')

    # 加载已有的结果
    all_data = {}
    if os.path.exists(OUTPUT):
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            all_data = json.load(f)

    for idx, batch in enumerate(batches):
        key = f'{name}_{batch[0]+1}_{batch[-1]+1}'
        if key in all_data and len(all_data[key]) > 500:
            print(f'  [{idx+1}/{len(batches)}] {key}: 已存在，跳过')
            continue

        try:
            result = extract_batch(SHEET, batch, f'{idx+1}/{len(batches)}')
            all_data[key] = result
            with open(OUTPUT, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            print(f'  -> 已保存 ({len(result)} chars)')
            time.sleep(1)
        except Exception as e:
            print(f'  FAILED: {e}')
            all_data[f'{key}_ERROR'] = str(e)

    return len(batches)


# 强化篇：第45-73页（索引44-72）
process_section('强化篇', 44, 72)

# 综合篇：第79-170页（索引78-169）
process_section('综合篇', 78, 169)

print('\n=== 全部提取完成！===')
