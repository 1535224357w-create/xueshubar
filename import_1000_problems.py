"""
导入 1000题 提取的题目到题目库
"""
import json, re, sys
from app import app, db
from models import Problem, KnowledgePoint


def parse_json_from_text(text):
    """从 Vision API 返回中提取 JSON（去掉 markdown 代码块标记）"""
    # 去掉 ```json 和 ``` 标记
    text = text.strip()
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()

    # 找第一个 { 和最后一个 }
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        return []
    json_str = text[start:end+1]
    try:
        data = json.loads(json_str)
        return data.get('problems', [])
    except json.JSONDecodeError as e:
        print(f'  JSON parse error: {e}')
        print(f'  Text snippet: {text[:200]}')
        return []


def estimate_difficulty(prob_type, knowledge_point=''):
    """根据题型和知识点估计难度"""
    if prob_type == '解答题':
        return 4
    elif prob_type == '选择题':
        return 3
    elif prob_type == '填空题':
        return 3
    return 3


def find_knowledge_point(kp_name, lecture_mapping):
    """根据知识点名称匹配知识树中的节点"""
    if not kp_name:
        return None
    kp_name = kp_name.strip()

    # 尝试直接匹配
    for kid, kname in lecture_mapping:
        if kp_name in kname or kname in kp_name:
            return kid

    # 模糊匹配关键词（映射到 lecture name 的子串）
    keywords = {
        '极限': '函数极限',
        '连续': '函数极限',
        '间断': '函数极限',
        '无穷小': '函数极限',
        '无穷大': '函数极限',
        '数列': '数列极限',
        '导数': '微分学的概念',
        '微分': '微分学的概念',
        '求导': '微分学的概念',
        '可导': '微分学的概念',
        '中值': '微分学的应用',
        '拉格朗日': '微分学的应用',
        '罗尔': '微分学的应用',
        '泰勒': '微分学的应用',
        '洛必达': '微分学的应用',
        '单调': '微分学的应用',
        '极值': '微分学的应用',
        '最值': '微分学的应用',
        '凹凸': '微分学的应用',
        '拐点': '微分学的应用',
        '渐近': '微分学的应用',
        '曲率': '微分学的应用',
        '不定积分': '积分学概念',
        '原函数': '积分学概念',
        '积分公式': '积分学概念',
        '定积分': '定积分',
        '换元': '定积分的计算',
        '分部积分': '定积分的计算',
        '面积': '定积分的应用',
        '体积': '定积分的应用',
        '弧长': '定积分的应用',
        '积分等': '定积分的应用',
        '积分不等': '定积分的应用',
        '参数方程': '定积分的应用',
        '极坐标': '定积分的应用',
        '多元': '多元函数微分学',
        '偏导': '多元函数微分学',
        '全微分': '多元函数微分学',
        '方向导数': '多元函数微分学',
        '梯度': '多元函数微分学应用',
        '拉格朗日乘数': '多元函数微分学应用',
        '条件极值': '多元函数微分学应用',
        '多元函数极': '多元函数微分学应用',
        '二重积分': '二重积分',
        '微分方程': '微分方程',
        '级数': '无穷级数',
        '收敛': '无穷级数',
        '幂级数': '无穷级数',
        '交错': '无穷级数',
        '充分条件': '函数极限',
        '必要条件': '函数极限',
        '充要条件': '函数极限',
        '数学归纳': '数列极限',
        '函数性质': '函数极限',
        '函数': '函数极限',
        '不等式': '函数极限',
        '切线': '微分学的概念',
        '法线': '微分学的概念',
        '微分方程解': '微分方程',
        '特解': '微分方程',
        '通解': '微分方程',
        '对称性': '二重积分',
        '旋转体': '定积分的应用',
        '平均值': '定积分的应用',
        '零点': '函数极限',
        '方程根': '函数极限',
    }

    for kw, lecture in keywords.items():
        if kw in kp_name:
            for kid, kname in lecture_mapping:
                if lecture in kname:
                    return kid
    return None


def run():
    with app.app_context():
        # 加载知识树映射（从 30讲 知识库）
        root = KnowledgePoint.query.filter_by(name='张宇基础30讲（高数）').first()
        if not root:
            print('Error: 张宇基础30讲（高数）知识节点不存在')
            return

        lectures = KnowledgePoint.query.filter_by(parent_id=root.id).order_by(KnowledgePoint.name).all()
        lecture_mapping = [(l.id, l.name) for l in lectures]
        print('可用知识点:')
        for lid, lname in lecture_mapping:
            print(f'  {lid}: {lname}')

        # 加载提取的题目数据
        with open(r'C:\Users\xbr\mathlearn\1000_problems_extracted.json', 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        total_imported = 0
        total_skipped = 0
        unmapped_kps = set()

        for batch_key, batch_text in raw_data.items():
            problems = parse_json_from_text(batch_text)
            if not problems:
                print(f'  [跳过] {batch_key}: 未解析到题目')
                continue

            for p in problems:
                pid = p.get('id', '').strip()
                content = p.get('content', '').strip()
                ptype = p.get('type', '').strip()
                options = p.get('options', '')
                if not isinstance(options, str):
                    options = str(options) if options else ''
                options = options.strip()
                kp_name = p.get('knowledge_point', '').strip()
                answer = p.get('answer', '').strip() if p.get('answer') else ''

                if not content:
                    total_skipped += 1
                    continue

                # 构建完整题目内容（含选项）
                full_content = content
                if options and options not in ('null', 'None', ''):
                    full_content += '\n' + options

                # 匹配知识点
                kp_id = find_knowledge_point(kp_name, lecture_mapping)
                if kp_id is None:
                    # 默认放到函数极限与连续
                    kp_id = lecture_mapping[0][0]
                    if kp_name:
                        unmapped_kps.add(kp_name)

                # 查重：检查是否已有相同内容的题目
                existing = Problem.query.filter_by(content=full_content[:200]).first()
                if existing:
                    total_skipped += 1
                    continue

                # 创建题目
                difficulty = estimate_difficulty(ptype, kp_name)
                prob = Problem(
                    content=full_content,
                    answer=answer,
                    difficulty=difficulty,
                    knowledge_point_id=kp_id,
                    source='system',
                    tags=ptype,
                )
                db.session.add(prob)
                total_imported += 1

            db.session.commit()

        print(f'\n=== 导入完成 ===')
        print(f'导入: {total_imported} 道题')
        print(f'跳过: {total_skipped} 道题')
        if unmapped_kps:
            print(f'\n未匹配的知识点 ({len(unmapped_kps)}):')
            for k in sorted(unmapped_kps)[:20]:
                print(f'  - {k}')


if __name__ == '__main__':
    run()
