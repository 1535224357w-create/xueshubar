"""
导入 张宇30讲 线代+概率 知识树
"""
from app import app, db
from models import KnowledgePoint


def run():
    with app.app_context():
        sections = [
            ('张宇基础30讲（线代）', '线性代数', [
                ('零基础课——线性代数入门', '向量基本概念、向量运算、线性变换'),
                ('第1讲 行列式', '行列式的定义、性质、计算、克拉默法则'),
                ('第2讲 矩阵', '矩阵运算、逆矩阵、秩、分块矩阵、初等变换'),
                ('第3讲 向量组', '向量组线性相关性、秩、正交性、施密特正交化'),
                ('第4讲 线性方程组', '齐次与非齐次方程组解的结构、通解'),
                ('第5讲 特征值与特征向量', '特征值特征向量、相似对角化、实对称矩阵'),
                ('第6讲 二次型', '二次型标准形、正定二次型、合同变换'),
            ]),
            ('张宇基础30讲（概率）', '概率论与数理统计', [
                ('第1讲 随机事件与概率', '事件运算、条件概率、全概率公式、贝叶斯公式、独立性'),
                ('第2讲 一维随机变量及其分布', '分布函数、概率质量函数、概率密度函数、常见分布'),
                ('第3讲 多维随机变量及其分布', '联合分布、边际分布、条件分布、独立性'),
                ('第4讲 随机变量的数字特征', '数学期望、方差、协方差与相关系数'),
                ('第5讲 大数定理与中心极限定理', '大数定律、中心极限定理'),
                ('第6讲 数理统计', '样本分布、参数估计、假设检验'),
            ]),
        ]

        total = 0
        for cat_name, label, lectures in sections:
            if KnowledgePoint.query.filter_by(name=cat_name).first():
                print(f'[Skip] {cat_name} 已存在')
                continue

            root = KnowledgePoint(name=cat_name, description='张宇基础30讲·' + label + '分册')
            db.session.add(root)
            db.session.flush()
            for name, desc in lectures:
                db.session.add(KnowledgePoint(name=name, description=desc, parent_id=root.id))
            db.session.commit()
            print(f'[OK] {cat_name}: {len(lectures)} 章')
            total += len(lectures)

        print(f'\n共导入 {total} 个章节')


if __name__ == '__main__':
    run()
