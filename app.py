"""高等数学学习网站 - 主程序"""
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, KnowledgePoint, Problem, UserWrongProblem

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
    info = {
        'os_env': str(os.environ.get('ALIPAY_APP_ID', '空'))[:20],
        'from_config': str(app.config.get('ALIPAY_APP_ID', '空'))[:20],
        'config_raw': str(app.config.get('ALIPAY_APP_ID', 'NONE'))[:20],
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
    # 获取所有一级知识点
    root_nodes = KnowledgePoint.query.filter_by(parent_id=None).all()
    return render_template('knowledge/tree.html', root_nodes=root_nodes)

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
                        'content': (
                            '解答这道数学题。要求：\n'
                            '1. 步骤简洁，多用数学符号\n'
                            '2. 如果涉及积分区域、函数图像等需要画图辅助理解，\n'
                            '   插入【PLOT】JSON指令\n'
                            '3. 最后写 【答案】结果\n\n'
                            '题目：' + content
                        )
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
        claude_key = app.config.get('ANTHROPIC_API_KEY', '')
        if claude_key:
            try:
                from claude_vision import recognize_math_problem
                text, _ = recognize_math_problem(img_data, claude_key,
                                                  model=app.config['CLAUDE_MODEL'])
                return jsonify({'text': text, 'raw_ocr': text[:100], 'success': True})
            except Exception as e:
                # Claude 失败，回退到百度OCR
                pass

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

    # 支付宝当面付（APP_ID 不是敏感信息，直接写死）
    app_id = '2021006167668054'
    if app_id:
        try:
            from alipay import AliPay
            import os
            app_dir = os.path.dirname(__file__)
            private_key_raw = os.getenv('ALIPAY_PRIVATE_KEY', '')
            if private_key_raw:
                # 从 Base64 解码（兼容 Render 环境变量丢失换行符）
                import base64
                try:
                    private_key_bytes = base64.b64decode(private_key_raw)
                    private_key = private_key_bytes.decode('utf-8')
                except:
                    # 如果不是 base64，尝试直接作为 PEM 使用
                    private_key = private_key_raw
                    if '\\n' in private_key:
                        private_key = private_key.replace('\\n', '\n')
            else:
                with open(os.path.join(app_dir, 'alipay_private_key.pem')) as f:
                    private_key = f.read()
            with open(os.path.join(app_dir, 'alipay_public_key.pem')) as f:
                public_key = f.read()

            alipay = AliPay(
                appid=app_id,
                app_notify_url='https://xueshubar.onrender.com/api/alipay/notify',
                app_private_key_string=private_key,
                alipay_public_key_string=public_key,
                sign_type='RSA2',
            )

            result = alipay.api_alipay_trade_precreate(
                subject='学数 bar VIP 会员',
                out_trade_no=out_trade_no,
                total_amount=amount / 100,
            )

            code = result.get('code')
            if code == '10000':
                order.payjs_order_id = out_trade_no
                db.session.commit()
                return jsonify({
                    'qrcode': result.get('qr_code', ''),
                    'order_id': order.id,
                })
            else:
                print(f'[支付宝] 下单失败: {result}')
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
    similar = []
    seen_ids = {problem.id}
    same_kp = Problem.query.filter(
        Problem.knowledge_point_id == problem.knowledge_point_id,
        Problem.id != problem.id
    ).order_by(Problem.difficulty).limit(limit).all()
    for p in same_kp:
        similar.append(p)
        seen_ids.add(p.id)
    if len(similar) < limit:
        current_kp = db.session.get(KnowledgePoint, problem.knowledge_point_id)
        if current_kp and current_kp.parent_id:
            sibling_ids = [
                c.id for c in KnowledgePoint.query.filter_by(parent_id=current_kp.parent_id).all()
                if c.id != current_kp.id
            ]
            if sibling_ids:
                siblings = Problem.query.filter(
                    Problem.knowledge_point_id.in_(sibling_ids),
                    ~Problem.id.in_(seen_ids)
                ).order_by(Problem.difficulty).limit(limit - len(similar)).all()
                for p in siblings:
                    similar.append(p)
                    seen_ids.add(p.id)
    if len(similar) < limit and problem.tags:
        for tag in problem.tags.split(','):
            tag = tag.strip()
            if not tag: continue
            tag_matches = Problem.query.filter(
                Problem.tags.contains(tag),
                ~Problem.id.in_(seen_ids)
            ).limit(limit - len(similar)).all()
            for p in tag_matches:
                similar.append(p)
                seen_ids.add(p.id)
            if len(similar) >= limit: break
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

def get_knowledge_tree_text():
    """把知识树变成文本供 AI 参考"""
    nodes = KnowledgePoint.query.filter_by(parent_id=None).all()
    texts = []
    for node in nodes:
        texts.append(f"{node.id}. {node.name}")
        for child in node.children.all():
            texts.append(f"  {child.id}. {child.name}")
    return '\n'.join(texts)

# ============ 初始化数据库 & 种子数据 ============
def init_database():
    """初始化数据库并插入种子知识点"""
    # 启用 WAL 模式，解决 SQLite 并发写入锁死问题
    from sqlalchemy import text
    db.session.execute(text('PRAGMA journal_mode=WAL'))
    db.session.execute(text('PRAGMA busy_timeout=5000'))
    db.session.commit()

    db.create_all()

    # 确保所有表已创建
    db.create_all()
    db.create_all()

    # 数据库迁移：添加新字段（兼容已有数据库）
    try:
        from sqlalchemy import text as sql_text
        cols_to_add = {
            'vip_expiry': 'TIMESTAMP',
            'upload_count_today': 'INTEGER DEFAULT 0',
            'upload_date': 'DATE',
        }
        for col, col_type in cols_to_add.items():
            try:
                db.session.execute(sql_text(f'ALTER TABLE users ADD COLUMN {col} {col_type}'))
            except Exception:
                pass
        # 尝试修复 upload_count_today 类型（重建列）
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

    # 一级知识点
    kp1 = KnowledgePoint(name='一元微积分', description='极限、导数、积分')
    kp2 = KnowledgePoint(name='多元微积分', description='偏导数、重积分、曲线曲面积分')
    kp3 = KnowledgePoint(name='线性代数', description='矩阵、行列式、向量空间')
    kp4 = KnowledgePoint(name='概率论与数理统计', description='概率、分布、统计推断')
    kp5 = KnowledgePoint(name='常微分方程', description='一阶、二阶、高阶微分方程')

    db.session.add_all([kp1, kp2, kp3, kp4, kp5])
    db.session.flush()

    # 二级知识点
    children = [
        KnowledgePoint(name='极限', description='数列极限、函数极限', parent_id=kp1.id),
        KnowledgePoint(name='导数与微分', description='求导法则、高阶导数', parent_id=kp1.id),
        KnowledgePoint(name='不定积分', description='换元法、分部积分', parent_id=kp1.id),
        KnowledgePoint(name='定积分', description='牛顿-莱布尼茨公式', parent_id=kp1.id),
        KnowledgePoint(name='偏导数', description='多元函数求导', parent_id=kp2.id),
        KnowledgePoint(name='重积分', description='二重积分、三重积分', parent_id=kp2.id),
        KnowledgePoint(name='矩阵运算', description='矩阵乘法、逆矩阵', parent_id=kp3.id),
        KnowledgePoint(name='行列式', description='行列式计算', parent_id=kp3.id),
        KnowledgePoint(name='随机变量', description='离散型、连续型随机变量', parent_id=kp4.id),
        KnowledgePoint(name='参数估计', description='点估计、区间估计', parent_id=kp4.id),
        KnowledgePoint(name='一阶微分方程', description='可分离变量、齐次方程', parent_id=kp5.id),
        KnowledgePoint(name='二阶微分方程', description='常系数线性方程', parent_id=kp5.id),
    ]
    db.session.add_all(children)
    db.session.commit()

# 确保数据库初始化（本地和 Render 部署都生效）
with app.app_context():
    init_database()

if __name__ == '__main__':
    app.run(debug=True)
