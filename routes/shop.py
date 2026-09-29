from flask import render_template, request, redirect, url_for, flash, session
from models import db, Product, ProductCategory, ProductVariant, CartItem, Order, OrderItem
from utils.helpers import generate_order_number
from . import shop_bp
import uuid
from decimal import Decimal
from sqlalchemy import text


def get_or_create_cart_id():
    if 'cart_id' not in session:
        session['cart_id'] = str(uuid.uuid4())
    return session['cart_id']


def get_cart_items():
    sid = session.get('cart_id')
    if not sid:
        return []
    return CartItem.query.filter_by(session_id=sid).all()


def cart_totals(items):
    subtotal = sum(Decimal(str(item.product.price)) * item.quantity for item in items if item.product)
    delivery = Decimal('150') if subtotal > 0 else Decimal('0')
    if subtotal >= 5000:
        delivery = Decimal('0')
    total = subtotal + delivery
    return subtotal, delivery, total


@shop_bp.route('/shop')
def shop():
    category = request.args.get('category')
    q = Product.query.filter_by(is_active=True)
    if category:
        cat = ProductCategory.query.filter_by(slug=category).first()
        if cat:
            q = q.filter_by(category_id=cat.id)
    products = q.order_by(Product.is_featured.desc(), Product.name).all()
    categories = ProductCategory.query.order_by(ProductCategory.order).all()
    return render_template('shop.html', products=products, categories=categories, current_cat=category)


@shop_bp.route('/product/<slug>')
def product(slug):
    p = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
    variants = ProductVariant.query.filter_by(product_id=p.id).all()
    related = Product.query.filter(
        Product.id != p.id, Product.is_active == True, Product.category_id == p.category_id
    ).limit(4).all()
    return render_template('product.html', product=p, variants=variants, related=related)


@shop_bp.route('/custom-jersey', methods=['GET', 'POST'])
def custom_jersey():
    base_price = Decimal('3499')

    if request.method == 'POST':
        try:
            name = request.form.get('player_name', '').strip()[:12]
            number = request.form.get('jersey_number', '').strip()[:2]
            jersey_type = request.form.get('jersey_type', 'Home').strip()[:20]
            size = request.form.get('size', 'M').strip()[:10]
            qty = int(request.form.get('quantity', 1) or 1)
            qty = max(1, min(qty, 5))

            custom_prod = Product.query.filter_by(slug='custom-pathari-11-fc-jersey').first()
            if not custom_prod:
                cat = ProductCategory.query.filter_by(name='Jerseys').first()
                custom_prod = Product(
                    name='Custom Pathari-11 FC Jersey',
                    slug='custom-pathari-11-fc-jersey',
                    description='Personalised official-style jersey with your name and number.',
                    price=base_price,
                    is_demo=True,
                    is_active=True,
                    stock=999,
                )
                if cat:
                    custom_prod.category_id = cat.id
                db.session.add(custom_prod)
                db.session.commit()

            sid = get_or_create_cart_id()
            item = CartItem(
                session_id=sid,
                product_id=custom_prod.id,
                quantity=qty,
                custom_name=name,
                custom_number=number,
                is_custom=True,
            )
            # size field stores kit + size for admin order view e.g. "Home / M"
            try:
                item.size = '%s / %s' % (jersey_type, size)
            except Exception:
                pass
            db.session.add(item)
            db.session.commit()
            flash('Custom jersey added to cart!', 'success')
            return redirect(url_for('shop.cart'))
        except Exception as e:
            db.session.rollback()
            print('custom_jersey POST:', e)
            flash('Could not add to cart. Try again.', 'error')

    jersey_imgs = {'Home': '', 'Away': '', 'Third': ''}
    try:
        rows = []
        try:
            rows = db.session.execute(text(
                "SELECT name, image, image_back FROM products WHERE COALESCE(is_active, true) = true"
            )).fetchall()
        except Exception:
            try:
                rows = db.session.execute(text(
                    "SELECT name, image FROM products WHERE is_active = true OR is_active = 1"
                )).fetchall()
            except Exception as e:
                print('products select:', e)

        for row in rows:
            n = (row[0] or '').lower()
            front = row[1] if len(row) > 1 else None
            back = row[2] if len(row) > 2 else None
            src = back or front
            if not src:
                continue
            if 'third' in n or '3rd' in n:
                jersey_imgs['Third'] = src
            elif 'away' in n:
                jersey_imgs['Away'] = src
            elif 'home' in n:
                jersey_imgs['Home'] = src
            elif 'jersey' in n or 'kit' in n:
                if not jersey_imgs['Home']:
                    jersey_imgs['Home'] = src

        if not any(jersey_imgs.values()):
            try:
                r = db.session.execute(text('SELECT image FROM products LIMIT 1')).fetchone()
                if r and r[0]:
                    jersey_imgs = {'Home': r[0], 'Away': r[0], 'Third': r[0]}
            except Exception:
                pass
    except Exception as e:
        print('custom_jersey images:', e)

    return render_template('custom-jersey.html', base_price=base_price, jersey_imgs=jersey_imgs)


