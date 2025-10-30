# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import re
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    def __repr__(self):
        return f"<User {self.username}>"

class DocumentTemplate(db.Model):
    __tablename__ = 'document_template'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    template_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow)

    def get_variables(self):
        """
        Извлекает все переменные из шаблона вида {{ имя_переменной }}.
        Поддерживает кириллицу, латиницу, цифры и подчёркивания.
        """
        pattern = r"\{\{\s*([a-zA-Zа-яА-ЯёЁ0-9_]+)\s*\}\}"
        return list(set(re.findall(pattern, self.template_text or "")))

    def __repr__(self):
        return f"<DocumentTemplate {self.name}>"

class GeneratedDocument(db.Model):
    __tablename__ = 'generated_document'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("document_template.id"), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    meta = db.Column(db.Text)  # Храним как JSON-строку

    @property
    def meta_dict(self):
        """Возвращает метаданные как словарь (для удобства в шаблонах или API)."""
        try:
            return json.loads(self.meta) if self.meta else {}
        except (TypeError, json.JSONDecodeError):
            return {}

    def __repr__(self):
        return f"<GeneratedDocument {self.filename}>"