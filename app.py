"""高等数学学习网站 - 主程序"""
import os, re, hmac, hashlib, base64
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, KnowledgePoint, Problem, UserWrongProblem


# ============ 激活码签名 ============
_CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # 去掉易混淆 I O U 0 1


def _sign_code_seed(seed):
    """用 HMAC-SHA256 对种子签名，返回 4 字符 base32 签名"""
    sig = hmac.new(
        app.config['SECRET_KEY'].encode(),
        seed.encode(),
        hashlib.sha256
    ).digest()[:3]  # 3 bytes → 24 bits → base32 编码后取前4字符
    return base64.b32encode(sig).decode('ascii')[:4]


def generate_activation_code():
    """生成带签名的激活码，格式 XXXX-XXXX-XXXX"""
    import secrets
    seed = ''.join(secrets.choice(_CODE_CHARS) for _ in range(8))
    sig = _sign_code_seed(seed)
    return f'{seed[:4]}-{seed[4:]}-{sig}'


def verify_code_signature(code):
    """验证激活码格式和签名
    - 新格式 XXXX-XXXX-XXXX：签名校验
    - 旧格式 XXXX-XXXX：跳过签名验证（兼容存量码）
    - 其他格式：拒绝
    """
    parts = code.split('-')
    valid_chars = set(_CODE_CHARS)
    def _valid(s): return len(s) == 4 and all(c in valid_chars for c in s)

    if len(parts) == 3:
        # 新格式：验证签名
        if _valid(parts[0]) and _valid(parts[1]) and _valid(parts[2]):
            seed = parts[0] + parts[1]
            return parts[2] == _sign_code_seed(seed)
        return False
    elif len(parts) == 2:
        # 旧格式 XXXX-XXXX：跳过签名验证（兼容存量码）
        return _valid(parts[0]) and _valid(parts[1])
    return False

# ============ 初始化应用 ============
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ============ 路由 - 首页 ============
@app.route('/')
def index():
    return render_template('index.html')

# ============ 路由 - 用户认证 ============
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not username or not email or not password:
            flash('请填写所有字段')
            return render_template('register.html')
        if len(password) < 8:
            flash('密码至少 8 位')
            return render_template('register.html')

        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('注册成功，请登录')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'注册失败：{str(e)}')
            return render_template('register.html')

    return render_template('register.html')


@app.route('/api/health')
def health():
    return 'ok'


@app.route('/api/check-alipay')
def check_alipay():
    """检查支付宝配置状态"""
    import os
    ver = 'v3'  # 更新版本号时修改这里
    info = {
        'version': ver,
        'os_env': str(os.environ.get('ALIPAY_APP_ID', '空'))[:20],
        'has_private_key': bool(os.environ.get('ALIPAY_PRIVATE_KEY', '')),
    }
    return jsonify(info)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('用户名或密码错误')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ============ 路由 - 知识树 ============
@app.route('/knowledge')
def knowledge_tree():
    # 获取所有一级知识点（预计算所有数据，避免模板中懒加载 SQL）
    root_nodes_q = KnowledgePoint.query.filter_by(parent_id=None).all()
    root_nodes = []
    for cat in root_nodes_q:
        children = []
        for ch in cat.children.order_by(KnowledgePoint.name).all():
            children.append({
                'id': ch.id,
                'name': ch.name,
                'description': ch.description,
            })
        root_nodes.append({
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'children': children,
            'child_count': len(children),
        })
    total_chapters = sum(n['child_count'] for n in root_nodes)
    return render_template('knowledge/tree.html', root_nodes=root_nodes, total_chapters=total_chapters)

@app.route('/api/knowledge/<int:kp_id>/children')
def get_knowledge_children(kp_id):
    kp = db.session.get(KnowledgePoint, kp_id)
    if not kp:
        return jsonify({'error': 'not found'}), 404
    return jsonify({
        'point': kp.to_dict(),
        'children': [c.to_dict() for c in kp.children.all()],
        'problem_count': kp.problems.count(),
    })

# ============ 路由 - 题目库 ============
@app.route('/problems')
def problem_list():
    kp_id = request.args.get('kp_id', type=int)
    difficulty = request.args.get('difficulty', type=int)
    query = Problem.query.filter_by(source='system')

    if kp_id:
        query = query.filter_by(knowledge_point_id=kp_id)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)

    problems = query.order_by(Problem.created_at.desc()).all()
    knowledge_points = KnowledgePoint.query.all()
    return render_template('problems/list.html', problems=problems, knowledge_points=knowledge_points)

@app.route('/problems/<int:problem_id>')
def problem_detail(problem_id):
    problem = db.session.get(Problem, problem_id)
    if not problem:
        flash('题目不存在')
        return redirect(url_for('problem_list'))
    return render_template('problems/detail.html', problem=problem)

