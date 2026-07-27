"""
批量提取 2027张宇1000题数一 试题册中的题目 → 导入题目库
分批调用 Vision API，每批 5 页
"""
import base64, os, json, time
from io import BytesIO
from PIL import Image
from openai import OpenAI

SHEET_DIR = r'C:\Users\xbr\Desktop\高数\2027张宇1000题 数一'
SHEET = os.path.join(SHEET_DIR, '27张宇1000题数一【试题册】.pdf')
API_KEY = 'sk-QdrDsblWyoRrcWhdSxGc145511DyXoYcu2a19tKoduboqDex'
BASE_URL = 'https://www.modelbridge.cloud/v1'
MODEL = 'claude-haiku-4-5'
OUTPUT = r'C:\Users\xbr\mathlearn\1000_problems_extracted.json'
BATCH_SIZE = 5


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


def extract_batch(pdf_path, page_indices, batch_num, total_batches):
    """提取指定页面的题目"""
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    parts = [{'type': 'text', 'text': '''Extract ALL math problems from these images.
Output ONLY valid JSON: {"problems": [{"id": "题号", "type": "选择题/填空题/解答题", "content": "题目内容(含LaTeX)", "options": "选项(如有)", "answer": "答案(如有)", "knowledge_point": "知识点"}]}
Extract every problem completely.'''}]

    for i in page_indices:
        try:
            b64, mime = page_to_b64(pdf_path, i)
            kb = len(b64) * 3 / 4 / 1024
            parts.append({
                'type': 'image_url',
                'image_url': {'url': f'data:{mime};base64,{b64}'}
            })
        except Exception as e:
            print(f'    Page {i+1} error: {e}')

    print(f'  [{batch_num}/{total_batches}] Sending {len(page_indices)} pages...')
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=8000, timeout=120,
        messages=[{'role': 'user', 'content': parts}]
    )
    text = resp.choices[0].message.content
    return text


# ========== 基础篇 - 第3-43页（索引2-42）==========
foundation_pages = list(range(2, 43))  # 41 pages
batches = [foundation_pages[i:i+BATCH_SIZE] for i in range(0, len(foundation_pages), BATCH_SIZE)]
total = len(batches)

print(f'=== 提取基础篇题目（第3-43页，共{len(foundation_pages)}页，{total}批）===')

all_results = {}
for idx, batch in enumerate(batches):
    try:
        start_label = batch[0] + 1
        end_label = batch[-1] + 1
        print(f'\n--- 批 {idx+1}/{total}: 第{start_label}-{end_label}页 ---')
        result = extract_batch(SHEET, batch, idx+1, total)
        all_results[f'pages_{start_label}_{end_label}'] = result
        # Save incrementally
        with open(OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f'  Done -> saved to {OUTPUT}')
        time.sleep(1)  # Brief pause between batches
    except Exception as e:
        print(f'  Batch {idx+1} FAILED: {e}')
        all_results[f'pages_{batch[0]+1}_{batch[-1]+1}_ERROR'] = str(e)

print(f'\n=== 提取完成！共处理 {len(foundation_pages)} 页，{total} 批 ===')
print(f'结果保存到 {OUTPUT}')
