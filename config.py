import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("EDUDOC_SECRET", "dev-secret-key-for-demo")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'edudochelper.sqlite'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    SIGN_FOLDER = UPLOAD_FOLDER / "signatures"
    PDF_FOLDER = UPLOAD_FOLDER / "pdfs"
    INSTANCE_FOLDER = BASE_DIR / "instance"

    @staticmethod
    def init_app(app):
        # Создаём папки при запуске
        folders = [Config.INSTANCE_FOLDER, Config.UPLOAD_FOLDER, Config.SIGN_FOLDER, Config.PDF_FOLDER]
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)