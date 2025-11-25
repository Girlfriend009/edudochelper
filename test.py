import unittest
from app import create_app
from models import db, User, DocumentTemplate, GeneratedDocument

class EduDocHelperTestCase(unittest.TestCase):
    def setUp(self):
        # Create test app and set up test database (in-memory)
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for test simplicity
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # Create default test user
            admin = User(username="admin")
            admin.set_password("admin")
            db.session.add(admin)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.drop_all()

    def login(self, username, password):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_login_logout(self):
        rv = self.login('admin', 'admin')
        # decode response for non-ASCII text
        self.assertIn("Вход выполнен успешно", rv.data.decode("utf-8"))
        rv = self.logout()
        self.assertIn("Вы вышли из системы", rv.data.decode("utf-8"))

    def test_create_template(self):
        self.login('admin', 'admin')
        rv = self.client.post('/templates/create', data=dict(
            name='Test Template',
            description='Test Description',
            template_text='Hello, {name}'
        ), follow_redirects=True)
        self.assertIn("Шаблон сохранён", rv.data.decode("utf-8"))
        # Confirm in DB
        with self.app.app_context():
            tpl = DocumentTemplate.query.filter_by(name='Test Template').first()
            self.assertIsNotNone(tpl)

    def test_generate_document(self):
        self.login('admin', 'admin')
        # Create template in DB
        with self.app.app_context():
            tpl = DocumentTemplate(
                name='Generate Template',
                description='Desc',
                template_text='Hello, {name}',
                created_at=None,
                last_modified=None
            )
            db.session.add(tpl)
            db.session.commit()
            tplid = tpl.id
        # Generate document from template
        rv = self.client.post(f'/templates/{tplid}/generate', data=dict(
            name='World'
        ), follow_redirects=True)
        self.assertTrue(rv.status_code == 200)
        self.assertTrue(rv.content_type in ['application/pdf', 'application/octet-stream'])

    def test_access_control(self):
        # Should redirect to login if not authenticated
        rv = self.client.get('/templates', follow_redirects=True)
        self.assertIn("Требуется вход в систему", rv.data.decode("utf-8"))

if __name__ == '__main__':
    unittest.main()
