# Pathari-11 FC – Official Club Website

Production-ready Flask application for PATHARI-11 FC (Nepal).

## Features
- Full public website matching approved UI/UX (blue/elephant theme)
- Matches, News, Gallery, Shop, Custom Jersey, Cart, Checkout
- Fan Membership system with digital card
- AI Fan Chatbot (uses live site data)
- Admin CMS (CRUD for News, Matches, Products, Players, Leadership, Gallery, Orders, Members, Settings)
- Official Tech Partner section (BAM Studio) above footer
- No invented player/leadership data – "Coming Soon" placeholders
- Demo content fully editable via admin

## Tech Stack
- Python Flask + SQLAlchemy + Flask-Login + Flask-Migrate
- PostgreSQL
- HTML5 / CSS3 / Vanilla JS

## Setup

```bash
# Create venv & install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure .env (already present)
# DATABASE_URL=postgresql://patharifc:patharifc123@localhost:5432/pathari_11_fc

# Run
python app.py
```

Open http://localhost:5000

### Admin
- URL: /admin/login
- Email: admin@patharifc.com
- Password: admin123

## Structure
See project root for modular layout (models, routes, services, templates, static).

## Important Content Rules
- Player & Leadership pages show "Official information coming soon" until published via admin.
- All demo news, matches, products are flagged and fully replaceable.
- BAM Studio Official Tech Partner block is hardcoded on every page (above footer) as required.

## Production Notes
- Change SECRET_KEY and ADMIN_PASSWORD
- Enable HTTPS / SESSION_COOKIE_SECURE
- Configure real payment gateway in checkout
- Point image storage to Cloudinary if desired
- Run with gunicorn + nginx

Website designed & developed by BAM Studio – Web & Technology Partner.
