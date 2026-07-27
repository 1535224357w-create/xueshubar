"""
导入 张宇基础30讲（高数）知识点结构到知识树
- 不覆盖已有数据，添加为独立板块
"""
from app import app, db
from models import KnowledgePoint, Problem


def run():
    with app.app_context():
        # 检查是否已导入过
        existing = KnowledgePoint.query.filter_by(name='张宇基础30讲（高数）').first()
        if existing:
            print('[OK] 知识树已存在，跳过导入')
            return

        # === 新建根节点（独立板块） ===
        root = KnowledgePoint(
            name='张宇基础30讲（高数）',
            description='张宇基础30讲·高等数学分册（考研数学一/二/三通用）'
        )
        db.session.add(root)
        db.session.flush()

        # === 第1-18讲 为主要章节 ===
        lectures = [
            (1, '函数极限与连续', '函数概念、极限定义与计算、无穷小、连续性、间断点'),
            (2, '数列极限', '数列概念、数列极限定义与性质、单调有界准则'),
            (3, '一元函数微分学的概念', '导数的定义与几何意义、可导性、高阶导数'),
            (4, '一元函数微分学的应用（一）', '微分应用、中值定理（罗尔、拉格朗日、柯西）、泰勒公式、洛必达'),
            (5, '一元函数微分学的应用（二）', '函数单调性、极值与最值、凹凸性与拐点、渐近线'),
            (6, '一元函数微分学的应用（三）', '中值定理综合、微分学几何/物理应用、曲率'),
            (7, '一元函数积分学概念', '原函数与不定积分、积分公式、换元法与分部积分法'),
            (8, '定积分的概念与性质', '定积分定义、性质、变限积分、牛顿-莱布尼茨公式'),
            (9, '定积分的计算', '定积分计算方法、换元法、分部积分法、分段函数积分'),
            (10, '定积分的应用（一）', '面积、体积、弧长、物理应用'),
            (11, '定积分的应用（二）', '积分等式、积分不等式、证明题'),
            (12, '定积分的应用（三）', '参数方程、极坐标方程的应用'),
            (13, '多元函数微分学', '多元函数概念、偏导数、全微分、复合函数求导'),
            (14, '二重积分', '二重积分概念、直角坐标与极坐标计算'),
            (15, '微分方程', '一阶微分方程、可分离变量、齐次、线性、高阶线性'),
            (16, '无穷级数', '级数概念、收敛性判定、正项级数、交错级数'),
            (17, '多元函数微分学应用', '极值、条件极值与拉格朗日乘数法、梯度'),
            (18, '隐函数与复合函数求导', '全微分条件、偏导数连续性、复合/隐函数求导'),
        ]

        for num, name, desc in lectures:
            kp = KnowledgePoint(
                name='第%d讲 %s' % (num, name),
                description=desc,
                parent_id=root.id
            )
            db.session.add(kp)

        # === 附录 ===
        appendices = [
            ('附录1 重要公式', '常用公式汇总、求导公式、积分公式、泰勒级数'),
            ('附录2 常用函数', '三角函数、反三角函数、指数对数函数、双曲函数'),
            ('附录3 常用函数的图像与性质', '常见函数图像、性质'),
            ('附录4 重要恒等式与极限', '数学恒等式、重要极限公式'),
            ('附录5 级数求和', '和函数求级数、各类求和方法'),
            ('附录6 变形技巧', '代数变形、三角变换、恒等变形'),
        ]

        for name, desc in appendices:
            kp = KnowledgePoint(name=name, description=desc, parent_id=root.id)
            db.session.add(kp)

        db.session.commit()
        print('[OK] 已导入："张宇基础30讲（高数）"板块')
        print('      - %d个主要章节 + %d个附录' % (len(lectures), len(appendices)))

        # 显示结构
        print('\n新增板块结构：')
        print('  [张宇基础30讲（高数）]')
        for c in KnowledgePoint.query.filter_by(parent_id=root.id).order_by(KnowledgePoint.name).all():
            print('    +-- %s' % c.name)

        print('\n[OK] 导入完成！')


if __name__ == '__main__':
    run()
