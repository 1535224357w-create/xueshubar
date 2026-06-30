"""数据库模型"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """用户"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    vip_expiry = db.Column(db.DateTime, nullable=True)  # VIP 到期时间，空=非会员
    upload_count_today = db.Column(db.Integer, default=0)  # 今日上传次数
    upload_date = db.Column(db.Date, nullable=True)  # 记录上传日期的字段

    # 关系：用户的错题
    wrong_problems = db.relationship('UserWrongProblem', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_vip(self):
        """判断是否为 VIP 会员（管理员自动拥有所有权限）"""
        if self.id == 1:
            return True
        if not self.vip_expiry:
            return False
        from datetime import timezone
        expiry = self.vip_expiry
        now = datetime.now(timezone.utc)
        if expiry.tzinfo is None:
            now = now.replace(tzinfo=None)
        return expiry > now


class Order(db.Model):
    """支付订单"""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan = db.Column(db.String(20), nullable=False)  # monthly / quarterly / yearly
    amount = db.Column(db.Integer, nullable=False)  # 金额（分）
    payjs_order_id = db.Column(db.String(32), unique=True, nullable=True)  # 支付平台订单号
    status = db.Column(db.String(20), default='pending')  # pending / paid / expired
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    paid_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='orders')

class KnowledgePoint(db.Model):
    """知识点（树形结构）"""
    __tablename__ = 'knowledge_points'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    parent_id = db.Column(db.Integer, db.ForeignKey('knowledge_points.id'), nullable=True)

    # 父子关系
    children = db.relationship('KnowledgePoint', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    # 该知识点下的题目
    problems = db.relationship('Problem', backref='knowledge_point', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
        }

class Problem(db.Model):
    """题目"""
    __tablename__ = 'problems'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)          # 题目内容（支持 LaTeX）
    answer = db.Column(db.Text, default='')                # 答案
    explanation = db.Column(db.Text, default='')           # 解析
    difficulty = db.Column(db.Integer, default=1)          # 难度 1-5
    source = db.Column(db.String(20), default='system')    # system / user_upload
    knowledge_point_id = db.Column(db.Integer, db.ForeignKey('knowledge_points.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    tags = db.Column(db.String(500), default='')           # 额外标签，逗号分隔
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # 谁做错了这道题
    wrong_records = db.relationship('UserWrongProblem', backref='problem', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'answer': self.answer,
            'explanation': self.explanation,
            'difficulty': self.difficulty,
            'source': self.source,
            'knowledge_point_id': self.knowledge_point_id,
            'knowledge_point_name': self.knowledge_point.name if self.knowledge_point else '',
            'tags': self.tags.split(',') if self.tags else [],
        }

class UserWrongProblem(db.Model):
    """用户的错题记录"""
    __tablename__ = 'user_wrong_problems'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id'), nullable=False)
    user_answer = db.Column(db.Text, default='')           # 用户填的答案
    note = db.Column(db.Text, default='')                  # 用户的笔记
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class ActivationCode(db.Model):
    """激活码"""
    __tablename__ = 'activation_codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    plan = db.Column(db.String(20), nullable=False)  # monthly / quarterly / yearly
    is_used = db.Column(db.Boolean, default=False)
    used_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Report(db.Model):
    """AI 学习报告"""
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
