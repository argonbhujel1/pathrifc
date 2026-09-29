from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import deferred
from flask_login import UserMixin
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='admin')  # admin, editor
    is_active = db.Column(db.Boolean, default=True)
    totp_secret = db.Column(db.String(64))
    totp_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ClubInfo(db.Model):
    __tablename__ = 'club_info'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    image = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Leadership(db.Model):
    __tablename__ = 'leadership'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    section = db.Column(db.String(50), default='Executive Board')  # Committee, Executive Board, Coordination & PR, Advisory Council, Technical Team
    photo = db.Column(db.Text)
    bio = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    number = db.Column(db.Integer)
    position = db.Column(db.String(50))  # GK, DF, MF, FW
    nationality = db.Column(db.String(50))
    date_of_birth = db.Column(db.Date)
    height = db.Column(db.String(20))
    preferred_foot = db.Column(db.String(20))
    photo = db.Column(db.Text)
    appearances = db.Column(db.Integer, default=0)
    goals = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    career = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    opponent = db.Column(db.String(100), nullable=False)
    opponent_logo = db.Column(db.Text)
    competition = db.Column(db.String(100), default='Nepal Super League')
    venue = db.Column(db.String(150))
    match_date = db.Column(db.DateTime, nullable=False)
    is_home = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='upcoming')  # upcoming, live, finished, postponed
    home_score = db.Column(db.Integer)
    away_score = db.Column(db.Integer)
    match_report = db.Column(db.Text)
    is_demo = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class News(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    category = db.Column(db.String(50), default='Club News')  # Match Report, Training, Announcement, Fan Community
    excerpt = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)
    featured_image = db.Column(db.Text)
    author = db.Column(db.String(100), default='Pathari-11 FC Media')
    publish_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='published')  # draft, published
    views = db.Column(db.Integer, default=0)
    is_demo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GalleryImage(db.Model):
    __tablename__ = 'gallery_images'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    category = db.Column(db.String(50), default='Matchday')  # Matchday, Training, Players, Fans, Events, Behind the Scenes
    image = db.Column(db.Text, nullable=False)
    caption = db.Column(db.String(255))
    is_demo = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProductCategory(db.Model):
    __tablename__ = 'product_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True)
    order = db.Column(db.Integer, default=0)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    compare_price = db.Column(db.Numeric(10, 2))
    category_id = db.Column(db.Integer, db.ForeignKey('product_categories.id'))
    category = db.relationship('ProductCategory', backref='products')
    image = db.Column(db.Text)
    image_back = deferred(db.Column(db.Text))  # optional; added via ensure_schema
    stock = db.Column(db.Integer, default=50)
    is_demo = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_limited_offer = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    variants = db.relationship('ProductVariant', backref='product', cascade='all, delete-orphan')

class ProductVariant(db.Model):
    __tablename__ = 'product_variants'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    size = db.Column(db.String(20))  # XS, S, M, L, XL, XXL
    stock = db.Column(db.Integer, default=20)
    sku = db.Column(db.String(50))

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product = db.relationship('Product')
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.id'), nullable=True)
    variant = db.relationship('ProductVariant')
    quantity = db.Column(db.Integer, default=1)
    custom_name = db.Column(db.String(50))  # for custom jersey
    custom_number = db.Column(db.String(5))
    size = db.Column(db.String(40))  # e.g. "Home / M"
    is_custom = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120))
    customer_phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(50))
    province = db.Column(db.String(50))
    postal_code = db.Column(db.String(20))
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    delivery_fee = db.Column(db.Numeric(10, 2), default=0)
    discount = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), default='Cash on Delivery')
    payment_status = db.Column(db.String(20), default='pending')
    status = db.Column(db.String(20), default='Pending')  # Pending, Confirmed, Processing, Shipped, Delivered, Cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    product_name = db.Column(db.String(150))
    size = db.Column(db.String(40))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2))
    custom_name = db.Column(db.String(50))
    custom_number = db.Column(db.String(5))
    is_custom = db.Column(db.Boolean, default=False)