# ============ 路由 - 上传错题 ============
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_problem():
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            flash('请输入题目内容')
            return render_template('problems/upload.html')

        # 非 VIP 用户检查每日上传次数限制
        if not current_user.is_vip:
            from datetime import date
            today = date.today()
            if current_user.upload_date != today:
                current_user.upload_count_today = 0
                current_user.upload_date = today
                db.session.commit()
            if current_user.upload_count_today >= 3:
                flash('免费用户每天只能上传 3 道题，开通会员可无限上传')
                return redirect(url_for('vip_page'))

        # 查重：如果内容相似的题已经在错题本中，不再重复添加
        norm = content.strip().lower().replace(' ', '')
        existing_ids = set()
        for r in UserWrongProblem.query.filter_by(user_id=current_user.id):
            if r.problem and r.problem.content.strip().lower().replace(' ', '') == norm:
                existing_ids.add(r.problem_id)
        if existing_ids:
            pid = existing_ids.pop()
            flash('这道题已经在你的错题本中了')
            return redirect(url_for('problem_detail', problem_id=pid))

        # 先创建一个临时题目记录
        new_problem = Problem(
            content=content,
            knowledge_point_id=1,  # 临时，AI 会分析后更新
            source='user_upload',
            creator_id=current_user.id,
        )
        db.session.add(new_problem)
        db.session.flush()  # 获取 ID

        # 用 AI 分析知识点（如果有 API Key 的话）
        api_key = app.config.get('DEEPSEEK_API_KEY', '')
        if api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=app.config['DEEPSEEK_BASE_URL'])
                response = client.chat.completions.create(
                    model=app.config['DEEPSEEK_MODEL'],
                    max_tokens=1000,
                    messages=[{
                        "role": "user",
                        "content": (
                            "分析下面这道高等数学题属于哪个知识点。\n\n"
                            "已有的知识点列表（请从中选择最匹配的，返回其 ID）：\n"
                            + get_knowledge_tree_text() + "\n\n"
                            "题目：\n" + content + "\n\n"
                            "请按以下格式返回（JSON格式，只返回纯 JSON 不要其他文字）：\n"
                            '{"knowledge_point_id": 数字, "explanation": "解析", "tags": []}'
                        )
                    }]
                )
                # 解析 AI 返回
                import json
                import re
                text = response.choices[0].message.content
                # 尝试提取 JSON
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    if 'knowledge_point_id' in data:
                        kp = db.session.get(KnowledgePoint, data['knowledge_point_id'])
                        if kp:
                            new_problem.knowledge_point_id = kp.id
                    if 'explanation' in data:
                        new_problem.explanation = data['explanation']
                    if 'tags' in data:
                        new_problem.tags = ','.join(data['tags'])
            except Exception as e:
                flash(f'AI 分析出错：{str(e)}，题目已保存但未分析知识点')

        # 也加入用户的错题本
        wrong = UserWrongProblem(
            user_id=current_user.id,
            problem_id=new_problem.id,
            user_answer=request.form.get('user_answer', ''),
            note=request.form.get('note', ''),
        )
        db.session.add(wrong)
        db.session.commit()

        # 生成解题分析
        answer_text = None
        solution = None
        ds_key = app.config.get('DEEPSEEK_API_KEY', '')
        if ds_key:
                from openai import OpenAI
                sol_client = OpenAI(api_key=ds_key, base_url=app.config['DEEPSEEK_BASE_URL'])
                try:
                    resp = sol_client.chat.completions.create(
                    model='deepseek-chat',
                    max_tokens=2048,
                    timeout=60,
                    messages=[{
                        'role': 'user',
                        'content': '解答：' + content + '\n\n最后一行写 【答案】'
                    }]
                    )
                    full = resp.choices[0].message.content
                    solution = None
                    answer_text = None
                    if full and full.strip():
                        from plot_engine import extract_plots, render_from_json
                        plots = extract_plots(full)
                        for obj, tag in plots:
                            img_b64 = render_from_json(obj)
                            if img_b64:
                                    img_html = '<img src="data:image/png;base64,' + img_b64 + '" style="max-height:350px">'
                                    full = full.replace(tag, img_html)
                            else:
                                    full = full.replace(tag, '')
                        # 清理残留的 PLOT 指令
                        import re
                        full = re.sub(r'【PLOT】.*?【/PLOT】', '', full)
                        if '【答案】' in full:
                            parts = full.split('【答案】')
                            solution = parts[0].strip()
                            answer_text = '【答案】' + parts[1].strip()
                        else:
                            solution = full
                except Exception:
                    pass

        # 更新上传计数
        if not current_user.is_vip:
            current_user.upload_count_today += 1

        # 保存 AI 生成的答案和解析到题目记录（清理残留指令）
        if solution:
            import re
            clean_solution = re.sub(r'【PLOT】.*?【/PLOT】', '', solution)
            new_problem.explanation = clean_solution[:2000]
        if answer_text:
            new_problem.answer = answer_text[:500]
        db.session.commit()

        # 查找相似题
        similar = find_similar_problems(new_problem)
        return render_template('problems/upload_result.html', problem=new_problem, similar=similar,
                               answer_text=answer_text, solution=solution)

    knowledge_points = KnowledgePoint.query.all()
    initial_content = request.args.get('content', '')
    return render_template('problems/upload.html', knowledge_points=knowledge_points, initial_content=initial_content)


# ============ 路由 - 拍照上传错题 ============
@app.route('/upload-photo', methods=['GET', 'POST'])
@login_required
def upload_photo():
    """拍照上传"""
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            flash('请先拍照并识别题目')
            return render_template('problems/upload_photo.html')

        # 把识别的结果提交到现有上传流程
        # 用 session 传参或直接转发
        return redirect(url_for('upload_problem', content=content))

    return render_template('problems/upload_photo.html')


# ============ API - OCR 识别图片中的数学题 ============
@app.route('/api/ocr', methods=['POST'])
@login_required
def ocr_problem():
    """多引擎OCR识别数学题 - 图像预处理 + 多引擎 + AI修复"""
    if 'image' not in request.files:
        return jsonify({'error': '请上传图片', 'text': ''}), 400

    file = request.files['image']
    if not file.filename:
        return jsonify({'error': '请选择图片', 'text': ''}), 400

    import tempfile, os
    ext = os.path.splitext(file.filename)[1] or '.jpg'
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    file.save(tmp.name)
    tmp.close()

    try:
        with open(tmp.name, 'rb') as f:
            img_data = f.read()

        # 第一步：优先使用 Claude 视觉模型（最准、最便宜）
        # 注意：claude_vision 内部已自动压缩图片防止 context 超限
        claude_key = app.config.get('ANTHROPIC_API_KEY', '')
        if claude_key:
            try:
                from claude_vision import recognize_math_problem
                text, _ = recognize_math_problem(img_data, claude_key,
                                                  model=app.config['CLAUDE_MODEL'])
                return jsonify({'text': text, 'raw_ocr': text[:100], 'success': True})
            except Exception as e:
                err_msg = str(e)
                if 'context length' in err_msg.lower() or 'maximum' in err_msg.lower():
                    # 上下文超限：用更小的图片再试一次
                    try:
                        from claude_vision import _compress_image
                        compressed, _ = _compress_image(img_data, max_size=(600, 600), quality=60)
                        text, _ = recognize_math_problem(compressed, claude_key,
                                                          model=app.config['CLAUDE_MODEL'])
                        return jsonify({'text': text, 'raw_ocr': text[:100], 'success': True})
                    except Exception:
                        pass
                # 其他失败，回退到百度OCR

        # 第二步：回退到百度OCR + DeepSeek
        bd_key = app.config.get('BAIDU_OCR_API_KEY', '')
        bd_secret = app.config.get('BAIDU_OCR_SECRET_KEY', '')
        if not bd_key or not bd_secret:
            return jsonify({'error': '未配置API（请配置 ANTHROPIC_API_KEY 或 BAIDU_OCR）', 'text': ''}), 400

        # 图像预处理
        try:
            from image_utils import preprocess_for_baidu
            enhanced = preprocess_for_baidu(img_data)
        except ImportError:
            enhanced = img_data

        from baidu_ocr import recognize_general, recognize_formula
        ocr_text, raw_resp, _ = recognize_general(enhanced, bd_key, bd_secret, preprocess=False)
        raw_ocr = ocr_text

        if len(ocr_text.strip()) < 5:
            try:
                formula_text, _, _ = recognize_formula(enhanced, bd_key, bd_secret, preprocess=False)
                if formula_text and len(formula_text) > len(ocr_text):
                    ocr_text = formula_text
                    raw_ocr = formula_text
            except Exception:
                pass

        if not ocr_text.strip():
            return jsonify({'error': '未能识别出文字', 'text': ''}), 400

        # DeepSeek 整理成中文
        ds_key = app.config.get('DEEPSEEK_API_KEY', '')
        if ds_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=ds_key, base_url=app.config['DEEPSEEK_BASE_URL'])
                prompt_msg = (
                    "你是一位数学老师。OCR从一张数学题图片中识别出了以下文字，请把它还原成完整的数学题。\n\n"
                    "OCR结果：\n" + ocr_text + "\n\n"
                    "要求：\n"
                    "1. 保留题目原本的数学结构，包括公式\n"
                    "2. 数学公式用LaTeX格式，用一对$括起来\n"
                    "3. 如果是中文题目，保留中文\n"
                    "4. 只输出还原后的题目本身，不要解释不要多余文字\n"
                    "5. 如果OCR结果明显有误，根据数学知识推测正确的题目"
                )
                resp = client.chat.completions.create(
                    model=app.config['DEEPSEEK_MODEL'],
                    max_tokens=500,
                    messages=[{'role': 'user', 'content': prompt_msg}]
                )
                text = resp.choices[0].message.content.strip()
            except Exception as e:
                text = ocr_text
        else:
            text = ocr_text

        return jsonify({
            'text': text,
            'raw_ocr': raw_ocr[:200],
            'engine_used': engine_used,
            'success': True
        })

    except Exception as e:
        return jsonify({'error': f'识别出错：{str(e)}', 'text': ''}), 500
    finally:
        os.unlink(tmp.name)


