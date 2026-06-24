"""
种子题目导入脚本

使用方法：
1. 按照下面的格式准备好你的题目（可以批量加）
2. 运行：python seed_data.py
3. 题目就会自动导入数据库

题目格式说明：
- content: 题目内容，LaTeX 公式用 $...$ 或 $$...$$ 括起来
- answer: 答案
- explanation: 解析
- difficulty: 难度 1~5
- knowledge_point_name: 对应的知识点名称（必须在知识树中存在）
"""

from app import app, db, init_database
from models import Problem, KnowledgePoint

# =============================================
# 在这里添加你的题目！
# 每条题目是一个字典，格式如下：
# =============================================
SEED_PROBLEMS = [
    # ---- 极限 ----
    {
        "content": "求极限 $\\lim_{x \\to 0} \\frac{\\sin x}{x}$",
        "answer": "1",
        "explanation": "这是重要极限 $\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1$。可以使用夹逼定理或洛必达法则证明。",
        "difficulty": 2,
        "knowledge_point_name": "极限"
    },
    {
        "content": "求极限 $\\lim_{x \\to 0} \\frac{1 - \\cos x}{x^2}$",
        "answer": "$\\frac{1}{2}$",
        "explanation": "利用 $1 - \\cos x \\sim \\frac{1}{2}x^2$（当 $x \\to 0$），所以原式 $= \\frac{1}{2}$。",
        "difficulty": 2,
        "knowledge_point_name": "极限"
    },
    {
        "content": "求极限 $\\lim_{x \\to \\infty} \\left(1 + \\frac{1}{x}\\right)^x$",
        "answer": "$e$",
        "explanation": "这是第二个重要极限 $\\lim_{x \\to \\infty} (1 + \\frac{1}{x})^x = e$。",
        "difficulty": 2,
        "knowledge_point_name": "极限"
    },
    {
        "content": "求极限 $\\lim_{x \\to 0} \\frac{\\sin 3x}{\\sin 2x}$",
        "answer": "$\\frac{3}{2}$",
        "explanation": "利用 $\\lim_{x \\to 0} \\frac{\\sin ax}{\\sin bx} = \\frac{a}{b}$。因为 $\\frac{\\sin 3x}{3x} \\to 1$，$\\frac{\\sin 2x}{2x} \\to 1$，所以原式 $= \\frac{3}{2}$。",
        "difficulty": 2,
        "knowledge_point_name": "极限"
    },
    {
        "content": "求极限 $\\lim_{x \\to 0} \\frac{e^x - 1}{x}$",
        "answer": "1",
        "explanation": "利用等价无穷小 $e^x - 1 \\sim x$（当 $x \\to 0$），所以原式 $= 1$。也可以用导数定义：$\\left. \\frac{d}{dx}e^x \\right|_{x=0} = 1$。",
        "difficulty": 3,
        "knowledge_point_name": "极限"
    },
    {
        "content": "求极限 $\\lim_{x \\to 0+} x \\ln x$",
        "answer": "0",
        "explanation": "令 $t = \\frac{1}{x}$，则原式 $= \\lim_{t \\to +\\infty} \\frac{-\\ln t}{t} = 0$（幂函数增长快于对数函数）。",
        "difficulty": 3,
        "knowledge_point_name": "极限"
    },
    {
        "content": "求极限 $\\lim_{x \\to 0} \\frac{\\tan x - \\sin x}{x^3}$",
        "answer": "$\\frac{1}{2}$",
        "explanation": "$\\tan x - \\sin x = \\tan x(1 - \\cos x) \\sim x \\cdot \\frac{x^2}{2} = \\frac{x^3}{2}$，所以原式 $= \\frac{1}{2}$。",
        "difficulty": 4,
        "knowledge_point_name": "极限"
    },

    # ---- 导数 ----
    {
        "content": "求 $y = x^3 + 2x^2 - 5x + 1$ 的导数",
        "answer": "$y' = 3x^2 + 4x - 5$",
        "explanation": "利用幂函数求导公式 $(x^n)' = nx^{n-1}$，逐项求导。",
        "difficulty": 1,
        "knowledge_point_name": "导数与微分"
    },
    {
        "content": "求 $y = e^x \\sin x$ 的导数",
        "answer": "$y' = e^x(\\sin x + \\cos x)$",
        "explanation": "利用乘积法则 $(uv)' = u'v + uv'$，其中 $u = e^x$，$v = \\sin x$。所以 $y' = e^x\\sin x + e^x\\cos x = e^x(\\sin x + \\cos x)$。",
        "difficulty": 2,
        "knowledge_point_name": "导数与微分"
    },
    {
        "content": "求 $y = \\ln(\\sin x)$ 的导数",
        "answer": "$y' = \\cot x$",
        "explanation": "利用链式法则：$y' = \\frac{1}{\\sin x} \\cdot \\cos x = \\cot x$。",
        "difficulty": 2,
        "knowledge_point_name": "导数与微分"
    },
    {
        "content": "求曲线 $y = x^3 - 3x + 1$ 在点 $(1, -1)$ 处的切线方程",
        "answer": "$y = -1$",
        "explanation": "$y' = 3x^2 - 3$，在 $x=1$ 处 $y' = 0$。所以切线方程为 $y - (-1) = 0(x - 1)$，即 $y = -1$。这条切线是水平的。",
        "difficulty": 3,
        "knowledge_point_name": "导数与微分"
    },

    # ---- 不定积分 ----
    {
        "content": "求不定积分 $\\int x^2 dx$",
        "answer": "$\\frac{x^3}{3} + C$",
        "explanation": "利用幂函数积分公式 $\\int x^n dx = \\frac{x^{n+1}}{n+1} + C$（$n \\neq -1$）。",
        "difficulty": 1,
        "knowledge_point_name": "不定积分"
    },
    {
        "content": "求不定积分 $\\int \\sin x \\, dx$",
        "answer": "$-\\cos x + C$",
        "explanation": "$\\int \\sin x \\, dx = -\\cos x + C$，因为 $(-\\cos x)' = \\sin x$。",
        "difficulty": 1,
        "knowledge_point_name": "不定积分"
    },
    {
        "content": "求不定积分 $\\int \\frac{1}{x} dx$",
        "answer": "$\\ln|x| + C$",
        "explanation": "这是基本积分公式，注意要加绝对值。",
        "difficulty": 1,
        "knowledge_point_name": "不定积分"
    },
    {
        "content": "求不定积分 $\\int x e^x dx$",
        "answer": "$(x-1)e^x + C$",
        "explanation": "使用分部积分法：令 $u = x$，$dv = e^x dx$，则 $du = dx$，$v = e^x$。$\\int x e^x dx = xe^x - \\int e^x dx = xe^x - e^x + C = (x-1)e^x + C$。",
        "difficulty": 3,
        "knowledge_point_name": "不定积分"
    },
    {
        "content": "求不定积分 $\\int \\frac{1}{\\sqrt{1-x^2}} dx$",
        "answer": "$\\arcsin x + C$",
        "explanation": "这是基本积分公式 $\\int \\frac{1}{\\sqrt{1-x^2}} dx = \\arcsin x + C$。",
        "difficulty": 2,
        "knowledge_point_name": "不定积分"
    },
    {
        "content": "用换元法求 $\\int \\cos(3x+1) dx$",
        "answer": "$\\frac{1}{3}\\sin(3x+1) + C$",
        "explanation": "令 $u = 3x+1$，则 $du = 3dx$，$dx = \\frac{du}{3}$。原式 $= \\int \\cos u \\cdot \\frac{du}{3} = \\frac{1}{3}\\sin u + C = \\frac{1}{3}\\sin(3x+1) + C$。",
        "difficulty": 2,
        "knowledge_point_name": "不定积分"
    },

    # ---- 定积分 ----
    {
        "content": "计算定积分 $\\int_0^1 x^2 dx$",
        "answer": "$\\frac{1}{3}$",
        "explanation": "$\\int_0^1 x^2 dx = \\left[\\frac{x^3}{3}\\right]_0^1 = \\frac{1}{3} - 0 = \\frac{1}{3}$。",
        "difficulty": 1,
        "knowledge_point_name": "定积分"
    },
    {
        "content": "计算定积分 $\\int_0^\\pi \\sin x \\, dx$",
        "answer": "2",
        "explanation": "$\\int_0^\\pi \\sin x \\, dx = [-\\cos x]_0^\\pi = (-\\cos\\pi) - (-\\cos 0) = 1 + 1 = 2$。",
        "difficulty": 1,
        "knowledge_point_name": "定积分"
    },
    {
        "content": "计算定积分 $\\int_0^1 xe^x dx$",
        "answer": "1",
        "explanation": "先用分部积分求原函数：$\\int xe^x dx = (x-1)e^x + C$，所以 $\\int_0^1 xe^x dx = [(x-1)e^x]_0^1 = 0 - (-1) = 1$。",
        "difficulty": 3,
        "knowledge_point_name": "定积分"
    },

    # ---- 偏导数 ----
    {
        "content": "求 $f(x,y) = x^2y + y^3$ 的偏导数 $f_x$ 和 $f_y$",
        "answer": "$f_x = 2xy$，$f_y = x^2 + 3y^2$",
        "explanation": "对 $x$ 求偏导时，$y$ 视为常数：$f_x = 2xy$。对 $y$ 求偏导时，$x$ 视为常数：$f_y = x^2 + 3y^2$。",
        "difficulty": 1,
        "knowledge_point_name": "偏导数"
    },
    {
        "content": "求 $z = e^{xy}$ 的偏导数 $\\frac{\\partial z}{\\partial x}$ 和 $\\frac{\\partial z}{\\partial y}$",
        "answer": "$\\frac{\\partial z}{\\partial x} = ye^{xy}$，$\\frac{\\partial z}{\\partial y} = xe^{xy}$",
        "explanation": "由链式法则：$\\frac{\\partial}{\\partial x}e^{xy} = e^{xy} \\cdot y = ye^{xy}$，同理 $\\frac{\\partial}{\\partial y}e^{xy} = e^{xy} \\cdot x = xe^{xy}$。",
        "difficulty": 2,
        "knowledge_point_name": "偏导数"
    },

    # ---- 矩阵运算 ----
    {
        "content": "已知 $A = \\begin{pmatrix} 1 & 2 \\\\ 3 & 4 \\end{pmatrix}$，$B = \\begin{pmatrix} 2 & 0 \\\\ 1 & 2 \\end{pmatrix}$，求 $A + B$",
        "answer": "$A+B = \\begin{pmatrix} 3 & 2 \\\\ 4 & 6 \\end{pmatrix}$",
        "explanation": "矩阵加法对应元素相加：$\\begin{pmatrix} 1+2 & 2+0 \\\\ 3+1 & 4+2 \\end{pmatrix}$。",
        "difficulty": 1,
        "knowledge_point_name": "矩阵运算"
    },
    {
        "content": "已知 $A = \\begin{pmatrix} 1 & 2 \\\\ 3 & 4 \\end{pmatrix}$，$B = \\begin{pmatrix} 2 & 0 \\\\ 1 & 2 \\end{pmatrix}$，求 $AB$",
        "answer": "$AB = \\begin{pmatrix} 4 & 4 \\\\ 10 & 8 \\end{pmatrix}$",
        "explanation": "矩阵乘法：$AB_{11} = 1\\cdot2 + 2\\cdot1 = 4$，$AB_{12} = 1\\cdot0 + 2\\cdot2 = 4$，$AB_{21} = 3\\cdot2 + 4\\cdot1 = 10$，$AB_{22} = 3\\cdot0 + 4\\cdot2 = 8$。",
        "difficulty": 2,
        "knowledge_point_name": "矩阵运算"
    },

    # ---- 行列式 ----
    {
        "content": "计算行列式 $\\begin{vmatrix} 1 & 2 \\\\ 3 & 4 \\end{vmatrix}$",
        "answer": "$-2$",
        "explanation": "二阶行列式公式：$\\begin{vmatrix} a & b \\\\ c & d \\end{vmatrix} = ad - bc = 1\\cdot4 - 2\\cdot3 = 4 - 6 = -2$。",
        "difficulty": 1,
        "knowledge_point_name": "行列式"
    },

    # ---- 一阶微分方程 ----
    {
        "content": "求解微分方程 $\\frac{dy}{dx} = 2xy$",
        "answer": "$y = Ce^{x^2}$",
        "explanation": "分离变量法：$\\frac{dy}{y} = 2x dx$，两边积分得 $\\ln|y| = x^2 + C$，所以 $y = Ce^{x^2}$。",
        "difficulty": 2,
        "knowledge_point_name": "一阶微分方程"
    },

    # ---- 二阶微分方程 ----
    {
        "content": "求解微分方程 $y'' - 3y' + 2y = 0$",
        "answer": "$y = C_1e^x + C_2e^{2x}$",
        "explanation": "特征方程 $r^2 - 3r + 2 = 0$，解得 $r_1 = 1$，$r_2 = 2$。所以通解为 $y = C_1e^{x} + C_2e^{2x}$。",
        "difficulty": 3,
        "knowledge_point_name": "二阶微分方程"
    },

    # ---- 重积分 ----
    {
        "content": "计算二重积分 $\\iint_D (x+y) dA$，其中 $D$ 是由 $x=0$，$y=0$，$x+y=1$ 围成的三角形区域。",
        "answer": "$\\frac{1}{3}$",
        "explanation": "积分区域 $D: 0 \\le x \\le 1, 0 \\le y \\le 1-x$。所以 $\\iint_D (x+y)dA = \\int_0^1 \\int_0^{1-x} (x+y) dy dx = \\int_0^1 [xy + \\frac{y^2}{2}]_0^{1-x} dx = \\int_0^1 (x(1-x) + \\frac{(1-x)^2}{2}) dx = \\frac{1}{3}$。",
        "difficulty": 3,
        "knowledge_point_name": "重积分"
    },

    # ---- 随机变量 ----
    {
        "content": "设随机变量 $X \\sim N(0,1)$，求 $P(-1 < X < 1)$。（已知 $\\Phi(1) = 0.8413$）",
        "answer": "$0.6826$",
        "explanation": "$P(-1 < X < 1) = \\Phi(1) - \\Phi(-1) = \\Phi(1) - (1 - \\Phi(1)) = 2\\Phi(1) - 1 = 2 \\times 0.8413 - 1 = 0.6826$。",
        "difficulty": 2,
        "knowledge_point_name": "随机变量"
    },
]


def seed():
    """导入所有种子题目到数据库"""
    with app.app_context():
        init_database()

        # 查询已有的题目数量，避免重复导入
        existing_count = Problem.query.count()
        if existing_count > 5:
            print(f"数据库已有 {existing_count} 道题目，跳过种子导入。")
            print("如果要重新导入，请先删除数据库文件 mathlearn.db")
            return

        count = 0
        for data in SEED_PROBLEMS:
            # 查找知识点
            kp_name = data.pop("knowledge_point_name")
            kp = KnowledgePoint.query.filter_by(name=kp_name).first()
            if not kp:
                print(f"[跳过] 知识点 '{kp_name}' 不存在")
                continue

            problem = Problem(
                content=data["content"],
                answer=data.get("answer", ""),
                explanation=data.get("explanation", ""),
                difficulty=data.get("difficulty", 1),
                knowledge_point_id=kp.id,
                source="system"
            )
            db.session.add(problem)
            count += 1

        db.session.commit()
        print(f"[成功] 导入 {count} 道题目！")


if __name__ == "__main__":
    seed()
