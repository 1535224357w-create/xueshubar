"""
修复已导入题目的知识点映射
"""
import re
from app import app, db
from models import Problem, KnowledgePoint

# 知识点匹配规则 (keyword -> lecture name contains)
KP_RULES = {
    '极限': ['函数极限'],
    '连续': ['函数极限'],
    '无穷小': ['函数极限'],
    '数列': ['数列极限'],
    '导数': ['微分学的概念'],
    '求导': ['微分学的概念'],
    '可导': ['微分学的概念'],
    '中值': ['微分学的应用'],
    '泰勒': ['微分学的应用'],
    '洛必达': ['微分学的应用'],
    '单调': ['微分学的应用'],
    '极值': ['微分学的应用'],
    '最值': ['微分学的应用'],
    '凹凸': ['微分学的应用'],
    '拐点': ['微分学的应用'],
    '渐近': ['微分学的应用'],
    '不定积分': ['积分学概念'],
    '原函数': ['积分学概念'],
    '定积分': ['定积分'],
    '换元': ['定积分的计算'],
    '分部积分': ['定积分的计算'],
    '面积': ['定积分的应用'],
    '体积': ['定积分的应用'],
    '弧长': ['定积分的应用'],
    '参数方程': ['定积分的应用'],
    '极坐标': ['定积分的应用'],
    '多元': ['多元函数微分学'],
    '偏导': ['多元函数微分学'],
    '全微分': ['多元函数微分学'],
    '梯度': ['多元函数微分学应用'],
    '拉格朗日乘': ['多元函数微分学应用'],
    '条件极值': ['多元函数微分学应用'],
    '二重积分': ['二重积分'],
    '微分方程': ['微分方程'],
    '级数': ['无穷级数'],
    '收敛': ['无穷级数'],
    '函数': ['函数极限'],
    '不等式': ['函数极限'],
    '零点': ['函数极限'],
    '方程根': ['函数极限'],
    '切线': ['微分学的概念'],
    '法线': ['微分学的概念'],
    '对称性': ['二重积分'],
    '旋转': ['定积分的应用'],
    '通解': ['微分方程'],
    '特解': ['微分方程'],
}


def find_best_lecture(content, lecture_mapping):
    """根据题目内容找到最匹配的知识点"""
    for keyword, lecture_names in KP_RULES.items():
        if keyword in content:
            for ln in lecture_names:
                for lid, lname in lecture_mapping:
                    if ln in lname:
                        return lid
    return None


def run():
    with app.app_context():
        root = KnowledgePoint.query.filter_by(name='张宇基础30讲（高数）').first()
        if not root:
            print('Error: root node not found')
            return

        lectures = KnowledgePoint.query.filter_by(parent_id=root.id).all()
        lecture_mapping = [(l.id, l.name) for l in lectures]

        # 找所有指向根节点的题目（即目前默认分配到根节点的）
        problems = Problem.query.filter_by(knowledge_point_id=root.id).all()
        print(f'找到 {len(problems)} 道需要修复映射的题目')

        fixed = 0
        for p in problems:
            new_kp_id = find_best_lecture(p.content, lecture_mapping)
            if new_kp_id:
                p.knowledge_point_id = new_kp_id
                fixed += 1

        db.session.commit()
        print(f'已修复 {fixed} 道题的知识点映射')

        # 统计现有分布
        print('\n各知识点题目数:')
        for lid, lname in lecture_mapping:
            cnt = Problem.query.filter_by(knowledge_point_id=lid).count()
            if cnt > 0:
                print(f'  {lname}: {cnt}')


if __name__ == '__main__':
    run()
