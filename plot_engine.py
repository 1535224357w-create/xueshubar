"""
绘图引擎 - 将 DeepSeek 的绘图 JSON 指令渲染为图片

支持类型: area, curve, multi, geometry
"""
import json
import io
import base64
import re
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

# 中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

COLORS = ['#2563eb', '#dc2626', '#16a34a', '#f59e0b', '#8b5cf6', '#06b6d4']
FILL_COLORS = ['#93c5fd', '#fca5a5', '#86efac', '#fde68a', '#c4b5fd', '#67e8f9']


def safe_eval(expr, x):
    """安全计算数学表达式"""
    allowed = {
        'x': x,
        'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
        'arcsin': np.arcsin, 'arccos': np.arccos, 'arctan': np.arctan,
        'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt,
        'abs': np.abs, 'pi': np.pi, 'e': np.e,
    }
    return eval(expr.replace('^', '**'), {"__builtins__": {}}, allowed)


def render_area(curves, x_range, fill=None):
    """积分区域图"""
    x = np.linspace(x_range[0], x_range[1], 500)
    fig, ax = plt.subplots(figsize=(6, 4.5))

    y_values = []
    for i, expr in enumerate(curves):
        y = safe_eval(expr, x)
        y_values.append(y)
        ax.plot(x, y, color=COLORS[i % len(COLORS)], linewidth=2, label=f'y = {expr}')

    if fill and len(y_values) >= 2:
        x_fill = np.linspace(max(fill[0], x_range[0]), min(fill[1], x_range[1]), 300)
        y_fill = [safe_eval(e, x_fill) for e in curves[:2]]
        ax.fill_between(x_fill, y_fill[0], y_fill[1], alpha=0.3, color='#22c55e', label='面积')

    _setup_axes(ax, x_range)
    ax.legend(fontsize=10)
    return _save(fig)


def render_curve(formula, x_range):
    """单条函数曲线"""
    x = np.linspace(x_range[0], x_range[1], 500)
    fig, ax = plt.subplots(figsize=(6, 4))
    y = safe_eval(formula, x)
    ax.plot(x, y, color=COLORS[0], linewidth=2, label=f'y = {formula}')
    _setup_axes(ax, x_range)
    ax.legend(fontsize=10)
    return _save(fig)


def render_multi(formulas, x_range):
    """多条曲线对比"""
    x = np.linspace(x_range[0], x_range[1], 500)
    fig, ax = plt.subplots(figsize=(6, 4.5))

    for i, expr in enumerate(formulas):
        y = safe_eval(expr, x)
        ax.plot(x, y, color=COLORS[i % len(COLORS)], linewidth=2, label=f'y = {expr}')

    _setup_axes(ax, x_range)
    ax.legend(fontsize=10)
    return _save(fig)


def render_geometry(shapes):
    """几何图形"""
    fig, ax = plt.subplots(figsize=(5, 5))

    for shape in shapes:
        t = shape.get('type', '')
        if t == 'circle':
            c = shape.get('center', [0, 0])
            r = shape.get('radius', 1)
            circle = plt.Circle(c, r, fill=False, color=COLORS[0], linewidth=2)
            ax.add_patch(circle)
        elif t == 'line':
            fr = shape.get('from', [0, 0])
            to = shape.get('to', [1, 1])
            ax.plot([fr[0], to[0]], [fr[1], to[1]], color=COLORS[1], linewidth=2)
        elif t == 'polygon':
            pts = shape.get('points', [])
            if pts:
                poly = Polygon(pts, fill=True, alpha=0.3, color=COLORS[2])
                ax.add_patch(poly)

    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color='gray', linewidth=0.5)
    ax.axvline(0, color='gray', linewidth=0.5)
    return _save(fig)


def _setup_axes(ax, x_range):
    """设置坐标轴"""
    ax.axhline(0, color='gray', linewidth=0.5, alpha=0.5)
    ax.axvline(0, color='gray', linewidth=0.5, alpha=0.5)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(x_range[0], x_range[1])


def _save(fig):
    """保存为 base64"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def render_from_json(plot_json):
    """从 JSON 指令渲染图表"""
    plot_type = plot_json.get('type', '')
    try:
        if plot_type == 'area':
            return render_area(
                plot_json.get('curves', []),
                plot_json.get('x_range', [-3, 3]),
                plot_json.get('fill')
            )
        elif plot_type == 'curve':
            return render_curve(
                plot_json.get('formula', 'x'),
                plot_json.get('x_range', [-5, 5])
            )
        elif plot_type == 'multi':
            return render_multi(
                plot_json.get('formulas', []),
                plot_json.get('x_range', [-3, 3])
            )
        elif plot_type == 'geometry':
            return render_geometry(plot_json.get('shapes', []))
        return None
    except Exception:
        return None


def extract_plots(text):
    """
    从文本中提取所有 【PLOT】JSON【/PLOT】 标记
    返回 [(json对象, 原始标记), ...]
    """
    pattern = r'【PLOT】(.+?)【/PLOT】'
    matches = re.findall(pattern, text, re.DOTALL)
    results = []
    for m in matches:
        try:
            obj = json.loads(m.strip())
            results.append((obj, f'【PLOT】{m}【/PLOT】'))
        except json.JSONDecodeError:
            continue
    return results
