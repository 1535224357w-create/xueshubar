"""
数学计算引擎 - 使用 SymPy 进行精确的符号数学计算
"""
import sympy as sp
import re


class MathEngine:
    """符号数学计算引擎，支持极限、积分、导数等高等数学运算"""

    def __init__(self):
        self.x = sp.symbols('x')
        self.y = sp.symbols('y')
        self.z = sp.symbols('z')
        self.n = sp.symbols('n')
        self.t = sp.symbols('t')

    def compute_limit(self, expr_str, var='x', approach=0):
        """计算极限"""
        expr = sp.sympify(expr_str)
        var_sym = sp.Symbol(var)
        result = sp.limit(expr, var_sym, approach)
        return sp.nsimplify(result)

    def compute_integral(self, expr_str, var='x'):
        """计算不定积分"""
        expr = sp.sympify(expr_str)
        var_sym = sp.Symbol(var)
        result = sp.integrate(expr, var_sym)
        return result

    def compute_definite_integral(self, expr_str, var='x', lower=0, upper=1):
        """计算定积分"""
        expr = sp.sympify(expr_str)
        var_sym = sp.Symbol(var)
        result = sp.integrate(expr, (var_sym, lower, upper))
        return sp.nsimplify(result)

    def compute_derivative(self, expr_str, var='x', order=1):
        """计算导数"""
        expr = sp.sympify(expr_str)
        var_sym = sp.Symbol(var)
        result = sp.diff(expr, var_sym, order)
        return result

    def solve_equation(self, eq_str, var='x'):
        """解方程"""
        var_sym = sp.Symbol(var)
        eq = sp.sympify(eq_str)
        if not isinstance(eq, sp.Eq):
            eq = sp.Eq(eq, 0)
        solutions = sp.solve(eq, var_sym)
        return solutions

    def evaluate(self, expr_str, var='x', value=0):
        """代入求值"""
        expr = sp.sympify(expr_str)
        var_sym = sp.Symbol(var)
        return expr.subs(var_sym, value)

    def to_latex(self, expr):
        """转 LaTeX 格式"""
        return sp.latex(expr)


# 测试
if __name__ == '__main__':
    m = MathEngine()
    print('测试 SymPy 计算能力：')
    print(f'lim x->0 sin(2x)/x = {m.compute_limit("sin(2*x)/x")}')
    print(f'int sin(2x) dx = {m.compute_integral("sin(2*x)")}')
    print(f'd/dx x^3 = {m.compute_derivative("x**3")}')
    print(f'int_0^1 x^2 dx = {m.compute_definite_integral("x**2", lower=0, upper=1)}')
    print(f'x^2-5x+6=0 的解: {m.solve_equation("x**2 - 5*x + 6")}')
