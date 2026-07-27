"""
重新导入所有1000题题目，按正确知识点映射到 30讲 高数/线代/概率
"""
import json, re
from app import app, db
from models import Problem, KnowledgePoint


def run():
    with app.app_context():
        # 加载所有 30讲 知识节点
        kp_map = {}  # name -> id
        for root in KnowledgePoint.query.filter_by(parent_id=None).all():
            for child in root.children.all():
                kp_map[child.name] = child.id

        if not kp_map:
            print('Error: 知识树为空')
            return

        # 知识点关键词映射 (keyword -> lecture_name contains)
        KP_RULES = {
            # === 高数 ===
            '极限': '函数极限', '连续': '函数极限', '无穷小': '函数极限', '间断': '函数极限',
            '数列极限': '数列极限', '数列': '数列极限',
            '导数': '微分学的概念', '求导': '微分学的概念', '可导': '微分学的概念',
            '中值': '微分学的应用', '泰勒': '微分学的应用', '洛必达': '微分学的应用',
            '单调': '微分学的应用', '极值': '微分学的应用', '最值': '微分学的应用',
            '凹凸': '微分学的应用', '渐近': '微分学的应用', '曲率': '微分学的应用',
            '不定积分': '积分学概念', '原函数': '积分学概念',
            '定积分': '定积分', '换元': '定积分的计算', '分部积分': '定积分的计算',
            '面积': '定积分的应用', '体积': '定积分的应用', '弧长': '定积分的应用',
            '参数方程': '定积分的应用', '极坐标': '定积分的应用',
            '多元': '多元函数微分学', '偏导': '多元函数微分学', '全微分': '多元函数微分学',
            '梯度': '多元函数微分学应用', '拉格朗日乘': '多元函数微分学应用',
            '二重积分': '二重积分',
            '微分方程': '微分方程', '通解': '微分方程', '特解': '微分方程',
            '级数': '无穷级数', '收敛': '无穷级数', '幂级数': '无穷级数',
            # === 线代 ===
            '行列式': '行列式', '余子式': '行列式', '克拉默': '行列式',
            '矩阵': '矩阵', '逆矩阵': '矩阵', '伴随矩阵': '矩阵', '秩': '矩阵',
            '向量组': '向量组', '线性相关': '向量组', '线性无关': '向量组',
            '施密特': '向量组', '正交': '向量组', '向量': '向量组',
            '线性方程组': '线性方程组', '基础解系': '线性方程组', '通解': '线性方程组',
            '特征值': '特征值与特征向量', '特征向量': '特征值与特征向量',
            '相似': '特征值与特征向量', '对角化': '特征值与特征向量',
            '二次型': '二次型', '正定': '二次型', '标准形': '二次型',
            # === 概率 ===
            '概率': '随机事件与概率', '事件': '随机事件与概率',
            '古典概': '随机事件与概率', '条件概率': '随机事件与概率',
            '贝叶斯': '随机事件与概率', '全概率': '随机事件与概率',
            '分布函数': '一维随机变量', '分布律': '一维随机变量',
            '概率密度': '一维随机变量', '正态': '一维随机变量', '泊松': '一维随机变量',
            '二维': '多维随机变量及其分布', '联合分布': '多维随机变量及其分布',
            '边际': '多维随机变量及其分布', '独立': '多维随机变量及其分布',
            '期望': '随机变量的数字特征', '方差': '随机变量的数字特征',
            '协方差': '随机变量的数字特征', '相关系数': '随机变量的数字特征',
            '大数': '大数定理与中心极限定理', '中心极限': '大数定理与中心极限定理',
            '样本': '数理统计', '参数估计': '数理统计', '假设检验': '数理统计',
        }

        def find_kp(content):
            for kw, lecture_part in KP_RULES.items():
                if kw in content:
                    for lname, lid in kp_map.items():
                        if lecture_part in lname:
                            return lid
                    return None
            return None

        # 加载JSON
        with open(r'C:\Users\xbr\mathlearn\1000_problems_extracted.json', 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        first_lid = next(iter(kp_map.values()))
        imported = 0
        skipped = 0

        for batch_text in raw_data.values():
            text = batch_text.strip()
            for pfx in ['```json', '```']:
                if text.startswith(pfx):
                    text = text[len(pfx):]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            start, end = text.find('{'), text.rfind('}')
            if start < 0 or end < 0:
                continue
            try:
                data = json.loads(text[start:end+1])
            except json.JSONDecodeError:
                continue

            for p in data.get('problems', []):
                content = (p.get('content') or '').strip()
                if not content:
                    skipped += 1
                    continue
                opt = p.get('options') or ''
                full = content + ('\n' + str(opt) if str(opt).strip() not in ('', 'None') else '')
                if Problem.query.filter_by(content=full[:200]).first():
                    skipped += 1
                    continue
                kp_id = find_kp(full) or first_lid
                diff = 4 if '解答' in str(p.get('type')) else 3
                db.session.add(Problem(content=full, difficulty=diff,
                                        knowledge_point_id=kp_id, source='system',
                                        tags=str(p.get('type', ''))))
                imported += 1

            db.session.commit()

        print(f'导入: {imported} 题')
        print(f'跳过: {skipped} 题')

        # 统计
        print('\n各知识点分布:')
        for lname, lid in sorted(kp_map.items(), key=lambda x: x[1]):
            cnt = Problem.query.filter_by(knowledge_point_id=lid).count()
            if cnt:
                print(f'  {lname}: {cnt} 题')


if __name__ == '__main__':
    run()
