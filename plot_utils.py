"""
图表生成工具 - 用 Matplotlib 绘制数学函数图
支持单条或多条曲线、积分区域填充等
"""
import io
import base64
import re
import numpy as np


def generate_plot(formulas, x_from=-3, x_to=3, title='示意图'):
    """
    根据公式生成函数图
    formulas: 字符串或字符串列表，如 'x^2' 或 ['x^2', 'x']
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        x = np.linspace(x_from, x_to, 400)
        allowed = {
            'x': x, 'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
            'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt,
            'pi': np.pi, 'e': np.e, 'abs': np.abs,
        }
        colors = ['#2563eb', '#dc2626', '#16a34a', '#f59e0b', '#8b5cf6']

        if isinstance(formulas, str):
            formulas = [formulas]

        plt.figure(figsize=(6, 4.5), dpi=100)

        for i, f in enumerate(formulas):
            expr = f.replace('^', '**').strip()
            y = eval(expr, {"__builtins__": {}}, allowed)
            plt.plot(x, y, color=colors[i % len(colors)],
                     linewidth=2, label=f'y = {f}')

        plt.axhline(y=0, color='gray', linewidth=0.5, alpha=0.5)
        plt.axvline(x=0, color='gray', linewidth=0.5, alpha=0.5)
        plt.grid(True, alpha=0.3)
        plt.xlim(x_from, x_to)
        if title:
            plt.title(title, fontsize=12, fontweight='bold')
        if len(formulas) > 1:
            plt.legend(fontsize=9)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
    except Exception:
        return None
