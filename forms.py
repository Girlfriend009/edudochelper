from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FileField, PasswordField, SubmitField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Войти")

class TemplateForm(FlaskForm):
    name = StringField("Название шаблона", validators=[DataRequired()])
    description = TextAreaField("Описание")
    template_text = TextAreaField("Текст шаблона (используйте {{ переменная }})", validators=[DataRequired()])
    submit = SubmitField("Сохранить")