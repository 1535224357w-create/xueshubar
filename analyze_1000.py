"""
分析 2027张宇1000题数一【试题册】的格式
"""
import base64, os, json
from io import BytesIO
from PIL import Image
from openai import OpenAI

SHEET_DIR = r'C:\Users\xbr\Desktop\高数\2027张宇1000题 数一'
API_KEY = 'sk-QdrDsblWyoRrcWhdSxGc145511DyXoYcu2a19tKoduboqDex'
BASE_URL = 'https://www.modelbridge.cloud/v1'
MODEL = 'claude-haiku-4-5'


def page_to_b64(pdf_path, page_num, scale=1.5):
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(pdf_path)
    bitmap = pdf[page_num].render(scale=scale)
    img = bitmap.to_pil()
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=80, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return b64, 'image/jpeg', img.size


def analyze_pages(pdf_path, page_indices, system_prompt, user_prompt):
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    parts = [{'type': 'text', 'text': user_prompt}]
    for idx in page_indices:
        try:
            b64, mime, size = page_to_b64(pdf_path, idx)
            kb = len(b64) * 3 / 4 / 1024
            print(f'  Page {idx+1}: {size[0]}x{size[1]}, ~{kb:.0f}KB')
            parts.append({'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{b64}'}})
        except Exception as e:
            print(f'  Skip page {idx+1}: {e}')
    resp = client.chat.completions.create(
        model=MODEL, max_tokens=3000,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': parts}
        ]
    )
    return resp.choices[0].message.content


SHEET = os.path.join(SHEET_DIR, '27张宇1000题数一【试题册】.pdf')
print('Analyzing format (first 8 pages)...')
result = analyze_pages(
    SHEET, list(range(8)),
    'You are a math exam analysis expert.',
    'This is the first 8 pages of 2027 Zhang Yu 1000题 Math I exam booklet. '
    'Describe the structure: how are problems organized, what is the numbering, '
    'what types of problems, what knowledge points are covered? '
    'Also tell me how many problems per page and total range.'
)
out_path = r'C:\Users\xbr\mathlearn\1000_format_analysis.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump({'result': result}, f, ensure_ascii=False, indent=2)
print('Saved to', out_path)