# ============ API - 生成解题分析（独立调用，不影响上传） ============
@app.route('/api/solution', methods=['POST'])
@login_required
def api_solution():
    """接收题目文本，返回 DeepSeek 生成的多解法解题分析"""
    content = request.json.get('content', '') if request.is_json else request.form.get('content', '')
    if not content:
        return jsonify({'error': '请输入题目', 'solution': None}), 400

    from solution_service import generate_solution
    solution = generate_solution(
        content,
        app.config.get('DEEPSEEK_API_KEY', ''),
        app.config['DEEPSEEK_BASE_URL']
    )
    return jsonify({'solution': solution})


# ============ 意见反馈 ============
@app.route('/api/feedback', methods=['POST'])
def feedback():
    """接收用户反馈并发送邮件"""
    data = request.get_json()
    content = data.get('content', '').strip() if data else ''
    if not content:
        return jsonify({'success': False}), 400

    try:
        import smtplib, ssl
        from email.message import EmailMessage

        smtp_host = app.config.get('SMTP_HOST', '')
        smtp_port = app.config.get('SMTP_PORT', 587)
        smtp_user = app.config.get('SMTP_USER', '')
        smtp_pass = app.config.get('SMTP_PASS', '')

        if not smtp_host or not smtp_user or not smtp_pass:
            return jsonify({'success': False, 'error': 'SMTP 未配置'}), 500

        msg = EmailMessage()
        msg.set_content(content)
        msg['Subject'] = f'学数 bar 用户反馈'
        msg['From'] = smtp_user
        msg['To'] = '1535224357@qq.com'

        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls(context=ctx)
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        if smtp_host and smtp_user and smtp_pass:
            import ssl
            ctx = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls(context=ctx)
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        # 未配置SMTP时记录日志
        else:
            with open('feedback.log', 'a', encoding='utf-8') as f:
                f.write(f'[反馈] {content}\n')

        return jsonify({'success': True})
    except Exception as e:
        print(f'[反馈错误] {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ 会员中心 ============
@app.route('/vip')
def vip_page():
    return render_template('vip.html')


@app.route('/api/vip/create-order', methods=['POST'])
@login_required
def create_order():
    """创建支付订单"""
    data = request.get_json()
    plan = data.get('plan', '') if data else ''
    if plan not in ('monthly', 'quarterly', 'yearly'):
        return jsonify({'error': '无效的套餐'}), 400

    # 套餐定价（分）
    prices = {'monthly': 1990, 'quarterly': 4990, 'yearly': 9900}
    amount = prices[plan]

    # 创建本地订单
    from models import Order
    import uuid
    order = Order(
        user_id=current_user.id,
        plan=plan,
        amount=amount,
    )
    db.session.add(order)
    db.session.flush()

    # 构造支付订单号
    out_trade_no = f'XS{order.id:06d}{uuid.uuid4().hex[:8]}'

    # 支付宝当面付（直接 API 调用，不依赖 SDK）
    try:
        import os
        app_dir = os.path.dirname(__file__)

        # 读取私钥
        private_key_raw = os.getenv('ALIPAY_PRIVATE_KEY', '')
        if private_key_raw:
            import base64
            try:
                private_key_bytes = base64.b64decode(private_key_raw)
                private_key = private_key_bytes.decode('utf-8')
            except:
                private_key = private_key_raw
                if '\\n' in private_key:
                    private_key = private_key.replace('\\n', '\n')
        else:
            with open(os.path.join(app_dir, 'alipay_private_key.pem')) as f:
                private_key = f.read()

        from alipay_direct import create_qr_code
        qr_code, error = create_qr_code(
            app_id='2021006167668054',
            private_key=private_key,
            out_trade_no=out_trade_no,
            total_amount=amount / 100,
            subject='学数 bar VIP',
            notify_url='https://xueshubar.onrender.com/api/alipay/notify'
        )
        if qr_code:
            order.payjs_order_id = out_trade_no
            db.session.commit()
            return jsonify({'qrcode': qr_code, 'order_id': order.id})
        else:
            print(f'[支付宝] 失败: {error}')
    except Exception as e:
        print(f'[支付宝] 异常: {e}')

    # 未配置支付宝时返回模拟二维码
    order.payjs_order_id = 'sim_' + out_trade_no
    db.session.commit()

    import base64
    qr_data = f'pay:sim:{out_trade_no}'
    qr_b64 = base64.b64encode(qr_data.encode()).decode()
    fake_qr = f'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_b64}'

    return jsonify({'qrcode': fake_qr, 'order_id': order.id})


# ============ 支付宝回调通知 ============
@app.route('/api/alipay/notify', methods=['POST'])
def alipay_notify():
    """支付宝支付结果回调"""
    from alipay import AliPay
    import os
    try:
        app_dir = os.path.dirname(__file__)
        private_key = os.getenv('ALIPAY_PRIVATE_KEY', '')
        if not private_key:
            with open(os.path.join(app_dir, 'alipay_private_key.pem')) as f:
                private_key = f.read()
        if private_key and '-----' not in private_key[:50]:
            if '\\n' in private_key:
                private_key = private_key.replace('\\n', '\n')
            if '\n' not in private_key:
                import textwrap
                b64 = private_key.strip()
                private_key = '-----BEGIN RSA PRIVATE KEY-----\n'
                private_key += '\n'.join(textwrap.wrap(b64, 64))
                private_key += '\n-----END RSA PRIVATE KEY-----'
        with open(os.path.join(app_dir, 'alipay_public_key.pem')) as f:
            public_key = f.read()

        alipay = AliPay(
            appid='2021006167668054',
            app_notify_url='',
            app_private_key_string=private_key,
            alipay_public_key_string=public_key,
            sign_type='RSA2',
        )

        data = request.form.to_dict()
        signature = data.pop('sign', '')
        if alipay.verify(data, signature):
            out_trade_no = data.get('out_trade_no', '')
            trade_status = data.get('trade_status', '')
            if trade_status == 'TRADE_SUCCESS' and out_trade_no:
                from models import Order
                order = Order.query.filter_by(payjs_order_id=out_trade_no).first()
                if order and order.status == 'pending':
                    from datetime import datetime, timezone, timedelta
                    order.status = 'paid'
                    order.paid_at = datetime.now(timezone.utc)
                    durations = {'monthly': 30, 'quarterly': 90, 'yearly': 365}
                    days = durations.get(order.plan, 30)
                    user = db.session.get(__import__('models').User, order.user_id)
                    if user:
                        if user.vip_expiry and user.vip_expiry > datetime.now(timezone.utc):
                            user.vip_expiry += timedelta(days=days)
                        else:
                            user.vip_expiry = datetime.now(timezone.utc) + timedelta(days=days)
                    db.session.commit()
        return 'success'
    except Exception:
        return 'fail'


# ============ 学习报告 ============
@app.route('/report')
@login_required
def report_page():
    """学习报告页面"""
    if not current_user.is_vip:
        flash('学习报告仅限会员使用')
        return redirect(url_for('vip_page'))

    records = UserWrongProblem.query.filter_by(user_id=current_user.id).order_by(UserWrongProblem.created_at.desc()).all()
    total = len(records)
    correct = 0
    kp_data = {}
    for r in records:
        if r.problem and r.problem.knowledge_point:
            kp = r.problem.knowledge_point.name
            if kp not in kp_data:
                kp_data[kp] = {'total': 0}
            kp_data[kp]['total'] += 1
        if r.id % 3 == 0:  # 模拟部分正确
            correct += 1

    accuracy = correct / total if total > 0 else 0
    days = max(1, (records[-1].created_at - records[0].created_at).days + 1 if len(records) > 1 else 1)

    # 知识点统计
    kp_stats = []
    for name, data in kp_data.items():
        acc = min(1.0, data['total'] * 0.4 + 0.3)
        kp_stats.append({'name': name, 'accuracy': acc})

    # 获取已保存的报告
    report = None
    try:
        from models import Report
        last_report = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).first()
        if last_report:
            report = last_report.content
    except:
        pass

    return render_template('report.html', total=total, correct=correct, accuracy=accuracy,
                           days=days, kp_stats=kp_stats, report=report)


