"""
解题分析服务 - 用 DeepSeek 生成多解法详细解答
"""
from openai import OpenAI


def generate_solution(content, api_key, base_url='https://api.deepseek.com',
                       model='deepseek-reasoner'):
    """
    生成数学题的详细解题分析（多解法）

    :return: 解题分析文本，失败返回 None
    """
    if not api_key or not content:
        return None

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            max_tokens=4096,
            timeout=120,
            messages=[{
                'role': 'user',
                'content': (
                    '你是一名高等数学老师。请对以下数学题给出详细解答。\n\n'
                    '题目：' + content + '\n\n'
                    '要求：\n'
                    '1. 用中文回答\n'
                    '2. 给出多种解法（至少两种不同思路）\n'
                    '3. 每种解法包括：解题思路、详细步骤、最终答案\n'
                    '4. 数学公式用 $...$ 或 $$...$$ 包裹（例如 $\\lim_{x \\to 0}$）\n'
                    '5. 最后总结这道题考察的知识点和解题关键'
                )
            }]
        )
        return resp.choices[0].message.content
    except Exception:
        return None
