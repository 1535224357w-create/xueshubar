"""
OCR ????? ? ?????? OCR ??????????

???????????
1. baidu_general ? ?????????????????
2. baidu_formula ? ???????????????
3. qwen_vl ? ???? Qwen-VL ???????????
4. zhipuai_glm4v ? ??AI GLM-4V ????
5. pix2tex ? ?? LaTeX-OCR???????????

?????
- ???????????
- ?????????????
- ????????????
"""
import re
import logging

logger = logging.getLogger(__name__)

# --- ??????? ---
_HAS_BAIDU = False
_HAS_QWEN = False
_HAS_ZHIPU = False
_HAS_PIX2TEX = False

try:
    from baidu_ocr import recognize_general, recognize_formula
    _HAS_BAIDU = True
except ImportError:
    pass

try:
    from qwen_vision import recognize_math_problem as qwen_recognize
    _HAS_QWEN = True
except ImportError:
    pass

try:
    from zhipuai_vision import recognize_math_problem as zhipu_recognize
    _HAS_ZHIPU = True
except ImportError:
    pass

# pix2tex (LaTeX-OCR)
try:
    from pix2tex.cli import LatexOCR
    _PIX2TEX_MODEL = None
    _HAS_PIX2TEX = True
except ImportError:
    import shutil
    if shutil.which('pix2tex_cli') or shutil.which('latexocr'):
        _HAS_PIX2TEX = True


class OCRResult:
    """?? OCR ?????"""
    def __init__(self, text='', engine='unknown', raw=None, score=0.0):
        self.text = text.strip()
        self.engine = engine
        self.raw = raw or {}
        self.score = score

    def __repr__(self):
        return f"OCRResult(engine={self.engine}, score={self.score:.2f}, text={self.text[:50]}...)"

    @property
    def is_valid(self):
        return bool(self.text) and self.score > 0


def score_ocr_text(text):
    """? OCR ?????????? (0~100)"""
    if not text or not text.strip():
        return 0.0
    score = 0.0
    text = text.strip()
    cn_chars = len(re.findall(r'[一-鿿]', text))
    if cn_chars > 3:
        score += 20
    elif cn_chars > 0:
        score += 10
    math_symbols = ['lim', 'sin', 'cos', 'tan', 'log', 'sqrt']
    has_math = sum(1 for s in math_symbols if s in text)
    if has_math > 0:
        score += min(has_math * 5, 15)
    if len(re.findall(r'[\\\^_{}]', text)) > 2:
        score += 10
    length = len(text)
    if 10 <= length <= 500:
        score += 15
    elif length > 1000:
        score -= 5
    math_keywords = ['?', '??', '??', '?', '??', '?', '??', '??', '??', '??', '??']
    kw_count = sum(1 for kw in math_keywords if kw in text)
    score += min(kw_count * 5, 10)
    num_ops = len(re.findall(r'[\d+\-*/=()<>]', text))
    if num_ops > 3:
        score += 10
    elif num_ops > 0:
        score += 5
    return max(score, 0.0)


def _run_pix2tex(image_bytes):
    """?? pix2tex (LaTeX-OCR)"""
    try:
        import subprocess, tempfile, os
        from PIL import Image
        try:
            from image_utils import preprocess_for_pix2tex
            image_bytes = preprocess_for_pix2tex(image_bytes)
        except ImportError:
            pass
        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        tmp.write(image_bytes)
        tmp.close()
        try:
            global _PIX2TEX_MODEL
            if _PIX2TEX_MODEL is None:
                _PIX2TEX_MODEL = LatexOCR()
            img = Image.open(tmp.name)
            result = _PIX2TEX_MODEL(img)
            return result.strip()
        except Exception:
            result = subprocess.run(['pix2tex_cli', tmp.name], capture_output=True, text=True, timeout=30)
            return result.stdout.strip()
        finally:
            try: os.unlink(tmp.name)
            except Exception: pass
    except Exception as e:
        logger.warning(f"pix2tex ????: {e}")
        return ''


def get_available_engines():
    """?????? OCR ??"""
    engines = []
    if _HAS_BAIDU:
        engines.append('baidu_general')
        engines.append('baidu_formula')
    if _HAS_QWEN:
        engines.append('qwen_vl')
    if _HAS_ZHIPU:
        engines.append('zhipuai_glm4v')
    if _HAS_PIX2TEX:
        engines.append('pix2tex')
    return engines


def ocr_pipeline(image_bytes, api_keys=None, preferred_engine=None):
    """??? OCR ?? ? ?????????????"""
    results = []
    if _HAS_BAIDU and api_keys:
        baidu_ak = api_keys.get('baidu_api_key', '')
        baidu_sk = api_keys.get('baidu_secret_key', '')
        if baidu_ak and baidu_sk:
            try:
                text, raw, ep = recognize_general(image_bytes, baidu_ak, baidu_sk)
                results.append(OCRResult(text, 'baidu_general', raw, score_ocr_text(text)))
            except Exception as e:
                logger.warning(f"????OCR??: {e}")
            try:
                text, raw, ep = recognize_formula(image_bytes, baidu_ak, baidu_sk)
                results.append(OCRResult(text, 'baidu_formula', raw, score_ocr_text(text)))
            except Exception as e:
                logger.warning(f"????OCR??: {e}")
    if _HAS_QWEN and api_keys:
        qwen_key = api_keys.get('qwen_api_key', '')
        if qwen_key:
            try:
                text, raw = qwen_recognize(image_bytes, qwen_key)
                results.append(OCRResult(text, 'qwen_vl', {}, score_ocr_text(text)))
            except Exception as e:
                logger.warning(f"Qwen-VL ????: {e}")
    if _HAS_ZHIPU and api_keys:
        zhipu_key = api_keys.get('zhipuai_api_key', '')
        if zhipu_key:
            try:
                text, raw = zhipu_recognize(image_bytes, zhipu_key)
                results.append(OCRResult(text, 'zhipuai_glm4v', {}, score_ocr_text(text)))
            except Exception as e:
                logger.warning(f"GLM-4V ????: {e}")
    if _HAS_PIX2TEX:
        try:
            text = _run_pix2tex(image_bytes)
            if text:
                if not text.startswith('$'):
                    text = '' + text + ''
                results.append(OCRResult(text, 'pix2tex', {}, score_ocr_text(text)))
        except Exception as e:
            logger.warning(f"pix2tex ????: {e}")
    if not results:
        return OCRResult('', 'none', {}, 0.0), []
    if preferred_engine:
        preferred = [r for r in results if r.engine == preferred_engine]
        if preferred and preferred[0].is_valid:
            return preferred[0], results
    results.sort(key=lambda r: r.score, reverse=True)
    return results[0], results
