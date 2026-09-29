import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'iaod-super-secure-key-2026-csmc502')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', str(BASE_DIR / 'iaod.db'))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', str(BASE_DIR / 'uploads'))
    REPORTS_FOLDER = os.environ.get('REPORTS_FOLDER', str(BASE_DIR / 'reports'))
    ALLOWED_EXTENSIONS = {'json', 'csv', 'pdf', 'txt'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max limit
    DEFAULT_TOLERANCE_PERCENT = 15.0  # 15% price spike tolerance
    TESTING = False

class TestConfig(Config):
    DATABASE_PATH = ':memory:'
    TESTING = True