class MembershipPlan(db.Model):
    __tablename__ = 'membership_plans'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # Fan, Silver, Gold, Premium
    slug = db.Column(db.String(50), unique=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    duration_months = db.Column(db.Integer, default=12)
    benefits = db.Column(db.Text)  # JSON or newline separated
    color = db.Column(db.String(20), default='#1e3a5f')
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    free_tickets = db.Column(db.Integer, default=0)

class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    membership_number = db.Column(db.String(30), unique=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('membership_plans.id'))
    plan = db.relationship('MembershipPlan')
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    date_of_birth = db.Column(db.Date)
    address = db.Column(db.String(255))
    profile_photo = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    payment_status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    payment_proof = db.Column(db.Text)
    free_tickets = db.Column(db.Integer, default=0)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    subject = db.Column(db.String(150))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    admin_reply = db.Column(db.Text)
    replied_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Sponsor(db.Model):
    __tablename__ = 'sponsors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    logo = db.Column(db.Text)
    website = db.Column(db.String(255))
    category = db.Column(db.String(100), default='Official Partner')  # custom admin category
    order = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=False)  # only BAM Studio published by default

class SiteSetting(db.Model):
    __tablename__ = 'site_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeagueStanding(db.Model):
    __tablename__ = 'league_standings'
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer, default=1)
    team_name = db.Column(db.String(100), nullable=False)
    played = db.Column(db.Integer, default=0)
    won = db.Column(db.Integer, default=0)
    drawn = db.Column(db.Integer, default=0)
    lost = db.Column(db.Integer, default=0)
    goals_for = db.Column(db.Integer, default=0)
    goals_against = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    is_pathari = db.Column(db.Boolean, default=False)
    season = db.Column(db.String(80), default='2025/26')
    is_published = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TopPerformer(db.Model):
    __tablename__ = 'top_performers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='Top Scorer')  # Top Scorer, Assists, Clean Sheets, Player of the Month
    value = db.Column(db.Integer, default=0)  # goals / assists / etc
    team = db.Column(db.String(100), default='Pathari-11 FC')
    photo = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    season = db.Column(db.String(80), default='2025/26')


class MuseumItem(db.Model):
    """Digital Museum — posters, kits, trophies, photos."""
    __tablename__ = 'museum_items'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), default='Photo')  # Photo, Kit, Trophy, Poster, Ticket, Document
    year = db.Column(db.String(20))
    image = db.Column(db.Text)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ClubLegend(db.Model):
    """Hall of Fame / Where Are They Now / notable figures."""
    __tablename__ = 'club_legends'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(80), default='Player')  # Player, Coach, Staff, Captain
    position = db.Column(db.String(60))  # LW/CF, GK, etc.
    nationality = db.Column(db.String(60), default='Nepal')
    era = db.Column(db.String(80))  # Pathari-11 FC seasons e.g. 2022, 2023
    achievement = db.Column(db.Text)  # documented honour tag
    tags = db.Column(db.String(200))  # comma: Players,Captains,Coaches,Club Legends,Achievements
    appearances = db.Column(db.String(20))
    goals = db.Column(db.String(20))
    assists = db.Column(db.String(20))
    awards = db.Column(db.String(255))
    biography = db.Column(db.Text)
    current_club = db.Column(db.String(120))
    photo = db.Column(db.Text)
    category = db.Column(db.String(40), default='Hall of Fame')
    order = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)


class AllTimeXI(db.Model):
    """Editable club XI slots — admin managed (not invented official lineups)."""
    __tablename__ = 'all_time_xi'
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.String(30), nullable=False)  # GK, RB, CB, LB, CM, AM, ST...
    slot = db.Column(db.Integer, default=1)
    name = db.Column(db.String(100), nullable=False)
    number = db.Column(db.Integer)
    note = db.Column(db.String(200))
    photo = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
