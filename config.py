import os
from dotenv import load_dotenv

_BASE = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(_BASE, '.env'))

_INSTANCE = os.path.join(_BASE, 'instance')
try:
    os.makedirs(_INSTANCE, exist_ok=True)
    _sqlite_path = os.path.join(_INSTANCE, 'pathari_11_fc.db')
except OSError:
    _sqlite_path = '/tmp/pathari_11_fc.db'

_DEFAULT_DB = 'sqlite:///' + _sqlite_path.replace('\\', '/')


def _normalize_db_url(url: str) -> str:
    """Neon / Heroku style URLs → SQLAlchemy."""
    if not url:
        return url
    # postgres:// is deprecated; SQLAlchemy wants postgresql://
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    # Neon often needs SSL
    if url.startswith('postgresql://') and 'sslmode=' not in url:
        sep = '&' if '?' in url else '?'
        url = url + sep + 'sslmode=require'
    return url


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')

    _env_db = (os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('POSTGRES_PRISMA_URL') or '').strip()
    if _env_db and '/tmp/' not in _env_db.replace('\\', '/'):
        SQLALCHEMY_DATABASE_URI = _normalize_db_url(_env_db)
    else:
        SQLALCHEMY_DATABASE_URI = _DEFAULT_DB

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

    # Cloudinary (required on Vercel — filesystem is ephemeral)
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')
    CLOUDINARY_FOLDER = os.getenv('CLOUDINARY_FOLDER', 'pathari-11-fc')

    DEMO_MODE = os.getenv('DEMO_MODE', 'true').lower() in ('1', 'true', 'yes')
    SEED_ON_START = os.getenv('SEED_ON_START', 'true').lower() in ('1', 'true', 'yes')

    PERMANENT_SESSION_LIFETIME = 86400 * 7
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() in ('1', 'true', 'yes')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = False
    WTF_CSRF_TIME_LIMIT = 3600

    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@patharifc.com')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    AI_API_KEY = os.getenv('AI_API_KEY', '')
    AI_API_BASE = os.getenv('AI_API_BASE', 'https://api.x.ai/v1')
    AI_MODEL = os.getenv('AI_MODEL', 'grok-2-latest')
