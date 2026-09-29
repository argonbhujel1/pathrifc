import os
import sys
from pathlib import Path

# Ensure project root is on sys.path (fixes ModuleNotFoundError: config when cwd differs)
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
os.chdir(_ROOT)

from flask import Flask, send_from_directory, session
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from models import db, User, CartItem, SiteSetting
from routes import main_bp, shop_bp, admin_bp
from services.seed import seed_all

# Simple in-memory settings cache (per serverless instance)
_settings_cache = {}
_settings_cache_ts = 0
_SETTINGS_TTL = 60  # seconds


def ensure_schema(app):
    """Add missing columns for SQLite when models evolve (safe no-op if exists)."""
    from sqlalchemy import text, inspect
    with app.app_context():
        try:
            eng = db.engine
            insp = inspect(eng)
            if 'members' in insp.get_table_names():
                cols = {c['name'] for c in insp.get_columns('members')}
                alters = []
                if 'payment_status' not in cols:
                    alters.append("ALTER TABLE members ADD COLUMN payment_status VARCHAR(20) DEFAULT 'pending'")
                if 'payment_method' not in cols:
                    alters.append("ALTER TABLE members ADD COLUMN payment_method VARCHAR(50)")
                if 'payment_reference' not in cols:
                    alters.append("ALTER TABLE members ADD COLUMN payment_reference VARCHAR(100)")
                if 'payment_proof' not in cols:
                    alters.append("ALTER TABLE members ADD COLUMN payment_proof VARCHAR(255)")
                if 'free_tickets' not in cols:
                    alters.append("ALTER TABLE members ADD COLUMN free_tickets INTEGER DEFAULT 0")
                for sql in alters:
                    try:
                        with eng.begin() as conn:
                            conn.execute(text(sql))
                        print('Schema:', sql[:60])
                    except Exception as e:
                        print('Schema skip:', e)
            if 'membership_plans' in insp.get_table_names():
                cols = {c['name'] for c in insp.get_columns('membership_plans')}
                if 'free_tickets' not in cols:
                    try:
                        with eng.begin() as conn:
                            conn.execute(text("ALTER TABLE membership_plans ADD COLUMN free_tickets INTEGER DEFAULT 0"))
                        print('Schema: membership_plans.free_tickets')
                    except Exception as e:
                        print('Schema skip:', e)

            if 'top_performers' in insp.get_table_names():
                try:
                    with eng.begin() as conn:
                        if eng.dialect.name == 'postgresql':
                            conn.execute(text("ALTER TABLE top_performers ALTER COLUMN season TYPE VARCHAR(80)"))
                    print('Schema: top_performers.season -> VARCHAR(80)')
                except Exception as e:
                    print('Schema season:', e)
            
            if 'contact_messages' in insp.get_table_names():
                cols = {c['name'] for c in insp.get_columns('contact_messages')}
                if 'admin_reply' not in cols:
                    try:
                        with eng.begin() as conn:
                            conn.execute(text("ALTER TABLE contact_messages ADD COLUMN admin_reply TEXT"))
                            conn.execute(text("ALTER TABLE contact_messages ADD COLUMN replied_at DATETIME"))
                        print('Schema: contact_messages.admin_reply')
                    except Exception as e:
                        print('Schema skip:', e)
            if 'products' in insp.get_table_names():
                cols = {c['name'] for c in insp.get_columns('products')}
                if 'is_limited_offer' not in cols:
                    try:
                        with eng.begin() as conn:
                            conn.execute(text("ALTER TABLE products ADD COLUMN is_limited_offer BOOLEAN DEFAULT 0"))
                        print('Schema: products.is_limited_offer')
                    except Exception as e:
                        print('Schema skip:', e)

            if 'leadership' in insp.get_table_names():
                cols = {c['name'] for c in insp.get_columns('leadership')}
                if 'section' not in cols:
                    try:
                        with eng.begin() as conn:
                            conn.execute(text("ALTER TABLE leadership ADD COLUMN section VARCHAR(50) DEFAULT 'Executive Board'"))
                        print('Schema: leadership.section')
                    except Exception as e:
                        print('Schema skip:', e)

            # Widen image URL columns (Cloudinary URLs > 255 chars)
            for table, col in [
                ('news', 'featured_image'),
                ('products', 'image'),
                ('sponsors', 'logo'),
                ('players', 'photo'),
                ('leadership', 'photo'),
                ('gallery_images', 'image'),
                ('site_settings', 'value'),
            ]:
                if table in insp.get_table_names():
                    try:
                        with eng.begin() as conn:
                            dialect = eng.dialect.name
                            if dialect == 'postgresql':
                                conn.execute(text(f'ALTER TABLE {table} ALTER COLUMN {col} TYPE TEXT'))
                            # sqlite ignores type changes
                        print(f'Schema: {table}.{col} -> TEXT')
                    except Exception as e:
                        print('Schema widen skip:', e)


            if 'products' in insp.get_table_names():
                cols = {c['name'] for c in insp.get_columns('products')}
                if 'image_back' not in cols:
                    try:
                        with eng.begin() as conn:
                            conn.execute(text("ALTER TABLE products ADD COLUMN image_back TEXT"))
                        print('Schema: products.image_back')
                    except Exception as e:
                        print('Schema image_back skip:', e)

        except Exception as e:
            print('ensure_schema:', e)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    def _safe_makedirs(path):
        """Vercel is read-only except /tmp — never crash on makedirs."""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except OSError:
            return False

    # Prefer /tmp on serverless (VERCEL=1)
    is_serverless = bool(os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
    if is_serverless:
        upload_base = '/tmp/pathari_uploads'
        _safe_makedirs(upload_base)
        app.config['UPLOAD_FOLDER'] = upload_base
    else:
        if not os.path.isabs(app.config['UPLOAD_FOLDER']):
            app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
        _safe_makedirs(os.path.join(app.root_path, 'instance'))
        _safe_makedirs(app.config['UPLOAD_FOLDER'])

    for sub in ['news', 'products', 'players', 'leadership', 'gallery', 'members', 'sponsors', 'branding']:
        _safe_makedirs(os.path.join(app.config['UPLOAD_FOLDER'], sub))

    db.init_app(app)
    migrate = Migrate(app, db)

    login_manager = LoginManager()
    login_manager.login_view = 'admin.login'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Global template context — available on ALL blueprints

    @app.context_processor
    def inject_globals():
        import time as _time
        global _settings_cache, _settings_cache_ts

        def get_cart_count():
            sid = session.get('cart_id')
            if not sid:
                return 0
            try:
                return CartItem.query.filter_by(session_id=sid).count()
            except Exception:
                return 0

        def _load_settings():
            global _settings_cache, _settings_cache_ts
            now = _time.time()
            if _settings_cache and (now - _settings_cache_ts) < _SETTINGS_TTL:
                return _settings_cache
            data = {}
            try:
                for s in SiteSetting.query.all():
                    data[s.key] = s.value
            except Exception:
                pass
            _settings_cache = data
            _settings_cache_ts = now
            return data

        def get_setting(key, default=''):
            return _load_settings().get(key, default) or default

        return {
            'cart_count': get_cart_count(),
            'site_title': get_setting('site_title', 'Pathari-11 FC | Official Football Club'),
            'tagline': get_setting('site_tagline', 'ONE CLUB. ONE PRIDE.'),
            'club_logo': get_setting('club_logo', ''),
            'bam_logo': get_setting('bam_logo', ''),
            'bam_name': get_setting('bam_name', 'BAM Studio'),
            'bam_url': get_setting('bam_url', 'https://argan.com.np/'),
            'home_bg': get_setting('home_bg', ''),
            'loading_bg': get_setting('loading_bg', ''),
            'hero_card': get_setting('hero_card', ''),
            'about_card': get_setting('about_card', ''),
            'contact_email': get_setting('contact_email', ''),
            'contact_phone': get_setting('contact_phone', ''),
            'contact_address': get_setting('contact_address', ''),
            'social_facebook': get_setting('facebook', ''),
            'social_instagram': get_setting('instagram', ''),
            'social_twitter': get_setting('twitter', ''),
            'social_youtube': get_setting('youtube', ''),
        }

    @app.template_filter('media_url')
    def media_url_filter(path):
        if not path:
            return ''
        p = str(path).strip()
        # Full Cloudinary / external URL already
        if p.startswith('http://') or p.startswith('https://') or p.startswith('//'):
            return p
        # Broken stored form: https:/res.cloudinary... (missing slash)
        if p.startswith('https:/') and not p.startswith('https://'):
            return 'https://' + p[7:]
        if p.startswith('http:/') and not p.startswith('http://'):
            return 'http://' + p[6:]
        # Accidentally stored with /uploads/https://...
        if '/uploads/http' in p:
            idx = p.find('http')
            return p[idx:]
        if p.startswith('/uploads/'):
            rest = p[len('/uploads/'):]
            if rest.startswith('http'):
                return rest
            return p
        return '/uploads/' + p.lstrip('/')

    @app.before_request
    def make_session_permanent():
        session.permanent = True

    app.register_blueprint(main_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(admin_bp)

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print('create_all:', e)
        try:
            ensure_schema(app)
        except Exception as e:
            print('ensure_schema:', e)
        # Always try add image_back + cart size (Neon)
        try:
            from sqlalchemy import text, inspect
            eng = db.engine
            insp = inspect(eng)
            if 'products' in insp.get_table_names():
                cols = {c['name'] for c in insp.get_columns('products')}
                if 'image_back' not in cols:
                    with eng.begin() as conn:
                        conn.execute(text('ALTER TABLE products ADD COLUMN image_back TEXT'))
                    print('Added products.image_back')
            if 'cart_items' in insp.get_table_names():
                cols = {c['name'] for c in insp.get_columns('cart_items')}
                if 'size' not in cols:
                    with eng.begin() as conn:
                        conn.execute(text('ALTER TABLE cart_items ADD COLUMN size VARCHAR(40)'))
                    print('Schema: cart_items.size')
        except Exception as e:
            print('schema alter:', e)

        try:
            from sqlalchemy import text, inspect as sa_inspect
            eng = db.engine
            insp = sa_inspect(eng)
            if 'club_legends' in insp.get_table_names():
                cols = {c['name'] for c in insp.get_columns('club_legends')}
                alters = []
                for col, typ in [
                    ('position', 'VARCHAR(60)'), ('nationality', 'VARCHAR(60)'),
                    ('tags', 'VARCHAR(200)'), ('appearances', 'VARCHAR(20)'),
                    ('goals', 'VARCHAR(20)'), ('assists', 'VARCHAR(20)'),
                    ('awards', 'VARCHAR(255)'), ('biography', 'TEXT'),
                ]:
                    if col not in cols:
                        alters.append('ALTER TABLE club_legends ADD COLUMN %s %s' % (col, typ))
                if alters:
                    with eng.begin() as conn:
                        for a in alters:
                            conn.execute(text(a))
                    print('Schema: club_legends extended')
        except Exception as e:
            print('club_legends schema:', e)


        try:
            from sqlalchemy import text, inspect as sa_inspect
            eng = db.engine
            insp = sa_inspect(eng)
            if 'users' in insp.get_table_names():
                cols = {c['name'] for c in insp.get_columns('users')}
                with eng.begin() as conn:
                    if 'totp_secret' not in cols:
                        conn.execute(text('ALTER TABLE users ADD COLUMN totp_secret VARCHAR(64)'))
                        print('Schema: users.totp_secret')
                    if 'totp_enabled' not in cols:
                        conn.execute(text('ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE'))
                        print('Schema: users.totp_enabled')
        except Exception as e:
            print('2fa schema:', e)

        try:
            if app.config.get('SEED_ON_START', True):
                seed_all(app)
        except Exception as e:
            print('seed warning:', e)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
