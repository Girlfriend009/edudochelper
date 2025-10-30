import os
from datetime import datetime, date
from flask import Flask, render_template, redirect, url_for, flash, request, send_file, abort, session
from werkzeug.utils import secure_filename
from models import db, User, DocumentTemplate, GeneratedDocument
from forms import LoginForm, TemplateForm
from utils import create_pdf_from_template, secure_unique_filename
from config import Config
import json


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.init_app(app)

    db.init_app(app)

    # ---------- Jinja2 фильтр для получения шаблона по ID ----------
    @app.template_filter('get_template')
    def get_template(template_id):
        return DocumentTemplate.query.get(template_id)

    # ---------- Вспомогательные функции ----------
    def require_login():
        if not session.get("user_id"):
            flash("Требуется вход в систему.", "warning")
            return False
        return True

    # ---------- Функция добавления демо шаблонов ----------
    def _add_demo_templates():
        templates_data = [
            {
                "name": "Справка об обучении",
                "description": "Официальная справка для студентов",
                "template_text": """Справка

Настоящая справка выдана {{ ФИО_студента }} в том, что он(а) является студентом(кой) {{ факультет }} факультета {{ университет }} с {{ дата_поступления }} по настоящее время.

Курс: {{ курс }}
Форма обучения: {{ форма_обучения }}

Подпись: {{ подпись }}
"""
            },
            {
                "name": "Благодарственное письмо",
                "description": "Для преподавателей и сотрудников",
                "template_text": """Благодарственное письмо

Выражаем искреннюю благодарность {{ ФИО }} за активное участие в организации {{ мероприятие }} и вклад в развитие образовательного процесса.

Желаем дальнейших успехов и профессионального роста!

{{ должность_подписи }}
{{ ФИО_подписи }}
{{ дата }}
"""
            },
            {
                "name": "Приказ о зачислении",
                "description": "Приказ ректора",
                "template_text": """ПРИКАЗ

{{ университет }}
{{ дата }}

О зачислении

Зачислить на {{ курс }} курс {{ факультет }} факультета следующих студентов:

1. {{ ФИО_студента }} — {{ специальность }}

Основание: Приказ Минобрнауки №{{ номер_приказа }}

Ректор: {{ подпись_ректора }}
"""
            }
        ]
        for t in templates_data:
            tpl = DocumentTemplate(
                name=t["name"],
                description=t["description"],
                template_text=t["template_text"],
                created_at=datetime.utcnow(),
                last_modified=datetime.utcnow()
            )
            db.session.add(tpl)
        db.session.commit()

    # ---------- Создание БД и тестовых данных ----------
    with app.app_context():
        db.create_all()

        # Создаём админа, если нет
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin")
            admin_pass = os.environ.get("ADMIN_PASSWORD", "admin")
            admin.set_password(admin_pass)
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Админ создан. Логин: admin, Пароль: {admin_pass}")

        # Добавляем тестовые шаблоны (если нет)
        if DocumentTemplate.query.count() == 0:
            _add_demo_templates()
            print("✅ Демо-шаблоны добавлены.")

    # ---------- Маршруты ----------
    @app.route("/")
    def index():
        templates = DocumentTemplate.query.all()
        generated_count = GeneratedDocument.query.count()
        today_count = GeneratedDocument.query.filter(
            GeneratedDocument.created_at >= date.today()
        ).count()
        return render_template("index.html",
                               templates=templates,
                               generated_count=generated_count,
                               today_count=today_count)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                session['user_id'] = user.id
                flash("Вход выполнен успешно.", "success")
                return redirect(url_for("templates_list"))
            flash("Неверный логин или пароль.", "danger")
        return render_template("login.html", form=form)

    @app.route("/logout")
    def logout():
        session.pop('user_id', None)
        flash("Вы вышли из системы.", "info")
        return redirect(url_for("index"))

    # ---------- Шаблоны ----------
    @app.route("/templates")
    def templates_list():
        if not require_login():
            return redirect(url_for("login"))
        q = request.args.get('q', '').strip()
        query = DocumentTemplate.query
        if q:
            query = query.filter(DocumentTemplate.name.contains(q))
        items = query.order_by(DocumentTemplate.id.desc()).all()
        return render_template("templates_list.html", templates=items, search_query=q)

    @app.route("/templates/create", methods=["GET", "POST"])
    @app.route("/templates/<int:tpl_id>/edit", methods=["GET", "POST"])
    def template_edit(tpl_id=None):
        if not require_login():
            return redirect(url_for("login"))
        tpl = DocumentTemplate.query.get(tpl_id) if tpl_id else None
        form = TemplateForm(obj=tpl)
        if form.validate_on_submit():
            if tpl is None:
                tpl = DocumentTemplate()
                tpl.created_at = datetime.utcnow()
            tpl.name = form.name.data
            tpl.description = form.description.data
            tpl.template_text = form.template_text.data
            tpl.last_modified = datetime.utcnow()
            db.session.add(tpl)
            db.session.commit()
            flash("Шаблон сохранён.", "success")
            return redirect(url_for("templates_list"))
        return render_template("template_edit.html", form=form, tpl=tpl)

    @app.route("/templates/<int:tpl_id>/delete", methods=["POST"])
    def template_delete(tpl_id):
        if not require_login():
            return redirect(url_for("login"))
        tpl = DocumentTemplate.query.get_or_404(tpl_id)
        GeneratedDocument.query.filter_by(template_id=tpl.id).delete()
        db.session.delete(tpl)
        db.session.commit()
        flash("Шаблон и связанные документы удалены.", "warning")
        return redirect(url_for("templates_list"))

    # ---------- Генерация документа ----------
    @app.route("/templates/<int:tpl_id>/generate", methods=["GET", "POST"])
    def template_generate(tpl_id):
        if not require_login():
            return redirect(url_for("login"))
        tpl = DocumentTemplate.query.get_or_404(tpl_id)
        variables = tpl.get_variables()

        if request.method == "POST":
            data = {var: request.form.get(var, '').strip() for var in variables}
            missing = [var for var, val in data.items() if not val]
            if missing:
                flash(f"Не заполнены обязательные поля: {', '.join(missing)}", "danger")
                return render_template("template_generate.html", tpl=tpl, variables=variables, data=data)

            signature_path = None
            uploaded = request.files.get('signature')
            if uploaded and uploaded.filename:
                filename = secure_unique_filename(uploaded.filename)
                saved = Config.SIGN_FOLDER / filename
                uploaded.save(saved)
                signature_path = str(saved)

            try:
                pdf_buffer = create_pdf_from_template(tpl.template_text, data, signature_path)
            except Exception as e:
                flash(f"Ошибка генерации PDF: {str(e)}", "danger")
                return render_template("template_generate.html", tpl=tpl, variables=variables, data=data)

            pdf_filename = f"{secure_unique_filename(tpl.name)}.pdf"
            saved_path = Config.PDF_FOLDER / pdf_filename
            with open(saved_path, "wb") as out:
                out.write(pdf_buffer.getvalue())

            gd = GeneratedDocument(
                template_id=tpl.id,
                filename=pdf_filename,
                created_at=datetime.utcnow(),
                meta=json.dumps(data, ensure_ascii=False)
            )
            db.session.add(gd)
            db.session.commit()

            flash("Документ успешно создан!", "success")
            return send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name=pdf_filename)

        return render_template("template_generate.html", tpl=tpl, variables=variables, data={})

    # ---------- Сгенерированные документы ----------
    @app.route("/generated")
    def generated_list():
        if not require_login():
            return redirect(url_for("login"))
        q = request.args.get('q', '').strip()
        query = GeneratedDocument.query
        if q:
            query = query.join(DocumentTemplate).filter(DocumentTemplate.name.contains(q))
        items = query.order_by(GeneratedDocument.created_at.desc()).all()
        return render_template("generated_list.html", items=items, search_query=q)

    @app.route("/generated/<int:doc_id>/download")
    def generated_download(doc_id):
        if not require_login():
            return redirect(url_for("login"))
        doc = GeneratedDocument.query.get_or_404(doc_id)
        filepath = Config.PDF_FOLDER / doc.filename
        if not filepath.exists():
            abort(404)
        return send_file(filepath, as_attachment=True, download_name=doc.filename)

    @app.route("/generated/<int:doc_id>/delete", methods=["POST"])
    def generated_delete(doc_id):
        if not require_login():
            return redirect(url_for("login"))
        doc = GeneratedDocument.query.get_or_404(doc_id)
        filepath = Config.PDF_FOLDER / doc.filename
        if filepath.exists():
            filepath.unlink()
        db.session.delete(doc)
        db.session.commit()
        flash("Документ удалён.", "warning")
        return redirect(url_for("generated_list"))

    # ---------- Health check ----------
    @app.route("/health")
    def health():
        return "OK", 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="127.0.0.1", port=5000)