@shop_bp.route('/cart')
def cart():
    items = get_cart_items()
    subtotal, delivery, total = cart_totals(items)
    return render_template('cart.html', items=items, subtotal=subtotal, delivery=delivery, total=total)


@shop_bp.route('/cart/add', methods=['POST'])
def cart_add():
    product_id = request.form.get('product_id', type=int)
    size = request.form.get('size', 'M')
    qty = request.form.get('quantity', 1, type=int) or 1
    qty = max(1, min(qty, 10))
    product = Product.query.get_or_404(product_id)
    variant = ProductVariant.query.filter_by(product_id=product.id, size=size).first()
    sid = get_or_create_cart_id()
    existing = CartItem.query.filter_by(
        session_id=sid, product_id=product.id,
        variant_id=variant.id if variant else None, is_custom=False
    ).first()
    if existing:
        existing.quantity += qty
    else:
        db.session.add(CartItem(
            session_id=sid,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            quantity=qty,
            is_custom=False,
        ))
    db.session.commit()
    flash('Added to cart.', 'success')
    return redirect(url_for('shop.cart'))


@shop_bp.route('/cart/update', methods=['POST'])
def cart_update():
    item_id = request.form.get('item_id', type=int)
    qty = request.form.get('quantity', 1, type=int) or 1
    item = CartItem.query.get_or_404(item_id)
    if qty <= 0:
        db.session.delete(item)
    else:
        item.quantity = min(qty, 20)
    db.session.commit()
    return redirect(url_for('shop.cart'))


@shop_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
def cart_remove(item_id):
    item = CartItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Removed.', 'success')
    return redirect(url_for('shop.cart'))


@shop_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    items = get_cart_items()
    if not items:
        flash('Cart is empty.', 'info')
        return redirect(url_for('shop.shop'))
    subtotal, delivery, total = cart_totals(items)
    if request.method == 'POST':
        # Accept both name and full_name field names
        name = (request.form.get('name') or request.form.get('full_name') or '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        notes = request.form.get('notes', '').strip()
        if not name or not phone or not address:
            flash('Name, phone and address are required.', 'error')
            return render_template(
                'checkout.html', items=items, subtotal=subtotal, delivery=delivery, total=total
            )
        try:
            order = Order(
                order_number=generate_order_number(),
                customer_name=name[:100],
                customer_email=(email[:120] if email else None),
                customer_phone=phone[:20],
                address=address[:255],
                city=(city[:50] if city else None),
                notes=notes or None,
                subtotal=subtotal,
                delivery_fee=delivery,
                total=total,
                status='Pending',
                payment_status='pending',
            )
            db.session.add(order)
            db.session.flush()
            for item in items:
                if not item.product:
                    continue
                size_val = getattr(item, 'size', None)
                if not size_val and item.variant:
                    size_val = item.variant.size
                if not size_val:
                    size_val = 'Custom' if item.is_custom else 'N/A'
                db.session.add(OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    product_name=(item.product.name or 'Product')[:150],
                    unit_price=item.product.price,
                    quantity=item.quantity or 1,
                    size=str(size_val)[:40],
                    custom_name=(item.custom_name or None),
                    custom_number=(item.custom_number or None),
                    is_custom=bool(item.is_custom),
                ))
                db.session.delete(item)
            db.session.commit()
            flash('Order placed successfully!', 'success')
            return redirect(url_for('shop.checkout_success', order_number=order.order_number))
        except Exception as e:
            db.session.rollback()
            print('checkout error:', e)
            flash('Could not place order. Please try again. (%s)' % type(e).__name__, 'error')
            return render_template(
                'checkout.html', items=items, subtotal=subtotal, delivery=delivery, total=total
            )
    return render_template(
        'checkout.html', items=items, subtotal=subtotal, delivery=delivery, total=total
    )


@shop_bp.route('/checkout/success/<order_number>')
def checkout_success(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template('checkout_success.html', order=order)