@app.route('/api/report/generate', methods=['POST'])
@login_required
def generate_report():
    """AI 生成学习报告"""
    if not current_user.is_vip:
        return jsonify({'error': '仅限会员'}), 403

    records = UserWrongProblem.query.filter_by(user_id=current_user.id).order_by(UserWrongProblem.created_at.desc()).all()
    if not records:
        return jsonify({'error': '暂无数据'}), 400

    total = len(records)
    kp_summary = {}
    for r in records:
        if r.problem and r.problem.knowledge_point:
            kp = r.problem.knowledge_point.name
            kp_summary[kp] = kp_summary.get(kp, 0) + 1

    ds_key = app.config.get('DEEPSEEK_API_KEY', '')
    if not ds_key:
        return jsonify({'error': 'AI 未配置'}), 500

    try:
        from openai import OpenAI
        client = OpenAI(api_key=ds_key, base_url=app.config['DEEPSEEK_BASE_URL'])
        resp = client.chat.completions.create(
            model='deepseek-chat',
            max_tokens=1500,
            timeout=60,
            messages=[{
                'role': 'user',
                'content': (
                    '你是一个数学学习分析助手。根据以下学习数据生成个性化报告。\n\n'
                    f'总做题量：{total}\n'
                    f'涉及知识点：{", ".join(kp_summary.keys())}\n'
                    f'各知识点做题分布：{str(kp_summary)}\n\n'
                    '请按以下格式输出，不要用Markdown：\n'
                    '【学习概况】\n...\n'
                    '【薄弱知识点】\n...\n'
                    '【学习建议】\n...\n'
                    '【下一步计划】\n...'
                )
            }]
        )
        report_text = resp.choices[0].message.content

        # 保存报告
        try:
            from models import Report
            from datetime import datetime, timezone
            r = Report(user_id=current_user.id, content=report_text)
            db.session.add(r)
            db.session.commit()
        except:
            pass

        return jsonify({'report': report_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ AI 追问 ============
@app.route('/api/ask', methods=['POST'])
@login_required
def ask_ai():
    """AI 对话式追问：DeepSeek 先验答案 → Claude 教学引导"""
    if not current_user.is_vip:
        return jsonify({'error': '会员专享'}), 403
    data = request.get_json()
    question = data.get('question', '').strip() if data else ''
    context = data.get('context', '') if data else ''
    if not question:
        return jsonify({'error': '请输入问题'}), 400

    from openai import OpenAI
    ds_key = app.config.get('DEEPSEEK_API_KEY', '')
    claude_key = app.config.get('ANTHROPIC_API_KEY', '')
    if not ds_key or not claude_key:
        return jsonify({'error': 'AI 未完全配置'}), 500

    try:
        # 第一步：DeepSeek 给出正确答案
        ds_client = OpenAI(api_key=ds_key, base_url=app.config['DEEPSEEK_BASE_URL'])
        ds_resp = ds_client.chat.completions.create(
            model='deepseek-chat',
            max_tokens=500,
            timeout=20,
            messages=[{
                'role': 'user',
                'content': f'请解答这道数学题，给出最终答案。\n题目：{context}\n问题：{question}'
            }]
        )
        correct_answer = ds_resp.choices[0].message.content.strip()

        # 第二步：Claude 参考正确答案进行教学引导
        claude_client = OpenAI(api_key=claude_key, base_url=app.config['ANTHROPIC_BASE_URL'])
        claude_resp = claude_client.chat.completions.create(
            model='claude-haiku-4-5',
            max_tokens=1000,
            timeout=30,
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': (
                        '你是一个耐心的高等数学辅导老师。用中文回答学生的问题。\n\n'
                        f'题目：{context}\n'
                        f'学生问：{question}\n\n'
                        f'【参考答案（DeepSeek验证）】\n{correct_answer}\n\n'
                        '教学要求：\n'
                        '1. 参考答案已确认正确，你不需要重新计算\n'
                        '2. 用引导式教学，先给提示让学生自己思考\n'
                        '3. 如果学生明显困惑，再给出逐步解释\n'
                        '4. 不要直接说"根据参考答案"，用你自己的话讲解'
                    )}
                ]
            }]
        )
        # 清理 markdown 符号
        answer = claude_resp.choices[0].message.content
        answer = re.sub(r'[*_#>`~\\]', '', answer)
        answer = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', answer)
        answer = re.sub(r'\n{3,}', '\n\n', answer)
        return jsonify({'answer': answer.strip()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ 周错题集 & 月测试题 ============
@app.route('/review')
@login_required
def review_page():
    """错题回顾与测试"""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    # 最近7天的错题
    week_ago = now - timedelta(days=7)
    weekly = UserWrongProblem.query.filter_by(user_id=current_user.id)\
        .filter(UserWrongProblem.created_at >= week_ago)\
        .order_by(UserWrongProblem.created_at.desc()).all()

    # 最近30天的错题
    month_ago = now - timedelta(days=30)
    monthly = UserWrongProblem.query.filter_by(user_id=current_user.id)\
        .filter(UserWrongProblem.created_at >= month_ago).all()

    # 薄弱知识点统计
    weak_kps = {}
    for r in monthly:
        if r.problem and r.problem.knowledge_point:
            kp = r.problem.knowledge_point.name
            weak_kps[kp] = weak_kps.get(kp, 0) + 1
    weak_kps = sorted(weak_kps.items(), key=lambda x: x[1], reverse=True)

    return render_template('review.html', weekly=weekly, monthly=len(monthly), weak_kps=weak_kps)


@app.route('/api/review/generate-test', methods=['POST'])
@login_required
def generate_test():
    """根据薄弱知识点生成月测试题"""
    if not current_user.is_vip:
        return jsonify({'error': '会员专享'}), 403

    from datetime import datetime, timezone, timedelta
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    records = UserWrongProblem.query.filter_by(user_id=current_user.id)\
        .filter(UserWrongProblem.created_at >= month_ago).all()

    # 统计薄弱知识点
    weak = {}
    for r in records:
        if r.problem and r.problem.knowledge_point:
            kp = r.problem.knowledge_point.name
            weak[kp] = weak.get(kp, 0) + 1
    top_kps = [k for k, v in sorted(weak.items(), key=lambda x: x[1], reverse=True)[:3]]

    # 从题库找相似题
    test_problems = []
    seen = set()
    for kp_name in top_kps:
        kp = KnowledgePoint.query.filter_by(name=kp_name).first()
        if kp:
            problems = Problem.query.filter_by(knowledge_point_id=kp.id, source='system')\
                .order_by(Problem.difficulty).limit(3).all()
            for p in problems:
                if p.id not in seen:
                    test_problems.append(p)
                    seen.add(p.id)

    # 生成试卷
    import json
    from markdown import markdown
    result = []
    for i, p in enumerate(test_problems):
        result.append({
            'num': i + 1,
            'content': p.content,
            'answer': p.answer or '见解析',
            'kp': p.knowledge_point.name if p.knowledge_point else '综合',
            'difficulty': p.difficulty,
        })

    return jsonify({'problems': result, 'total': len(result), 'weak_areas': top_kps})


# ============ 删除错题记录 ============
@app.route('/api/wrong/delete/<int:record_id>', methods=['POST'])
@login_required
def delete_wrong(record_id):
    """从错题本删除一条记录"""
    from models import UserWrongProblem
    rec = db.session.get(UserWrongProblem, record_id)
    if not rec or rec.user_id != current_user.id:
        return jsonify({'error': '无权限'}), 403
    db.session.delete(rec)
    db.session.commit()
    return jsonify({'success': True})


# ============ 刷题模式 ============
@app.route('/practice')
@login_required
def practice_page():
    kps = KnowledgePoint.query.order_by(KnowledgePoint.name).all()
    return render_template('practice.html', knowledge_points=kps)


@app.route('/api/practice/start')
@login_required
def practice_start():
    """获取刷题题目列表"""
    kp_id = request.args.get('kp_id', type=int)
    diff = request.args.get('difficulty', type=int)
    limit = min(request.args.get('limit', 10, type=int), 50)

    q = Problem.query.filter_by(source='system')
    if kp_id:
        q = q.filter_by(knowledge_point_id=kp_id)
    if diff:
        q = q.filter_by(difficulty=diff)

    problems = q.order_by(db.func.random()).limit(limit).all()
    return jsonify({'problems': [{
        'id': p.id,
        'content': p.content,
        'difficulty': p.difficulty,
        'kp_name': p.knowledge_point.name if p.knowledge_point else '综合',
    } for p in problems]})


@app.route('/api/practice/check', methods=['POST'])
@login_required
def practice_check():
    """AI 判题"""
    data = request.get_json()
    pid = data.get('problem_id') if data else None
    user_answer = (data.get('user_answer') or '').strip() if data else ''

    problem = db.session.get(Problem, pid) if pid else None
    if not problem:
        return jsonify({'correct': False, 'analysis': '题目不存在'})

    ds_key = app.config.get('DEEPSEEK_API_KEY', '')
    if not ds_key:
        return jsonify({'correct': False, 'analysis': 'AI 未配置'})

    try:
        from openai import OpenAI
        client = OpenAI(api_key=ds_key, base_url=app.config['DEEPSEEK_BASE_URL'])
        resp = client.chat.completions.create(
            model='deepseek-chat',
            max_tokens=600,
            timeout=20,
            messages=[{
                'role': 'user',
                'content': f'题目：{problem.content}\n标准答案：{problem.answer}\n学生答案：{user_answer}\n\n判断学生答案是否正确，给出分析。用以下JSON格式输出：\n{{"correct": true/false, "analysis": "分析"}}'
            }]
        )
        import json, re
        text = resp.choices[0].message.content
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            d = json.loads(m.group())
            return jsonify({'correct': d.get('correct', False), 'analysis': d.get('analysis', '')})
    except: pass
    return jsonify({'correct': False, 'analysis': '判题失败'})


@app.route('/api/practice/add-wrong', methods=['POST'])
@login_required
def practice_add_wrong():
    """刷题后加入错题本"""
    data = request.get_json()
    pid = data.get('problem_id') if data else None
    ans = (data.get('user_answer') or '').strip() if data else ''
    problem = db.session.get(Problem, pid) if pid else None
    if not problem:
        return jsonify({'msg': '题目不存在'})

    # 查重
    for r in UserWrongProblem.query.filter_by(user_id=current_user.id):
        if r.problem_id == pid:
            return jsonify({'msg': '已在错题本中'})

    w = UserWrongProblem(user_id=current_user.id, problem_id=pid, user_answer=ans)
    db.session.add(w)
    db.session.commit()
    return jsonify({'msg': '已加入错题本'})


# ============ 激活码系统 ============
@app.route('/api/vip/activate', methods=['POST'])
@login_required
def activate_code():
    """使用激活码开通 VIP"""
    data = request.get_json()
    code_str = data.get('code', '').strip().upper() if data else ''
    if not code_str:
        return jsonify({'success': False, 'msg': '请输入激活码'}), 400

    from models import ActivationCode
    from datetime import datetime, timezone, timedelta

    # 先校验签名/格式
    if not verify_code_signature(code_str):
        return jsonify({'success': False, 'msg': '激活码格式无效'})

    ac = ActivationCode.query.filter_by(code=code_str).first()
    if not ac:
        return jsonify({'success': False, 'msg': '激活码不存在'})
    if ac.is_used:
        return jsonify({'success': False, 'msg': '该激活码已被使用'})

    # 激活
    ac.is_used = True
    ac.used_by = current_user.id
    ac.used_at = datetime.now(timezone.utc)

    durations = {'monthly': 30, 'quarterly': 90, 'yearly': 365}
    days = durations.get(ac.plan, 30)
    if current_user.vip_expiry and current_user.vip_expiry > datetime.now(timezone.utc):
        current_user.vip_expiry += timedelta(days=days)
    else:
        current_user.vip_expiry = datetime.now(timezone.utc) + timedelta(days=days)
    db.session.commit()
    return jsonify({'success': True, 'msg': f'VIP 已开通，有效期至 {current_user.vip_expiry.strftime("%Y-%m-%d")}'})


@app.route('/admin-codes')
@login_required
def admin_codes():
    """激活码管理页面"""
    if current_user.id != 1:
        flash('无权限')
        return redirect(url_for('index'))
    return render_template('admin_codes.html')


@app.route('/api/admin/gen-code', methods=['POST'])
@login_required
def gen_code():
    """生成激活码（仅管理员）"""
    if current_user.id != 1:
        return jsonify({'error': '无权限'}), 403
    data = request.get_json()
    plan = data.get('plan', 'monthly') if data else 'monthly'
    count = min(data.get('count', 1) if data else 1, 50)

    from models import ActivationCode
    import secrets
    codes = []
    for _ in range(count):
        code = generate_activation_code()  # 带签名的 XXXX-XXXX-XXXX 格式
        ac = ActivationCode(code=code, plan=plan, created_by=current_user.id)
        db.session.add(ac)
        codes.append(code)
    db.session.commit()
    return jsonify({'codes': codes})


@app.route('/api/admin/seed-problems', methods=['POST'])
@login_required
def seed_1000_problems():
    """远程导入1000题题目（仅管理员）"""
    if current_user.id != 1:
        return jsonify({'error': '无权限'}), 403

    import json, re, os

    json_path = os.path.join(os.path.dirname(__file__), '1000_problems_extracted.json')
    if not os.path.exists(json_path):
        return jsonify({'error': '种子数据文件不存在'})

    with open(json_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # 知识点映射
    KP_KW = {
        '极限': '函数极限', '连续': '函数极限', '无穷小': '函数极限', '数列': '数列极限',
        '导数': '微分学的概念', '求导': '微分学的概念', '可导': '微分学的概念', '微分': '微分学的概念',
        '中值': '微分学的应用', '泰勒': '微分学的应用', '洛必达': '微分学的应用',
        '单调': '微分学的应用', '极值': '微分学的应用', '最值': '微分学的应用', '凹凸': '微分学的应用',
        '渐近': '微分学的应用', '曲率': '微分学的应用',
        '不定积分': '积分学概念', '原函数': '积分学概念',
        '定积分': '定积分', '换元': '定积分的计算', '分部积分': '定积分的计算',
        '面积': '定积分的应用', '体积': '定积分的应用', '弧长': '定积分的应用',
        '参数方程': '定积分的应用', '极坐标': '定积分的应用',
        '多元': '多元函数微分学', '偏导': '多元函数微分学', '全微分': '多元函数微分学',
        '二重积分': '二重积分',
        '微分方程': '微分方程', '通解': '微分方程', '特解': '微分方程',
        '级数': '无穷级数', '收敛': '无穷级数',
        '向量': '向量', '矩阵': '矩阵', '行列式': '行列式',
        '特征': '特征值与特征向量', '二次型': '二次型', '线性方程组': '线性方程组',
        '概率': '随机事件与概率', '事件': '随机事件与概率', '分布': '一维随机变量',
        '期望': '随机变量的数字特征', '方差': '随机变量的数字特征',
        '正态': '一维随机变量', '参数估计': '参数估计', '假设检验': '参数估计',
    }

    root30 = KnowledgePoint.query.filter_by(name='张宇基础30讲（高数）').first()
    lectures30 = {}
    if root30:
        for l in root30.children.all():
            lectures30[l.name] = l.id

    # 匹配知识点ID
    def find_kp(content):
        for kw, area in KP_KW.items():
            if kw in content:
                # 先在30讲里找
                for lname, lid in lectures30.items():
                    if area in lname:
                        return lid
                # 再到660树里找
                kp = KnowledgePoint.query.filter(KnowledgePoint.name.contains(area)).first()
                if kp:
                    return kp.id
        return None

    imported = 0
    skipped = 0

    for batch_key, batch_text in raw_data.items():
        text = batch_text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1:
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
            kp_id = find_kp(full) or (list(lectures30.values())[0] if lectures30 else None)
            diff = 4 if '解答' in str(p.get('type')) else 3
            tags = str(p.get('type', ''))
            db.session.add(Problem(content=full, difficulty=diff,
                                    knowledge_point_id=kp_id, source='system', tags=tags))
            imported += 1

    db.session.commit()
    return jsonify({'imported': imported, 'skipped': skipped})
def reset_admin_password():
    """重置管理员密码（仅开发调试用）"""
    try:
        from models import User
        user = db.session.get(User, 1)
        if user:
            new_pw = 'Admin123'
            user.set_password(new_pw)
            db.session.commit()
            return jsonify({'success': True, 'username': user.username, 'new_password': new_pw})
        return jsonify({'error': '管理员不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/reset-users', methods=['POST'])
@login_required
def reset_users():
    """清空所有用户数据（仅管理员，用于清理测试数据）"""
    if current_user.id != 1:
        return jsonify({'error': '无权限'}), 403
    try:
        db.session.execute(db.text('DELETE FROM orders'))
        db.session.execute(db.text('DELETE FROM user_wrong_problems'))
        db.session.execute(db.text('DELETE FROM activation_codes'))
        db.session.execute(db.text('DELETE FROM users'))
        db.session.execute(db.text('DELETE FROM problems WHERE source=\'user_upload\''))
        db.session.commit()
        return jsonify({'success': True})
    except Exception:
        db.session.rollback()
        return jsonify({'error': '失败'}), 500


@app.route('/api/vip/check-order')
@login_required
def check_order():
    """查询订单支付状态"""
    order_id = request.args.get('order_id', type=int)
    if not order_id:
        return jsonify({'status': 'error'}), 400

    from models import Order
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.id:
        return jsonify({'status': 'error'}), 404

    # 模拟支付：如果是模拟订单直接标记为已支付
    if order.status == 'pending' and order.payjs_order_id and order.payjs_order_id.startswith('sim_'):
        from datetime import datetime, timezone, timedelta
        order.status = 'paid'
        order.paid_at = datetime.now(timezone.utc)

        # 设置 VIP 有效期
        durations = {'monthly': 30, 'quarterly': 90, 'yearly': 365}
        days = durations.get(order.plan, 30)
        if current_user.vip_expiry and current_user.vip_expiry > datetime.now(timezone.utc):
            current_user.vip_expiry += timedelta(days=days)
        else:
            current_user.vip_expiry = datetime.now(timezone.utc) + timedelta(days=days)
        db.session.commit()

    return jsonify({'status': order.status})


# ============ 相似题推荐 ============
def find_similar_problems(problem, limit=5):
    """查找相似题（按知识点 + 内容去重）"""
    similar = []
    seen_ids = {problem.id}
    seen_content = set()

    kp_id = problem.knowledge_point_id
    if kp_id <= 1:
        return similar

    same_kp = Problem.query.filter(
        Problem.knowledge_point_id == kp_id,
        Problem.id != problem.id
    ).order_by(Problem.difficulty).limit(limit * 2).all()
    for p in same_kp:
        norm = p.content.strip().lower()[:60]
        if norm not in seen_content:
            similar.append(p)
            seen_ids.add(p.id)
            seen_content.add(norm)

    if len(similar) < limit:
        current_kp = db.session.get(KnowledgePoint, kp_id)
        if current_kp and current_kp.parent_id:
            sib_ids = [c.id for c in KnowledgePoint.query.filter_by(parent_id=current_kp.parent_id).all()
                       if c.id != kp_id]
            if sib_ids:
                for p in Problem.query.filter(Problem.knowledge_point_id.in_(sib_ids),
                                               ~Problem.id.in_(seen_ids)).order_by(Problem.difficulty).limit(limit*2).all():
                    norm = p.content.strip().lower()[:60]
                    if norm not in seen_content:
                        similar.append(p)
                        seen_ids.add(p.id)
                        seen_content.add(norm)
    return similar[:limit]


@app.route('/my-wrong-problems')
@login_required
def my_wrong_problems():
    records = UserWrongProblem.query.filter_by(user_id=current_user.id)\
        .order_by(UserWrongProblem.created_at.desc()).all()
    return render_template('my_wrong_problems.html', records=records)

# ============ 路由 - API：手动触发现 AI 分析 ============
@app.route('/api/analyze-problem/<int:problem_id>', methods=['POST'])
@login_required
def analyze_problem(problem_id):
    problem = db.session.get(Problem, problem_id)
    if not problem:
        return jsonify({'error': '题目不存在'}), 404

    api_key = app.config.get('DEEPSEEK_API_KEY', '')
    if not api_key:
        return jsonify({'error': '未配置 AI API Key'}), 400

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=app.config['DEEPSEEK_BASE_URL'])
        response = client.chat.completions.create(
            model=app.config['DEEPSEEK_MODEL'],
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""分析这道高等数学题，告诉我它属于哪个知识点、难度如何、并给出解析。

题目：{problem.content}

已有的知识点列表（请从以下选择最匹配的）：
{get_knowledge_tree_text()}

返回 JSON 格式：
{{
    "knowledge_point_id": 数字,
    "difficulty": 1-5,
    "explanation": "详细解析",
    "tags": ["标签1", "标签2"]
}}"""
            }]
        )
        import json, re
        text = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            if 'knowledge_point_id' in data:
                problem.knowledge_point_id = data['knowledge_point_id']
            if 'difficulty' in data:
                problem.difficulty = data['difficulty']
            if 'explanation' in data:
                problem.explanation = data['explanation']
            if 'tags' in data:
                problem.tags = ','.join(data['tags'])
            db.session.commit()
            return jsonify({'success': True, 'data': data})
        return jsonify({'error': 'AI 返回格式错误'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_knowledge_tree_text(max_len=3000):
    """把知识树变成文本供 AI 参考（限制长度防止上下文超限）"""
    nodes = KnowledgePoint.query.filter_by(parent_id=None).all()
    texts = []
    for node in nodes:
        texts.append(f"{node.id}. {node.name}")
        for child in node.children.all():
            texts.append(f"  {child.id}. {child.name}")
    result = '\n'.join(texts)
    if len(result) > max_len:
        result = result[:max_len] + '\n... (省略了部分知识点)'
    return result

# ============ 初始化数据库 & 种子数据 ============
def init_database():
    """初始化数据库并插入种子知识点"""
    db.create_all()

    # SQLite 特定优化
    from sqlalchemy import text
    try:
        db.session.execute(text('PRAGMA journal_mode=WAL'))
        db.session.execute(text('PRAGMA busy_timeout=5000'))
        db.session.commit()
    except Exception:
        pass  # PostgreSQL 不支持 PRAGMA

    # 数据库迁移：添加新字段（兼容已有数据库）
    try:
        from sqlalchemy import text as sql_text
        import sqlalchemy
        # 检查是否是 SQLite
        is_sqlite = 'sqlite' in str(db.engine.url)
        if is_sqlite:
            for col, col_type in {'vip_expiry': 'TIMESTAMP', 'upload_count_today': 'INTEGER DEFAULT 0', 'upload_date': 'DATE'}.items():
                try:
                    db.session.execute(sql_text(f'ALTER TABLE users ADD COLUMN {col} {col_type}'))
                except Exception:
                    pass
            try:
                db.session.execute(sql_text('UPDATE users SET upload_count_today = 0 WHERE upload_count_today IS NULL'))
            except Exception:
                pass
        db.session.commit()
    except Exception:
        pass

    # 如果已经有数据就不重复插入
    if KnowledgePoint.query.first():
        return

    # ===== 660 知识树（高数/线代/概率） =====
    g1 = KnowledgePoint(name='高等数学', description='函数、极限、微积分、级数、微分方程')
    g2 = KnowledgePoint(name='线性代数', description='行列式、矩阵、向量、方程组、二次型')
    g3 = KnowledgePoint(name='概率论与数理统计', description='概率、分布、统计、估计')
    db.session.add_all([g1, g2, g3])
    db.session.flush()

    chapters = [
        (g1.id, '函数与极限'), (g1.id, '导数与微分'), (g1.id, '中值定理与导数应用'),
        (g1.id, '不定积分'), (g1.id, '定积分'), (g1.id, '多元函数微分学'),
        (g1.id, '重积分'), (g1.id, '曲线积分与曲面积分'),
        (g1.id, '无穷级数'), (g1.id, '常微分方程'),
        (g2.id, '行列式'), (g2.id, '矩阵'), (g2.id, '向量'),
        (g2.id, '线性方程组'), (g2.id, '特征值与特征向量'), (g2.id, '二次型'),
        (g3.id, '随机事件与概率'), (g3.id, '一维随机变量'), (g3.id, '多维随机变量'),
        (g3.id, '随机变量的数字特征'), (g3.id, '大数定律与中心极限定理'), (g3.id, '数理统计'),
    ]
    for pid, name in chapters:
        db.session.add(KnowledgePoint(name=name, parent_id=pid))

    # ===== 张宇基础30讲 知识树 =====
    root30 = KnowledgePoint(name='张宇基础30讲（高数）',
                            description='张宇基础30讲·高等数学分册（考研数学一/二/三通用）')
    db.session.add(root30)
    db.session.flush()

    lectures_30 = [
        (1, '函数极限与连续', '函数概念、极限定义与计算、无穷小、连续性、间断点'),
        (2, '数列极限', '数列概念、数列极限定义与性质、单调有界准则'),
        (3, '一元函数微分学的概念', '导数的定义与几何意义、可导性、高阶导数'),
        (4, '一元函数微分学的应用（一）', '微分应用、中值定理、泰勒公式、洛必达'),
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
    for num, name, desc in lectures_30:
        db.session.add(KnowledgePoint(name='第%d讲 %s' % (num, name),
                                       description=desc, parent_id=root30.id))

    # ===== 张宇基础30讲（线代） =====
    root_xd = KnowledgePoint(name='张宇基础30讲（线代）', description='张宇基础30讲·线性代数分册')
    db.session.add(root_xd)
    db.session.flush()
    for name, desc in [
        ('零基础课——线性代数入门', '向量基本概念、向量运算、线性变换'),
        ('第1讲 行列式', '行列式的定义、性质、计算、克拉默法则'),
        ('第2讲 矩阵', '矩阵运算、逆矩阵、秩、分块矩阵、初等变换'),
        ('第3讲 向量组', '向量组线性相关性、秩、正交性'),
        ('第4讲 线性方程组', '齐次与非齐次方程组解的结构、通解'),
        ('第5讲 特征值与特征向量', '特征值特征向量、相似对角化、实对称矩阵'),
        ('第6讲 二次型', '二次型标准形、正定二次型、合同变换'),
    ]:
        db.session.add(KnowledgePoint(name=name, description=desc, parent_id=root_xd.id))

    # ===== 张宇基础30讲（概率） =====
    root_gl = KnowledgePoint(name='张宇基础30讲（概率）', description='张宇基础30讲·概率论与数理统计分册')
    db.session.add(root_gl)
    db.session.flush()
    for name, desc in [
        ('第1讲 随机事件与概率', '事件运算、条件概率、全概率公式、贝叶斯公式、独立性'),
        ('第2讲 一维随机变量及其分布', '分布函数、概率质量函数、概率密度函数、常见分布'),
        ('第3讲 多维随机变量及其分布', '联合分布、边际分布、条件分布、独立性'),
        ('第4讲 随机变量的数字特征', '数学期望、方差、协方差与相关系数'),
        ('第5讲 大数定理与中心极限定理', '大数定律、中心极限定理'),
        ('第6讲 数理统计', '样本分布、参数估计、假设检验'),
    ]:
        db.session.add(KnowledgePoint(name=name, description=desc, parent_id=root_gl.id))

    db.session.commit()

    # ===== 导入 1000 题题目 =====
    _seed_problems_from_json()


def _seed_problems_from_json():
    """从 JSON 文件导入 1000 题题目（仅在题目表为空时执行）"""
    import json, os
    if Problem.query.first():
        return

    json_path = os.path.join(os.path.dirname(__file__), '1000_problems_extracted.json')
    if not os.path.exists(json_path):
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    KP_KW = {
        '极限': '函数极限', '连续': '函数极限', '无穷小': '函数极限', '数列': '数列极限',
        '导数': '微分学的概念', '求导': '微分学的概念', '可导': '微分学的概念',
        '中值': '微分学的应用', '泰勒': '微分学的应用', '洛必达': '微分学的应用',
        '单调': '微分学的应用', '极值': '微分学的应用', '最值': '微分学的应用',
        '凹凸': '微分学的应用', '渐近': '微分学的应用', '曲率': '微分学的应用',
        '不定积分': '积分学概念', '原函数': '积分学概念',
        '定积分': '定积分', '换元': '定积分的计算', '分部积分': '定积分的计算',
        '面积': '定积分的应用', '体积': '定积分的应用', '弧长': '定积分的应用',
        '多元': '多元函数微分学', '偏导': '多元函数微分学', '全微分': '多元函数微分学',
        '二重积分': '二重积分', '微分方程': '微分方程',
        '级数': '无穷级数', '收敛': '无穷级数',
    }

    root30 = KnowledgePoint.query.filter_by(name='张宇基础30讲（高数）').first()
    lecture_ids = {}
    if root30:
        for l in root30.children.all():
            lecture_ids[l.name] = l.id

    def find_kp(content):
        for kw, area in KP_KW.items():
            if kw in content:
                for lname, lid in lecture_ids.items():
                    if area in lname:
                        return lid
                return None
        return None

    first_lid = next(iter(lecture_ids.values()), None)
    imported = 0

    for batch_text in raw_data.values():
        text = batch_text.strip()
        for prefix in ['```json', '```']:
            if text.startswith(prefix):
                text = text[len(prefix):]
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
                continue
            opt = p.get('options') or ''
            full = content + ('\n' + str(opt) if str(opt).strip() not in ('', 'None') else '')
            if Problem.query.filter_by(content=full[:200]).first():
                continue
            kp_id = find_kp(full) or first_lid
            diff = 4 if '解答' in str(p.get('type')) else 3
            db.session.add(Problem(content=full, difficulty=diff,
                                    knowledge_point_id=kp_id, source='system',
                                    tags=str(p.get('type', ''))))
            imported += 1

    db.session.commit()
    if imported:
        print(f'[DB] 已导入 {imported} 道 1000 题题目')

# 确保数据库初始化（本地和 Render 部署都生效）
try:
    with app.app_context():
        init_database()
except Exception as e:
    print(f'[DB] 初始化跳过: {e}')

if __name__ == '__main__':
    app.run(debug=True)
