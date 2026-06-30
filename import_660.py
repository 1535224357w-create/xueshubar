"""
导入 25年660题（数一）章节结构到知识树（基于Claude视觉识别结果）
"""
from app import app, db
from models import KnowledgePoint


def run():
    with app.app_context():
        # 清空旧数据（先删有外键依赖的表）
        from models import Problem, UserWrongProblem
        UserWrongProblem.query.delete()
        Problem.query.delete()
        KnowledgePoint.query.delete()

        # === 一级分类 ===
        g1 = KnowledgePoint(name='高等数学', description='函数、极限、微积分、级数、微分方程')
        g2 = KnowledgePoint(name='线性代数', description='行列式、矩阵、向量、方程组、二次型')
        g3 = KnowledgePoint(name='概率论与数理统计', description='概率、分布、统计、估计')
        db.session.add_all([g1, g2, g3])
        db.session.flush()

        # === 二级章节 ===
        chapters = [
            # 高数
            (g1.id, '函数与极限', '函数概念与性质、极限定义与计算、连续性'),
            (g1.id, '导数与微分', '导数定义、求导法则、高阶导数、微分'),
            (g1.id, '中值定理与导数应用', '罗尔定理、拉格朗日、泰勒公式、函数单调性、极值、凹凸性'),
            (g1.id, '不定积分', '换元积分、分部积分、特殊积分技巧'),
            (g1.id, '定积分', '定积分性质与计算、反常积分、定积分应用'),
            (g1.id, '多元函数微分学', '偏导数、全微分、链式法则、极值'),
            (g1.id, '重积分', '二重积分、三重积分、重积分应用'),
            (g1.id, '曲线积分与曲面积分', '格林公式、高斯公式、斯托克斯公式'),
            (g1.id, '无穷级数', '常数项级数、幂级数、傅里叶级数'),
            (g1.id, '常微分方程', '一阶微分方程、高阶线性微分方程、微分方程应用'),
            # 线代
            (g2.id, '行列式', '行列式定义、性质、计算、克拉默法则'),
            (g2.id, '矩阵', '矩阵运算、逆矩阵、秩、分块矩阵'),
            (g2.id, '向量', '向量组线性相关、秩、正交、施密特正交化'),
            (g2.id, '线性方程组', '齐次与非齐次方程组解的结构、通解'),
            (g2.id, '特征值与特征向量', '特征值、特征向量、相似对角化、实对称矩阵'),
            (g2.id, '二次型', '二次型标准形、正定二次型、合同变换'),
            # 概率
            (g3.id, '随机事件与概率', '事件运算、条件概率、全概率公式、贝叶斯公式'),
            (g3.id, '一维随机变量', '离散型、连续型、分布函数、概率密度'),
            (g3.id, '多维随机变量', '联合分布、边缘分布、条件分布、独立性'),
            (g3.id, '随机变量的数字特征', '数学期望、方差、协方差、相关系数'),
            (g3.id, '大数定律与中心极限定理', '切比雪夫不等式、大数定律、中心极限定理'),
            (g3.id, '数理统计', '样本与统计量、抽样分布、参数估计、假设检验'),
        ]

        for parent_id, name, desc in chapters:
            db.session.add(KnowledgePoint(name=name, description=desc, parent_id=parent_id))

        db.session.commit()
        print(f'✅ 已导入 3 个一级分类 + {len(chapters)} 个二级章节到知识树')
        print()
        print('知识树结构：')
        for g in [g1, g2, g3]:
            print(f'\n  {g.name}')
            for c in KnowledgePoint.query.filter_by(parent_id=g.id).all():
                print(f'    ├─ {c.name}')


if __name__ == '__main__':
    run()
