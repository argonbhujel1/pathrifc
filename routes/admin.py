from flask import session, render_template, request, redirect, url_for, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from models import (
    db, User, Match, News, Product, ProductCategory, ProductVariant,
    MembershipPlan, Member, ContactMessage, Player, Leadership, GalleryImage,
    Sponsor, Order, ClubInfo, SiteSetting, LeagueStanding, TopPerformer, MuseumItem, ClubLegend, AllTimeXI
)
from utils.helpers import slugify, save_upload, save_image_from_url, resolve_image_input
from datetime import datetime
from functools import wraps
from . import admin_bp

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('admin', 'editor'):
            flash('Please log in as admin.', 'error')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            if getattr(user, 'totp_enabled', False) and user.totp_secret:
                session['pending_2fa_uid'] = user.id
                session['pending_2fa_remember'] = True
                return redirect(url_for('admin.login_2fa'))
            login_user(user, remember=True)
            flash('Welcome back.', 'success')
            return redirect(url_for('admin.dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('admin/login.html')


@admin_bp.route('/login/2fa', methods=['GET', 'POST'])
def login_2fa():
    uid = session.get('pending_2fa_uid')
    if not uid:
        return redirect(url_for('admin.login'))
    user = User.query.get(uid)
    if not user or not user.totp_enabled or not user.totp_secret:
        session.pop('pending_2fa_uid', None)
        return redirect(url_for('admin.login'))
    if request.method == 'POST':
        code = (request.form.get('code') or '').strip().replace(' ', '')
        try:
            import pyotp
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(code, valid_window=1):
                session.pop('pending_2fa_uid', None)
                remember = session.pop('pending_2fa_remember', True)
                login_user(user, remember=remember)
                flash('2FA verified. Welcome.', 'success')
                return redirect(url_for('admin.dashboard'))
        except Exception as e:
            print('2fa verify:', e)
        flash('Invalid authenticator code. Try again.', 'error')
    return render_template('admin/login_2fa.html')


@admin_bp.route('/security', methods=['GET', 'POST'])
@admin_required
def security_2fa():
    """Enable / disable Google Authenticator (TOTP) for current admin."""
    import pyotp
    import urllib.parse
    user = current_user
    # Ensure secret exists when viewing setup
    if not user.totp_secret:
        user.totp_secret = pyotp.random_base32()
        db.session.commit()

    totp = pyotp.TOTP(user.totp_secret)
    issuer = 'PathariFC-Admin'
    label = '%s:%s' % (issuer, user.email or 'admin')
    otpauth = totp.provisioning_uri(name=user.email or 'admin', issuer_name=issuer)
    qr_url = 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + urllib.parse.quote(otpauth)

    if request.method == 'POST':
        action = request.form.get('action')
        code = (request.form.get('code') or '').strip().replace(' ', '')
        if action == 'enable':
            if totp.verify(code, valid_window=1):
                user.totp_enabled = True
                db.session.commit()
                flash('2FA enabled. Use your authenticator app at every login.', 'success')
            else:
                flash('Invalid code — scan QR again and enter the current 6-digit code.', 'error')
        elif action == 'disable':
            if not user.totp_enabled:
                flash('2FA is already off.', 'info')
            elif totp.verify(code, valid_window=1):
                user.totp_enabled = False
                # rotate secret after disable
                user.totp_secret = pyotp.random_base32()
                db.session.commit()
                flash('2FA disabled.', 'success')
            else:
                flash('Enter a valid authenticator code to disable 2FA.', 'error')
        elif action == 'reset_secret':
            if user.totp_enabled:
                flash('Disable 2FA before resetting the secret.', 'error')
            else:
                user.totp_secret = pyotp.random_base32()
                db.session.commit()
                flash('New secret generated. Scan the new QR code.', 'success')
                return redirect(url_for('admin.security_2fa'))
        return redirect(url_for('admin.security_2fa'))

    return render_template(
        'admin/security_2fa.html',
        enabled=bool(user.totp_enabled),
        secret=user.totp_secret,
        qr_url=qr_url,
        otpauth=otpauth,
    )


@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'success')
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
@admin_required
def dashboard():
    from sqlalchemy import or_, not_
    # Shop revenue: exclude Cancelled orders
    shop_rev = db.session.query(db.func.coalesce(db.func.sum(Order.total), 0)).filter(
        db.func.lower(Order.status) != 'cancelled'
    ).scalar() or 0
    # Membership revenue: paid / verified members only
    mem_rev = 0
    try:
        paid = Member.query.filter(
            db.func.lower(Member.payment_status).in_(['paid', 'verified', 'completed', 'success'])
        ).all()
        for m in paid:
            if m.plan and m.plan.price:
                mem_rev += float(m.plan.price)
    except Exception as e:
        print('mem revenue:', e)
    stats = {
        'orders': Order.query.filter(db.func.lower(Order.status) != 'cancelled').count(),
        'orders_cancelled': Order.query.filter(db.func.lower(Order.status) == 'cancelled').count(),
        'revenue': float(shop_rev),
        'membership_revenue': float(mem_rev),
        'total_revenue': float(shop_rev) + float(mem_rev),
        'products': Product.query.count(),
        'members': Member.query.count(),
        'news': News.query.count(),
        'matches': Match.query.count(),
        'messages': ContactMessage.query.filter_by(is_read=False).count(),
        'players': Player.query.count(),
    }
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent_orders)

