"""
图像预处理工具 — 优化图片质量以提高 OCR 识别准确率

包含：
- 自适应对比度增强 (CLAHE)
- 二值化 (Otsu / 自适应阈值)
- 去噪 (中值滤波 / 高斯滤波)
- 倾斜校正 (deskew)
- 管道函数：一键预处理
"""

import io
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance


def _to_array(pil_img):
    """PIL Image → numpy array (灰度)"""
    if pil_img.mode != 'L':
        pil_img = pil_img.convert('L')
    return np.array(pil_img)


def _to_pil(arr):
    """numpy array → PIL Image"""
    return Image.fromarray(arr)


def enhance_contrast(image_bytes, clip_limit=2.0, tile_grid=(8, 8)):
    """
    CLAHE 自适应直方图均衡化 — 显著提升低对比度图片的文字可识别度
    """
    try:
        import cv2
        has_cv2 = True
    except ImportError:
        has_cv2 = False

    img = Image.open(io.BytesIO(image_bytes))
    arr = _to_array(img)

    if has_cv2:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
        enhanced = clahe.apply(arr)
    else:
        enhancer = ImageEnhance.Contrast(img.convert('L'))
        enhanced = enhancer.enhance(1.5)
        return _to_bytes(enhanced, 'JPEG')

    return _to_bytes(_to_pil(enhanced), 'JPEG')


def binarize(image_bytes, method='otsu', block_size=15, c_value=10):
    """
    二值化 — 将图片转为黑白，消除阴影和背景干扰
    """
    try:
        import cv2
        has_cv2 = True
    except ImportError:
        has_cv2 = False

    img = Image.open(io.BytesIO(image_bytes))
    arr = _to_array(img)

    if has_cv2:
        if method == 'otsu':
            _, binary = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            binary = cv2.adaptiveThreshold(
                arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, block_size, c_value
            )
    else:
        gray = img.convert('L')
        threshold = 128
        binary = gray.point(lambda p: 255 if p > threshold else 0)
        return _to_bytes(binary, 'PNG')

    return _to_bytes(_to_pil(binary), 'PNG')


def denoise(image_bytes, strength='medium'):
    """去噪 — 消除扫描/拍照噪点"""
    try:
        import cv2
        has_cv2 = True
    except ImportError:
        has_cv2 = False

    img = Image.open(io.BytesIO(image_bytes))

    if has_cv2:
        arr = _to_array(img)
        if strength == 'light':
            filtered = cv2.GaussianBlur(arr, (3, 3), 0)
        elif strength == 'medium':
            filtered = cv2.medianBlur(arr, 3)
        else:
            filtered = cv2.fastNlMeansDenoising(arr, None, 10, 7, 21)
        return _to_bytes(_to_pil(filtered), 'JPEG')
    else:
        img_gray = img.convert('L')
        if strength == 'light':
            filtered = img_gray.filter(ImageFilter.SMOOTH)
        else:
            filtered = img_gray.filter(ImageFilter.MedianFilter(size=3))
        return _to_bytes(filtered, 'JPEG')


def deskew(image_bytes, max_angle=15):
    """倾斜校正 — 检测并校正图片旋转"""
    try:
        import cv2
    except ImportError:
        return image_bytes

    img = Image.open(io.BytesIO(image_bytes))
    arr = _to_array(img)
    _, binary = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(binary > 0))
    if len(coords) < 10:
        return image_bytes
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.5 or abs(angle) > max_angle:
        return image_bytes
    h, w = arr.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(arr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return _to_bytes(_to_pil(rotated), 'JPEG')


def upscale(image_bytes, scale=2):
    """放大 — 对低分辨率图片放大以提高OCR识别率"""
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    new_size = (w * scale, h * scale)
    enlarged = img.resize(new_size, Image.LANCZOS)
    return _to_bytes(enlarged, 'JPEG')


def preprocess_pipeline(image_bytes, steps=None):
    """
    完整预处理管道
    默认: upscale → enhance → denoise → binarize
    """
    if steps is None:
        steps = ['upscale', 'enhance', 'denoise', 'binarize']
    data = image_bytes
    for step in steps:
        if step == 'upscale':
            data = upscale(data, scale=2)
        elif step == 'enhance':
            data = enhance_contrast(data)
        elif step == 'denoise':
            data = denoise(data, strength='medium')
        elif step == 'binarize':
            data = binarize(data, method='otsu')
        elif step == 'deskew':
            data = deskew(data)
        elif step == 'enhance_light':
            data = enhance_contrast(data, clip_limit=1.5)
    return data


def preprocess_for_baidu(image_bytes):
    """为百度 OCR 优化：放大 + 对比度 + 去噪"""
    return preprocess_pipeline(image_bytes, steps=['upscale', 'enhance', 'denoise'])


def preprocess_for_pix2tex(image_bytes):
    """为 LaTeX-OCR 优化：放大 + 轻对比度 + 二值化"""
    return preprocess_pipeline(image_bytes, steps=['upscale', 'enhance_light', 'binarize'])


def preprocess_for_vision_model(image_bytes):
    """为视觉语言模型优化：放大 + 轻对比度"""
    return preprocess_pipeline(image_bytes, steps=['upscale', 'enhance_light'])


def _to_bytes(pil_img, fmt='JPEG'):
    """PIL Image → bytes"""
    buf = io.BytesIO()
    pil_img.save(buf, format=fmt, quality=95)
    return buf.getvalue()