# ---------- News CRUD ----------
@admin_bp.route('/news')
@admin_required
def news_list():
    items = News.query.order_by(News.publish_date.desc()).all()
    return render_template('admin/news_list.html', items=items)

@admin_bp.route('/news/new', methods=['GET', 'POST'])
@admin_bp.route('/news/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def news_edit(id=None):
    item = News.query.get(id) if id else None
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Title required.', 'error')
            return render_template('admin/news_form.html', item=item)
        if not item:
            item = News(slug=slugify(title))
            db.session.add(item)
        item.title = title
        item.slug = slugify(title)
        item.category = request.form.get('category', 'Club News')
        item.excerpt = request.form.get('excerpt', '')
        item.content = request.form.get('content', '')
        item.author = request.form.get('author', 'Pathari-11 FC Media')
        item.status = request.form.get('status', 'published')
        item.is_demo = False
        path = resolve_image_input('featured_image', 'image_url', request.form, request.files, 'news')
        if path:
            item.featured_image = path
        elif request.files.get('featured_image') and request.files['featured_image'].filename:
            flash('Image upload failed — check Cloudinary keys or use an image URL.', 'error')
        db.session.commit()
        flash('News saved.', 'success')
        return redirect(url_for('admin.news_list'))
    return render_template('admin/news_form.html', item=item)

@admin_bp.route('/news/<int:id>/delete', methods=['POST'])
@admin_required
def news_delete(id):
    item = News.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Deleted.', 'success')
    return redirect(url_for('admin.news_list'))

# ---------- Matches CRUD ----------
@admin_bp.route('/matches')
@admin_required
def matches_list():
    items = Match.query.order_by(Match.match_date.desc()).all()
    return render_template('admin/matches_list.html', items=items)

@admin_bp.route('/matches/new', methods=['GET', 'POST'])
@admin_bp.route('/matches/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def match_edit(id=None):
    item = Match.query.get(id) if id else None
    if request.method == 'POST':
        if not item:
            item = Match(opponent='')
            db.session.add(item)
        item.opponent = request.form.get('opponent', '').strip()
        item.competition = request.form.get('competition', 'Nepal Super League')
        item.venue = request.form.get('venue', '')
        dt_str = request.form.get('match_date')
        if dt_str:
            item.match_date = datetime.fromisoformat(dt_str)
        item.is_home = request.form.get('is_home') == 'on'
        item.status = request.form.get('status', 'upcoming')
        hs = request.form.get('home_score')
        as_ = request.form.get('away_score')
        item.home_score = int(hs) if hs not in (None, '') else None
        item.away_score = int(as_) if as_ not in (None, '') else None
        item.is_demo = False
        item.is_published = request.form.get('is_published') == 'on'
        path = resolve_image_input('opponent_logo', 'opponent_logo_url', request.form, request.files, 'sponsors')
        if path:
            item.opponent_logo = path
        db.session.commit()
        flash('Match saved.', 'success')
        return redirect(url_for('admin.matches_list'))
    return render_template('admin/match_form.html', item=item)

@admin_bp.route('/matches/<int:id>/delete', methods=['POST'])
@admin_required
def match_delete(id):
    item = Match.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Deleted.', 'success')
    return redirect(url_for('admin.matches_list'))

# ---------- Products ----------
@admin_bp.route('/products')
@admin_required
def products_list():
    items = Product.query.order_by(Product.name).all()
    return render_template('admin/products_list.html', items=items)

@admin_bp.route('/products/new', methods=['GET', 'POST'])
@admin_bp.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def product_edit(id=None):
    item = Product.query.get(id) if id else None
    categories = ProductCategory.query.all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Name required.', 'error')
            return render_template('admin/product_form.html', item=item, categories=categories)
        if not item:
            item = Product(name=name, slug=slugify(name), price=0)
            db.session.add(item)
        item.name = name
        item.slug = slugify(name)
        item.description = request.form.get('description', '')
        item.price = request.form.get('price', 0)
        cp = request.form.get('compare_price')
        item.compare_price = float(cp) if cp not in (None, '') else None
        item.stock = request.form.get('stock', 0, type=int)
        item.category_id = request.form.get('category_id', type=int) or None
        item.is_active = request.form.get('is_active') == 'on'
        item.is_featured = request.form.get('is_featured') == 'on'
        item.is_limited_offer = request.form.get('is_limited_offer') == 'on'
        item.is_demo = False
        path = resolve_image_input('image', 'image_url', request.form, request.files, 'products')
        if path:
            item.image = path
        elif request.files.get('image') and request.files['image'].filename:
            flash('Front image upload failed — check Cloudinary or use URL.', 'error')
        path_back = resolve_image_input('image_back', 'image_back_url', request.form, request.files, 'products')
        if path_back:
            try:
                item.image_back = path_back
            except Exception:
                # Fallback: store as SiteSetting if column missing
                from models import SiteSetting
                s = SiteSetting.query.filter_by(key=f'product_back_{item.id}').first()
                if not s:
                    s = SiteSetting(key=f'product_back_{item.id}', value=path_back)
                    db.session.add(s)
                else:
                    s.value = path_back
        elif request.files.get('image_back') and request.files['image_back'].filename:
            flash('Back image upload failed — check Cloudinary or use URL.', 'error')
        db.session.commit()
        flash('Product saved.', 'success')
        return redirect(url_for('admin.products_list'))
    return render_template('admin/product_form.html', item=item, categories=categories)

@admin_bp.route('/products/<int:id>/delete', methods=['POST'])
@admin_required
def product_delete(id):
    item = Product.query.get_or_404(id)
    try:
        from models import CartItem, OrderItem, ProductVariant
        CartItem.query.filter_by(product_id=item.id).delete()
        # Keep order history but null product if needed — delete order items for clean delete
        OrderItem.query.filter_by(product_id=item.id).delete()
        ProductVariant.query.filter_by(product_id=item.id).delete()
        db.session.delete(item)
        db.session.commit()
        flash('Product deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Could not delete: {e}', 'error')
    return redirect(url_for('admin.products_list'))

# ---------- Players (placeholder ready) ----------
@admin_bp.route('/players')
@admin_required
def players_list():
    items = Player.query.order_by(Player.order).all()
    return render_template('admin/players_list.html', items=items)


@admin_bp.route('/players/clear-bad-photos', methods=['POST'])
@admin_required
def players_clear_bad_photos():
    """Remove wrong auto-fetched external photos (keep Cloudinary/local)."""
    try:
        n = 0
        for pl in Player.query.all():
            if not pl.photo:
                continue
            p = str(pl.photo).lower()
            if 'cloudinary.com' in p or p.startswith('/uploads/') or 'res.cloudinary' in p:
                continue
            if 'thesportsdb.com' in p:
                continue
            pl.photo = None
            n += 1
        db.session.commit()
        flash('Cleared %s unreliable photos. Re-fetch or upload correct ones.' % n, 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'error')
    return redirect(url_for('admin.players_list'))


@admin_bp.route('/players/fetch-photos', methods=['POST'])
@admin_required
def players_fetch_photos():
    """Auto-fetch missing player photos from Wikipedia (capped)."""
    try:
        from utils.helpers import ensure_player_photos, fetch_player_photo_url
        from models import AllTimeXI, TopPerformer, ClubLegend
        for pl in Player.query.all():
            if pl.photo is not None and not str(pl.photo).strip():
                pl.photo = None
        missing = [p for p in Player.query.all() if not p.photo]
        n = ensure_player_photos(missing[:15], only_missing=True)
        for xi in AllTimeXI.query.all():
            if not xi.photo:
                pl = Player.query.filter_by(name=xi.name).first()
                xi.photo = (pl.photo if pl and pl.photo else None) or fetch_player_photo_url(xi.name)
        for tp in TopPerformer.query.all():
            if not tp.photo:
                pl = Player.query.filter_by(name=tp.name).first()
                tp.photo = (pl.photo if pl and pl.photo else None) or fetch_player_photo_url(tp.name)
        for lg in ClubLegend.query.all():
            if not lg.photo:
                pl = Player.query.filter_by(name=lg.name).first()
                lg.photo = (pl.photo if pl and pl.photo else None) or fetch_player_photo_url(lg.name)
        db.session.commit()
        flash('Auto-fetched photos for %s players (where available).' % n, 'success')
    except Exception as e:
        db.session.rollback()
        flash('Photo fetch failed: %s' % e, 'error')
    return redirect(url_for('admin.players_list'))

@admin_bp.route('/players/new', methods=['GET', 'POST'])
@admin_bp.route('/players/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def player_edit(id=None):
    item = Player.query.get(id) if id else None
    if request.method == 'POST':
        if not item:
            item = Player()
            db.session.add(item)
        item.name = request.form.get('name', '').strip()
        item.number = request.form.get('number', type=int)
        item.position = request.form.get('position', '')
        item.nationality = request.form.get('nationality', '')
        item.height = request.form.get('height', '')
        item.preferred_foot = request.form.get('preferred_foot', '')
        item.appearances = request.form.get('appearances', 0, type=int)
        item.goals = request.form.get('goals', 0, type=int)
        item.assists = request.form.get('assists', 0, type=int)
        item.career = request.form.get('career', '')
        item.is_published = request.form.get('is_published') == 'on'
        item.order = request.form.get('order', 0, type=int)
        dob = request.form.get('date_of_birth')
        if dob:
            item.date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date()
        path = resolve_image_input('photo', 'photo_url', request.form, request.files, 'players')
        if path:
            item.photo = path
        try:
            db.session.flush()
            # Propagate photo to Top Performers / All-Time XI / Hall of Fame by name
            if item.photo and item.name:
                nm = item.name.strip()
                for tp in TopPerformer.query.filter(TopPerformer.name.ilike(nm)).all():
                    tp.photo = item.photo
                # partial last-name match
                last = nm.split()[-1]
                for tp in TopPerformer.query.filter(TopPerformer.name.ilike('%' + last + '%')).all():
                    if not tp.photo or tp.name.lower() == nm.lower() or last.lower() in (tp.name or '').lower():
                        tp.photo = item.photo
                try:
                    for xi in AllTimeXI.query.filter(AllTimeXI.name.ilike(nm)).all():
                        if hasattr(xi, 'photo'):
                            xi.photo = item.photo
                except Exception:
                    pass
                try:
                    for lg in ClubLegend.query.filter(ClubLegend.name.ilike(nm)).all():
                        lg.photo = item.photo
                except Exception:
                    pass
            db.session.commit()
            flash('Player saved. Photo synced to Top Performers / Hall of Fame where name matches.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Save failed: %s' % e, 'error')
            return render_template('admin/player_form.html', item=item)
        return redirect(url_for('admin.players_list'))
    return render_template('admin/player_form.html', item=item)

# ---------- Leadership ----------
@admin_bp.route('/leadership')
@admin_required
def leadership_list():
    items = Leadership.query.order_by(Leadership.order).all()
    return render_template('admin/leadership_list.html', items=items)

@admin_bp.route('/leadership/new', methods=['GET', 'POST'])
@admin_bp.route('/leadership/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def leadership_edit(id=None):
    item = Leadership.query.get(id) if id else None
    if request.method == 'POST':
        if not item:
            item = Leadership(name='', position='')
            db.session.add(item)
        item.name = request.form.get('name', '').strip()
        item.position = request.form.get('position', '').strip()
        item.section = request.form.get('section', 'Club Leadership') or 'Club Leadership'
        item.bio = request.form.get('bio', '')
        item.order = request.form.get('order', 0, type=int)
        item.is_published = request.form.get('is_published') == 'on'
        path = resolve_image_input('photo', 'photo_url', request.form, request.files, 'leadership')
        if path:
            item.photo = path
        try:
            db.session.commit()
            flash('Leadership saved.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Save failed: %s' % e, 'error')
            return render_template('admin/leadership_form.html', item=item)
        return redirect(url_for('admin.leadership_list'))
    return render_template('admin/leadership_form.html', item=item)

# ---------- Orders ----------
@admin_bp.route('/orders')
@admin_required
def orders_list():
    items = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders_list.html', items=items)

@admin_bp.route('/orders/<int:id>')
@admin_required
def order_detail(id):
    order = Order.query.get_or_404(id)
    # Official jersey back photos for custom order preview
    jersey_imgs = {'home': '', 'away': '', 'third': ''}
    try:
        for p in Product.query.filter(Product.is_active == True).all():
            n = (p.name or '').lower()
            src = getattr(p, 'image_back', None) or p.image
            if not src:
                continue
            if 'third' in n or '3rd' in n:
                jersey_imgs['third'] = src
            elif 'away' in n:
                jersey_imgs['away'] = src
            elif 'home' in n:
                jersey_imgs['home'] = src
            elif ('jersey' in n or 'kit' in n) and not jersey_imgs['home']:
                jersey_imgs['home'] = src
    except Exception as e:
        print('order jersey imgs:', e)
    # Attach preview image URL per custom line item
    for oi in order.items:
        kit = 'home'
        sz = (oi.size or '').lower()
        if 'away' in sz:
            kit = 'away'
        elif 'third' in sz or '3rd' in sz:
            kit = 'third'
        oi._kit = kit
        oi._jersey_img = jersey_imgs.get(kit) or jersey_imgs.get('home') or ''
    return render_template('admin/order_detail.html', order=order, jersey_imgs=jersey_imgs)

@admin_bp.route('/orders/<int:id>/status', methods=['POST'])
@admin_required
def order_status(id):
    order = Order.query.get_or_404(id)
    try:
        old_status = (order.status or '').strip()
        new_status = (request.form.get('status') or order.status or 'Pending').strip()
        order.status = new_status
        # Reduce stock when moving TO Confirmed (once) — case-insensitive
        if new_status.lower() == 'confirmed' and old_status.lower() != 'confirmed':
            for oi in order.items:
                if oi.product_id:
                    prod = Product.query.get(oi.product_id)
                    if prod and prod.stock is not None:
                        prod.stock = max(0, int(prod.stock or 0) - int(oi.quantity or 1))
            flash('Order confirmed. Product stock updated.', 'success')
        else:
            flash('Order status updated to %s.' % new_status, 'success')
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print('order_status error:', e)
        flash('Could not update order: %s' % type(e).__name__, 'error')
    return redirect(url_for('admin.order_detail', id=id))

# ---------- Members ----------
@admin_bp.route('/members')
@admin_required
def members_list():
    items = Member.query.order_by(Member.joined_at.desc()).all()
    return render_template('admin/members_list.html', items=items)

# ---------- Messages ----------
@admin_bp.route('/messages')
@admin_required
def messages_list():
    items = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/messages_list.html', items=items)

@admin_bp.route('/messages/<int:id>')
@admin_required
def message_detail(id):
    msg = ContactMessage.query.get_or_404(id)
    return render_template('admin/message_detail.html', msg=msg)

@admin_bp.route('/messages/<int:id>/read', methods=['POST'])
@admin_required
def message_read(id):
    msg = ContactMessage.query.get_or_404(id)
    msg.is_read = True
    db.session.commit()
    flash('Marked as read.', 'success')
    return redirect(url_for('admin.message_detail', id=id))

@admin_bp.route('/messages/<int:id>/unread', methods=['POST'])
@admin_required
def message_unread(id):
    msg = ContactMessage.query.get_or_404(id)
    msg.is_read = False
    db.session.commit()
    flash('Marked as unread.', 'success')
    return redirect(url_for('admin.messages_list'))

@admin_bp.route('/messages/<int:id>/reply', methods=['POST'])
@admin_required
def message_reply(id):
    msg = ContactMessage.query.get_or_404(id)
    reply = request.form.get('admin_reply', '').strip()
    if reply:
        msg.admin_reply = reply
        msg.is_read = True
        from datetime import datetime
        msg.replied_at = datetime.utcnow()
        db.session.commit()
        flash('Reply saved. (Email sending can be connected later.)', 'success')
    return redirect(url_for('admin.message_detail', id=id))

@admin_bp.route('/messages/<int:id>/delete', methods=['POST'])
@admin_required
def message_delete(id):
    msg = ContactMessage.query.get_or_404(id)
    db.session.delete(msg)
    db.session.commit()
    flash('Message deleted.', 'success')
    return redirect(url_for('admin.messages_list'))

# ---------- Gallery ----------
@admin_bp.route('/gallery')
@admin_required
def gallery_list():
    items = GalleryImage.query.order_by(GalleryImage.created_at.desc()).all()
    return render_template('admin/gallery_list.html', items=items)

@admin_bp.route('/gallery/new', methods=['GET', 'POST'])
@admin_required
def gallery_new():
    if request.method == 'POST':
        path = resolve_image_input('image', 'image_url', request.form, request.files, 'gallery')
        if not path:
            flash('Upload failed. Use PNG/JPG/WEBP/GIF file or a direct image URL.', 'error')
            return render_template('admin/gallery_form.html')
        if path:
            img = GalleryImage(
                title=request.form.get('title', ''),
                category=request.form.get('category', 'Matchday'),
                image=path,
                caption=request.form.get('caption', ''),
                is_demo=False,
                is_published=True
            )
            db.session.add(img)
            db.session.commit()
            flash('Image added.', 'success')
            return redirect(url_for('admin.gallery_list'))
    return render_template('admin/gallery_form.html', item=None)

@admin_bp.route('/gallery/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def gallery_edit(id):
    item = GalleryImage.query.get_or_404(id)
    if request.method == 'POST':
        item.title = request.form.get('title', item.title)
        item.category = request.form.get('category', item.category)
        item.caption = request.form.get('caption', item.caption)
        item.is_published = request.form.get('is_published') == 'on'
        path = resolve_image_input('image', 'image_url', request.form, request.files, 'gallery')
        if path:
            item.image = path
        db.session.commit()
        flash('Gallery image updated.', 'success')
        return redirect(url_for('admin.gallery_list'))
    return render_template('admin/gallery_form.html', item=item)

@admin_bp.route('/gallery/<int:id>/delete', methods=['POST'])
@admin_required
def gallery_delete(id):
    item = GalleryImage.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Image deleted.', 'success')
    return redirect(url_for('admin.gallery_list'))

# ---------- Settings ----------

# ---------- Digital Museum ----------
@admin_bp.route('/museum')
@admin_required
def museum_list():
    items = MuseumItem.query.order_by(MuseumItem.order, MuseumItem.id).all()
    return render_template('admin/museum_list.html', items=items)

@admin_bp.route('/museum/new', methods=['GET', 'POST'])
@admin_bp.route('/museum/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def museum_edit(id=None):
    item = MuseumItem.query.get(id) if id else None
    if request.method == 'POST':
        if not item:
            item = MuseumItem(title='')
            db.session.add(item)
        item.title = request.form.get('title', '').strip()
        item.category = request.form.get('category', 'Photo').strip()
        item.year = request.form.get('year', '').strip()
        item.description = request.form.get('description', '').strip()
        item.order = int(request.form.get('order') or 0)
        item.is_published = request.form.get('is_published') == 'on'
        path = resolve_image_input('image', 'image_url', request.form, request.files, 'museum')
        if path:
            item.image = path
        db.session.commit()
        flash('Museum item saved.', 'success')
        return redirect(url_for('admin.museum_list'))
    return render_template('admin/museum_form.html', item=item)

@admin_bp.route('/museum/<int:id>/delete', methods=['POST'])
@admin_required
def museum_delete(id):
    item = MuseumItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Deleted.', 'success')
    return redirect(url_for('admin.museum_list'))

# ---------- Legends / WATN ----------
@admin_bp.route('/legends')
@admin_required
def legends_list():
    items = ClubLegend.query.order_by(ClubLegend.order, ClubLegend.id).all()
    return render_template('admin/legends_list.html', items=items)

@admin_bp.route('/legends/new', methods=['GET', 'POST'])
@admin_bp.route('/legends/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def legends_edit(id=None):
    item = ClubLegend.query.get(id) if id else None
    if request.method == 'POST':
        try:
            if not item:
                item = ClubLegend(name='Pending')
                db.session.add(item)
            item.name = (request.form.get('name') or '').strip() or 'Unknown'
            item.role = (request.form.get('role') or 'Player').strip()
            item.position = (request.form.get('position') or '').strip()
            item.nationality = (request.form.get('nationality') or 'Nepal').strip()
            item.era = (request.form.get('era') or '').strip()
            item.achievement = (request.form.get('achievement') or '').strip()
            tags = request.form.getlist('tags')
            if not tags:
                raw = (request.form.get('tags') or '').strip()
                tags = [x.strip() for x in raw.split(',') if x.strip()]
            item.tags = ','.join(tags) if tags else (request.form.get('tag_text') or '').strip()
            item.appearances = (request.form.get('appearances') or '').strip()
            item.goals = (request.form.get('goals') or '').strip()
            item.assists = (request.form.get('assists') or '').strip()
            item.awards = (request.form.get('awards') or '').strip()
            item.biography = (request.form.get('biography') or '').strip()
            item.current_club = (request.form.get('current_club') or '').strip()
            item.category = (request.form.get('category') or 'Hall of Fame').strip()
            item.order = int(request.form.get('order') or 0)
            item.is_published = request.form.get('is_published') == 'on'
            path = resolve_image_input('photo', 'photo_url', request.form, request.files, 'legends')
            if path:
                item.photo = path
            db.session.commit()
            flash('Hall of Fame entry saved.', 'success')
            return redirect(url_for('admin.legends_list'))
        except Exception as e:
            db.session.rollback()
            print('legends_edit:', e)
            flash('Could not save: %s' % type(e).__name__, 'error')
    return render_template('admin/legends_form.html', item=item)

@admin_bp.route('/legends/<int:id>/delete', methods=['POST'])
@admin_required
def legends_delete(id):
    item = ClubLegend.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Deleted.', 'success')
    return redirect(url_for('admin.legends_list'))

# ---------- All-Time XI ----------
@admin_bp.route('/all-time-xi')
@admin_required
def xi_list():
    items = AllTimeXI.query.order_by(AllTimeXI.order, AllTimeXI.id).all()
    return render_template('admin/xi_list.html', items=items)

@admin_bp.route('/all-time-xi/new', methods=['GET', 'POST'])
@admin_bp.route('/all-time-xi/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def xi_edit(id=None):
    item = AllTimeXI.query.get(id) if id else None
    if request.method == 'POST':
        if not item:
            item = AllTimeXI(position='CM', name='')
            db.session.add(item)
        item.position = request.form.get('position', 'CM').strip()
        item.name = request.form.get('name', '').strip()
        num = request.form.get('number', '').strip()
        item.number = int(num) if num.isdigit() else None
        item.note = request.form.get('note', '').strip()
        item.order = int(request.form.get('order') or 0)
        item.is_published = request.form.get('is_published') == 'on'
        path = resolve_image_input('photo', 'photo_url', request.form, request.files, 'xi')
        if path:
            item.photo = path
        db.session.commit()
        flash('All-Time XI slot saved.', 'success')
        return redirect(url_for('admin.xi_list'))
    return render_template('admin/xi_form.html', item=item)

@admin_bp.route('/all-time-xi/<int:id>/delete', methods=['POST'])
@admin_required
def xi_delete(id):
    item = AllTimeXI.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Deleted.', 'success')
    return redirect(url_for('admin.xi_list'))



# ---------- Club Info (history / about — admin editable) ----------
@admin_bp.route('/club-info')
@admin_required
def club_info_list():
    items = ClubInfo.query.order_by(ClubInfo.key).all()
    return render_template('admin/club_info_list.html', items=items)

@admin_bp.route('/club-info/new', methods=['GET', 'POST'])
@admin_bp.route('/club-info/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def club_info_edit(id=None):
    item = ClubInfo.query.get(id) if id else None
    if request.method == 'POST':
        try:
            key = (request.form.get('key') or '').strip()
            title = (request.form.get('title') or '').strip()
            content = request.form.get('content') or ''
            if not key:
                flash('Key required (e.g. about_story, trophy_cabinet).', 'error')
                return render_template('admin/club_info_form.html', item=item)
            if not item:
                if ClubInfo.query.filter_by(key=key).first():
                    flash('Key already exists.', 'error')
                    return render_template('admin/club_info_form.html', item=item)
                item = ClubInfo(key=key)
                db.session.add(item)
            item.key = key
            item.title = title
            item.content = content
            path = resolve_image_input('image', 'image_url', request.form, request.files, 'branding')
            if path:
                item.image = path
            db.session.commit()
            flash('Club info saved — visible on public Club page.', 'success')
            return redirect(url_for('admin.club_info_list'))
        except Exception as e:
            db.session.rollback()
            flash('Save failed: %s' % e, 'error')
    return render_template('admin/club_info_form.html', item=item)

@admin_bp.route('/club-info/<int:id>/delete', methods=['POST'])
@admin_required
def club_info_delete(id):
    item = ClubInfo.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Deleted.', 'success')
    return redirect(url_for('admin.club_info_list'))


@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        for key in ['site_title', 'site_tagline', 'contact_email', 'contact_phone', 'contact_address',
                    'facebook', 'instagram', 'twitter', 'youtube', 'bam_name', 'bam_url',
                    'ai_enabled', 'ai_api_key', 'ai_api_base', 'ai_model', 'ai_system_prompt']:
            val = request.form.get(key)
            if val is None:
                continue
            # Do not wipe secret key if admin left password field empty
            if key == 'ai_api_key' and str(val).strip() == '':
                continue
            s = SiteSetting.query.filter_by(key=key).first()
            if s:
                s.value = val
            else:
                db.session.add(SiteSetting(key=key, value=val))
        path = resolve_image_input('club_logo', 'club_logo_url', request.form, request.files, 'branding')
        if path:
            s = SiteSetting.query.filter_by(key='club_logo').first()
            if s:
                s.value = path
            else:
                db.session.add(SiteSetting(key='club_logo', value=path))
        path2 = resolve_image_input('home_ground_image', 'home_ground_image_url', request.form, request.files, 'stadium')
        if path2:
            s2 = SiteSetting.query.filter_by(key='home_ground_image').first()
            if s2:
                s2.value = path2
            else:
                db.session.add(SiteSetting(key='home_ground_image', value=path2))

        bam_path = resolve_image_input('bam_logo', 'bam_logo_url', request.form, request.files, 'branding')
        if bam_path:
            s = SiteSetting.query.filter_by(key='bam_logo').first()
            if s:
                s.value = bam_path
            else:
                db.session.add(SiteSetting(key='bam_logo', value=bam_path))
        for field, url_field, key in [
            ('home_bg', 'home_bg_url', 'home_bg'),
            ('loading_bg', 'loading_bg_url', 'loading_bg'),
            ('hero_card', 'hero_card_url', 'hero_card'),
            ('about_card', 'about_card_url', 'about_card'),
        ]:
            path = resolve_image_input(field, url_field, request.form, request.files, 'branding')
            if path:
                s = SiteSetting.query.filter_by(key=key).first()
                if s:
                    s.value = path
                else:
                    db.session.add(SiteSetting(key=key, value=path))
        db.session.commit()
        flash('Settings saved.', 'success')
        try:
            import app as app_module
            app_module._settings_cache = {}
            app_module._settings_cache_ts = 0
        except Exception:
            pass
        return redirect(url_for('admin.settings'))
    settings_dict = {s.key: s.value for s in SiteSetting.query.all()}
    return render_template('admin/settings.html', settings=settings_dict)


# ---------- Sponsors ----------
@admin_bp.route('/sponsors')
@admin_required
def sponsors_list():
    items = Sponsor.query.order_by(Sponsor.order, Sponsor.id).all()
    return render_template('admin/sponsors_list.html', items=items)

@admin_bp.route('/sponsors/new', methods=['GET', 'POST'])
@admin_bp.route('/sponsors/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def sponsor_edit(id=None):
    item = Sponsor.query.get(id) if id else None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Name required.', 'error')
            return render_template('admin/sponsor_form.html', item=item)
        if not item:
            item = Sponsor(name=name)
            db.session.add(item)
        item.name = name
        item.website = request.form.get('website', '').strip() or None
        item.category = (request.form.get('category') or 'Official Partner').strip() or 'Official Partner'
        item.order = request.form.get('order', 0, type=int) or 0
        item.is_published = request.form.get('is_published') == 'on'
        path = resolve_image_input('logo', 'logo_url', request.form, request.files, 'sponsors')
        if path:
            item.logo = path
        db.session.commit()
        flash('Sponsor saved.', 'success')
        return redirect(url_for('admin.sponsors_list'))
    return render_template('admin/sponsor_form.html', item=item)

@admin_bp.route('/sponsors/<int:id>/delete', methods=['POST'])
@admin_required
def sponsor_delete(id):
    item = Sponsor.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Sponsor deleted.', 'success')
    return redirect(url_for('admin.sponsors_list'))


@admin_bp.route('/members/<int:id>/verify', methods=['POST'])
@admin_required
def member_verify(id):
    member = Member.query.get_or_404(id)
    member.payment_status = 'verified'
    member.status = 'active'
    if member.plan and member.plan.free_tickets:
        member.free_tickets = member.plan.free_tickets
    db.session.commit()
    flash(f'Payment verified for {member.full_name}. Membership active.', 'success')
    return redirect(url_for('admin.members_list'))


# ---------- League Table ----------
@admin_bp.route('/league')
@admin_required
def league_list():
    items = LeagueStanding.query.order_by(LeagueStanding.position).all()
    return render_template('admin/league_list.html', items=items)

@admin_bp.route('/league/new', methods=['GET', 'POST'])
@admin_bp.route('/league/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def league_edit(id=None):
    item = LeagueStanding.query.get(id) if id else None
    if request.method == 'POST':
        if not item:
            item = LeagueStanding(team_name='')
            db.session.add(item)
        item.team_name = request.form.get('team_name', '').strip()
        item.position = request.form.get('position', 1, type=int)
        item.played = request.form.get('played', 0, type=int)
        item.won = request.form.get('won', 0, type=int)
        item.drawn = request.form.get('drawn', 0, type=int)
        item.lost = request.form.get('lost', 0, type=int)
        item.goals_for = request.form.get('goals_for', 0, type=int)
        item.goals_against = request.form.get('goals_against', 0, type=int)
        item.points = request.form.get('points', 0, type=int)
        item.is_pathari = request.form.get('is_pathari') == 'on'
        item.season = request.form.get('season', '2025/26')
        item.is_published = request.form.get('is_published') == 'on'
        db.session.commit()
        flash('League row saved.', 'success')
        return redirect(url_for('admin.league_list'))
    return render_template('admin/league_form.html', item=item)

@admin_bp.route('/league/<int:id>/delete', methods=['POST'])
@admin_required
def league_delete(id):
    item = LeagueStanding.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Deleted.', 'success')
    return redirect(url_for('admin.league_list'))

# ---------- Top Performers ----------
@admin_bp.route('/performers')
@admin_required
def performers_list():
    items = TopPerformer.query.order_by(TopPerformer.order, TopPerformer.id).all()
    return render_template('admin/performers_list.html', items=items)

@admin_bp.route('/performers/new', methods=['GET', 'POST'])
@admin_bp.route('/performers/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def performer_edit(id=None):
    item = TopPerformer.query.get(id) if id else None
    if request.method == 'POST':
        if not item:
            item = TopPerformer(name='')
            db.session.add(item)
        item.name = request.form.get('name', '').strip()
        item.category = request.form.get('category', 'Top Scorer')
        item.value = request.form.get('value', 0, type=int)
        item.team = request.form.get('team', 'Pathari-11 FC')
        item.order = request.form.get('order', 0, type=int)
        item.season = request.form.get('season', '2025/26')
        item.is_published = request.form.get('is_published') == 'on'
        path = resolve_image_input('photo', 'photo_url', request.form, request.files, 'players')
        if path:
            item.photo = path
        db.session.commit()
        flash('Performer saved.', 'success')
        return redirect(url_for('admin.performers_list'))
    return render_template('admin/performer_form.html', item=item)

@admin_bp.route('/performers/<int:id>/delete', methods=['POST'])
@admin_required
def performer_delete(id):
    item = TopPerformer.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Deleted.', 'success')
    return redirect(url_for('admin.performers_list'))
