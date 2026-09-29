import os
from flask import render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import login_required, current_user
from models import (
    db, Match, News, Product, Player, Leadership, GalleryImage, ClubInfo,
    MembershipPlan, Member, ContactMessage, Sponsor, SiteSetting, CartItem, LeagueStanding, TopPerformer
)
from utils.helpers import generate_membership_number, slugify
from datetime import datetime, timedelta
from . import main_bp
import uuid

def get_setting(key, default=''):
    s = SiteSetting.query.filter_by(key=key).first()
    return s.value if s else default

@main_bp.route('/')
def index():
    next_match = Match.query.filter(
        Match.status == 'upcoming',
        Match.is_published == True
    ).order_by(Match.match_date.asc()).first()

    recent_results = Match.query.filter(
        Match.status == 'finished',
        Match.is_published == True
    ).order_by(Match.match_date.desc()).limit(4).all()

    upcoming = Match.query.filter(
        Match.status == 'upcoming',
        Match.is_published == True
    ).order_by(Match.match_date.asc()).limit(4).all()

    latest_news = News.query.filter_by(status='published').order_by(News.publish_date.desc()).limit(4).all()

    featured_products = Product.query.filter_by(is_featured=True, is_active=True).limit(4).all()
    if not featured_products:
        featured_products = Product.query.filter_by(is_active=True).order_by(Product.id.desc()).limit(4).all()

    about = ClubInfo.query.filter_by(key='about_story').first()
    vision = ClubInfo.query.filter_by(key='vision').first()
    mission = ClubInfo.query.filter_by(key='mission').first()
    values = ClubInfo.query.filter_by(key='values').first()

    sponsors = Sponsor.query.filter(
        Sponsor.is_published == True,
        Sponsor.category != 'Web & Technology Partner'
    ).order_by(Sponsor.order, Sponsor.id).all()
    # order 0-2 biggest, 3-6 medium, 7+ small
    sponsor_big = [s for s in sponsors if (s.order or 0) <= 2]
    sponsor_mid = [s for s in sponsors if 3 <= (s.order or 0) <= 6]
    sponsor_small = [s for s in sponsors if (s.order or 0) >= 7]

    standings = LeagueStanding.query.filter_by(is_published=True).order_by(LeagueStanding.position).limit(10).all()
    if not standings:
        standings = LeagueStanding.query.order_by(LeagueStanding.position).limit(10).all()
    performers = TopPerformer.query.filter_by(is_published=True).order_by(TopPerformer.order, TopPerformer.id).limit(6).all()
    if not performers:
        performers = TopPerformer.query.order_by(TopPerformer.order, TopPerformer.id).limit(6).all()
    # Always prefer current squad photo (admin upload) over stale performer photo
    try:
        for p in performers:
            pl = Player.query.filter(Player.name.ilike(p.name)).first()
            if not pl and p.name:
                last = p.name.split()[-1]
                pl = Player.query.filter(Player.name.ilike('%' + last + '%')).first()
            if pl and pl.photo:
                p.photo = pl.photo
    except Exception:
        pass
    squad_preview = Player.query.filter_by(is_published=True).order_by(Player.order, Player.number).limit(8).all()

    # Homepage hub previews
    try:
        from models import MuseumItem, ClubLegend, AllTimeXI, MembershipPlan, GalleryImage
        all_time_xi = AllTimeXI.query.filter_by(is_published=True).order_by(AllTimeXI.order).limit(11).all()
        hall_preview = ClubLegend.query.filter_by(is_published=True, category='Hall of Fame').order_by(ClubLegend.order).limit(3).all()
        museum_preview = MuseumItem.query.filter_by(is_published=True).order_by(MuseumItem.order).limit(3).all()
        plans = MembershipPlan.query.filter_by(is_active=True).order_by(MembershipPlan.order, MembershipPlan.price).limit(4).all()
        gallery_preview = GalleryImage.query.filter_by(is_published=True).order_by(GalleryImage.id.desc()).limit(4).all()
        trophies = ClubInfo.query.filter_by(key='trophy_cabinet').first()
    except Exception:
        all_time_xi, hall_preview, museum_preview, plans, gallery_preview, trophies = [], [], [], [], [], None

    return render_template('index.html',
        next_match=next_match,
        recent_results=recent_results,
        upcoming=upcoming,
        latest_news=latest_news,
        featured_products=featured_products,
        about=about,
        vision=vision,
        mission=mission,
        values=values,
        sponsors=sponsors, sponsor_big=sponsor_big, sponsor_mid=sponsor_mid, sponsor_small=sponsor_small,
        standings=standings,
        performers=performers,
        squad_preview=squad_preview,
        all_time_xi=all_time_xi,
        hall_preview=hall_preview,
        museum_preview=museum_preview,
        membership_plans=plans,
        gallery_preview=gallery_preview,
        trophies=trophies,
    )

@main_bp.route('/club')
def club():
    about = ClubInfo.query.filter_by(key='about_story').first()
    vision = ClubInfo.query.filter_by(key='vision').first()
    mission = ClubInfo.query.filter_by(key='mission').first()
    values = ClubInfo.query.filter_by(key='values').first()
    established = ClubInfo.query.filter_by(key='established').first()
    keys = ['trophy_cabinet', 'home_ground', 'club_stats', 'club_records', 'season_table',
            'club_timeline', 'about_title']
    extra = {k: ClubInfo.query.filter_by(key=k).first() for k in keys}
    # template uses "timeline" — map club_timeline
    extra['timeline'] = extra.get('club_timeline') or ClubInfo.query.filter_by(key='timeline').first()
    try:
        from models import MuseumItem, ClubLegend, AllTimeXI
        museum = MuseumItem.query.filter_by(is_published=True).order_by(MuseumItem.order, MuseumItem.id).all()
        hall = ClubLegend.query.filter_by(is_published=True, category='Hall of Fame').order_by(ClubLegend.order).all()
        watn = ClubLegend.query.filter_by(is_published=True, category='Where Are They Now').order_by(ClubLegend.order).all()
        all_time_xi = AllTimeXI.query.filter_by(is_published=True).order_by(AllTimeXI.order).all()
    except Exception:
        museum, hall, watn, all_time_xi = [], [], [], []
    stadium_img = None
    try:
        s = SiteSetting.query.filter_by(key='home_ground_image').first()
        stadium_img = s.value if s else None
    except Exception:
        pass
    return render_template(
        'club.html',
        about=about, vision=vision, mission=mission, values=values,
        established=established, museum=museum, hall=hall, watn=watn,
        all_time_xi=all_time_xi, stadium_img=stadium_img, **extra
    )

@main_bp.route('/leadership/<int:id>')
def leadership_detail(id):
    person = Leadership.query.get_or_404(id)
    if not person.is_published:
        flash('Official information coming soon.', 'info')
        return redirect(url_for('main.leadership'))
    return render_template('leadership_detail.html', person=person)

@main_bp.route('/leadership')
def leadership():
    section = request.args.get('section')
    q = Leadership.query.filter_by(is_published=True)
    if section and section != 'All':
        q = q.filter_by(section=section)
    leaders = q.order_by(Leadership.order, Leadership.id).all()
    sections = ['All', 'Club Leadership', 'Technology Partner Team', 'Advisory Council']
    return render_template('leadership.html', leaders=leaders, sections=sections, current_section=section or 'All')

@main_bp.route('/squad')
def squad():
    players = Player.query.filter_by(is_published=True).order_by(Player.order, Player.number).all()
    return render_template('squad.html', players=players)

@main_bp.route('/player/<int:id>')
def player(id):
    p = Player.query.get_or_404(id)
    if not p.is_published:
        flash('Player profile not available yet.', 'info')
        return redirect(url_for('main.squad'))
    return render_template('player.html', player=p)

@main_bp.route('/matches')
def matches():
    tab = request.args.get('tab', 'upcoming')
    year = request.args.get('year', 'all')
    upcoming = Match.query.filter_by(status='upcoming', is_published=True).order_by(Match.match_date.asc()).all()
    results_q = Match.query.filter_by(status='finished', is_published=True)
    if year and year != 'all':
        try:
            y = int(year)
            results_q = results_q.filter(
                db.extract('year', Match.match_date) == y
            )
        except ValueError:
            pass
    results = results_q.order_by(Match.match_date.desc()).all()
    standings = LeagueStanding.query.filter_by(is_published=True).order_by(LeagueStanding.position).all()
    performers = TopPerformer.query.filter_by(is_published=True).order_by(TopPerformer.order, TopPerformer.id).all()
    # years present in results for filter chips
    years = sorted({
        m.match_date.year for m in Match.query.filter_by(status='finished', is_published=True).all()
        if m.match_date
    }, reverse=True)
    return render_template(
        'matches.html',
        upcoming=upcoming, results=results, tab=tab,
        standings=standings, performers=performers,
        years=years, current_year=year,
    )

@main_bp.route('/match/<int:id>')
def match_detail(id):
    m = Match.query.get_or_404(id)
    return render_template('match.html', match=m)

@main_bp.route('/news')
def news():
    category = request.args.get('category')
    q = News.query.filter_by(status='published')
    if category:
        q = q.filter_by(category=category)
    articles = q.order_by(News.publish_date.desc()).all()
    categories = db.session.query(News.category).distinct().all()
    return render_template('news.html', articles=articles, categories=[c[0] for c in categories], current_cat=category)

@main_bp.route('/news/<slug>')
def news_detail(slug):
    article = News.query.filter_by(slug=slug, status='published').first_or_404()
    article.views = (article.views or 0) + 1
    db.session.commit()
    related = News.query.filter(News.id != article.id, News.status=='published').order_by(News.publish_date.desc()).limit(3).all()
    return render_template('news_detail.html', article=article, related=related)

@main_bp.route('/gallery')
def gallery():
    category = request.args.get('category')
    q = GalleryImage.query.filter_by(is_published=True)
    if category:
        q = q.filter_by(category=category)
    images = q.order_by(GalleryImage.order, GalleryImage.created_at.desc()).all()
    cats = ['Matchday', 'Training', 'Players', 'Fans', 'Events', 'Behind the Scenes']
    return render_template('gallery.html', images=images, categories=cats, current_cat=category)

@main_bp.route('/membership')
def membership():
    plans = MembershipPlan.query.filter_by(is_active=True).order_by(MembershipPlan.order).all()
    return render_template('membership.html', plans=plans)

@main_bp.route('/membership/register', methods=['GET', 'POST'])
def membership_register():
    plans = MembershipPlan.query.filter_by(is_active=True).order_by(MembershipPlan.order).all()
    plan_id = request.args.get('plan') or request.form.get('plan_id')
    selected = MembershipPlan.query.get(plan_id) if plan_id else (plans[0] if plans else None)

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        dob = request.form.get('date_of_birth')
        address = request.form.get('address', '').strip()
        plan_id = request.form.get('plan_id')

        if not full_name or not phone or not plan_id:
            flash('Please fill all required fields.', 'error')
            return render_template('membership-register.html', plans=plans, selected=selected)

        plan = MembershipPlan.query.get(plan_id)
        if not plan:
            flash('Invalid plan selected.', 'error')
            return redirect(url_for('main.membership'))

        is_free = float(plan.price or 0) == 0
        payment_method = request.form.get('payment_method', '')
        payment_reference = request.form.get('payment_reference', '').strip()

        member = Member(
            membership_number=generate_membership_number(),
            plan_id=plan.id,
            full_name=full_name,
            phone=phone,
            email=email or None,
            date_of_birth=datetime.strptime(dob, '%Y-%m-%d').date() if dob else None,
            address=address,
            status='active' if is_free else 'pending',
            payment_status='free' if is_free else 'submitted',
            payment_method=payment_method or ('Free' if is_free else None),
            payment_reference=payment_reference or None,
            free_tickets=plan.free_tickets or 0,
            expires_at=datetime.utcnow() + timedelta(days=365)
        )
        if 'payment_proof' in request.files and request.files['payment_proof'].filename:
            from utils.helpers import save_upload
            path = save_upload(request.files['payment_proof'], 'members')
            if path:
                member.payment_proof = path
        db.session.add(member)
        db.session.commit()
        session.permanent = True
        session['member_id'] = member.id
        session['membership_number'] = member.membership_number
        session['member_name'] = member.full_name
        if is_free:
            flash('Welcome! Your FREE Fan membership is active.', 'success')
        else:
            flash('Registration received. Admin will verify your payment shortly.', 'success')
        return redirect(url_for('main.membership_card', number=member.membership_number))

    return render_template('membership-register.html', plans=plans, selected=selected)

@main_bp.route('/membership/card')
@main_bp.route('/membership/card/<number>')
def membership_card(number=None):
    member = None
    if number:
        member = Member.query.filter_by(membership_number=number).first()
    if not member and session.get('member_id'):
        member = Member.query.get(session.get('member_id'))
    if not member and session.get('membership_number'):
        member = Member.query.filter_by(membership_number=session.get('membership_number')).first()
    if not member:
        flash('Please complete registration first.', 'info')
        return redirect(url_for('main.membership'))
    # Refresh session so nav shows My Membership
    session.permanent = True
    session['member_id'] = member.id
    session['membership_number'] = member.membership_number
    session['member_name'] = member.full_name
    return render_template('membership-card.html', member=member)

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        message = request.form.get('message', '').strip()
        if name and email and message:
            msg = ContactMessage(name=name, email=email, phone=phone, message=message)
            db.session.add(msg)
            db.session.commit()
            flash('Thank you! Your message has been received. We will get back to you soon.', 'success')
            return redirect(url_for('main.contact'))
        flash('Please fill in all required fields.', 'error')
    return render_template('contact.html')

@main_bp.route('/api/chat', methods=['POST'])
def chat_api():
    """Pathari Bot — real AI when API key is set in Admin Settings."""
    import json
    import os
    import ssl
    import urllib.error
    import urllib.request

    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({
            'reply': 'Namaste! I am Pathari Bot, official fan assistant of Pathari-11 FC.',
            'bot': 'Pathari'
        })

    def get_set(key, default=''):
        try:
            from models import SiteSetting
            s = SiteSetting.query.filter_by(key=key).first()
            if s and s.value is not None and str(s.value).strip() != '':
                return str(s.value).strip()
            return default
        except Exception:
            return default

    api_key = (
        get_set('ai_api_key')
        or current_app.config.get('AI_API_KEY')
        or os.environ.get('AI_API_KEY')
        or ''
    ).strip()
    ai_on = (get_set('ai_enabled', 'true') or 'true').lower() in ('1', 'true', 'yes', 'on')

    if api_key and ai_on:
        try:
            base = (
                get_set('ai_api_base')
                or os.environ.get('AI_API_BASE')
                or 'https://api.x.ai/v1'
            ).rstrip('/')
            model = get_set('ai_model') or os.environ.get('AI_MODEL') or 'grok-3'
            system = get_set('ai_system_prompt') or (
                'You are Pathari (shortcut I$H), the official AI fan assistant of Pathari-11 FC (Pathari, Nepal; Pathari-11). '
                "Answer clearly and directly. Use short answers. Nepali greetings OK (Namaste, Let's Rock Pathri). "
                'Help with matches, squad/players, shop, membership, gallery, contact. '
                'NEVER invent player names or stats — only use LIVE DATA provided below or say official info is on the website. '
                'If the user asks for the squad or player names, list them from LIVE DATA immediately without repeated clarifying questions.'
            )
            # Full website live data for Pathari answers
            try:
                ctx = []
                # Matches
                ups = Match.query.filter_by(status='upcoming', is_published=True).order_by(Match.match_date.asc()).limit(5).all()
                if ups:
                    ctx.append('Upcoming fixtures: ' + '; '.join(
                        'vs %s on %s (%s)' % (m.opponent, m.match_date.strftime('%d %b %Y %H:%M'), m.venue or 'TBC')
                        for m in ups))
                results = Match.query.filter_by(status='completed', is_published=True).order_by(Match.match_date.desc()).limit(5).all()
                if results:
                    ctx.append('Recent results: ' + '; '.join(
                        'vs %s %s-%s' % (m.opponent, m.home_score if m.home_score is not None else '?', m.away_score if m.away_score is not None else '?')
                        for m in results))
                # Squad
                players = Player.query.filter_by(is_published=True).order_by(Player.number.asc(), Player.name.asc()).all()
                if players:
                    lines = []
                    for pl in players:
                        bit = pl.name or 'Unknown'
                        if pl.number is not None:
                            bit = '#%s %s' % (pl.number, bit)
                        if pl.position:
                            bit += ' (%s)' % pl.position
                        lines.append(bit)
                    ctx.append('Published squad: ' + '; '.join(lines))
                else:
                    ctx.append('Squad not published yet — direct users to Our Squad page. Do not invent players.')
                # Leadership
                leaders = Leadership.query.filter_by(is_published=True).order_by(Leadership.order).limit(25).all()
                if leaders:
                    ctx.append('Leadership: ' + '; '.join(
                        '%s (%s)' % (L.name, L.position or L.section or '') for L in leaders if L.name))
                # News (latest)
                news = News.query.filter_by(status='published').order_by(News.id.desc()).limit(8).all()
                if not news:
                    news = News.query.filter_by(status='published').order_by(News.id.desc()).limit(8).all()
                if news:
                    nlines = []
                    for a in news:
                        title = a.title or ''
                        summary = (a.excerpt or a.content or '')[:120].replace('\n', ' ')
                        nlines.append('%s — %s' % (title, summary))
                    ctx.append('Latest official news on website: ' + ' || '.join(nlines))
                    ctx.append('For transfer rumours: only mention what appears in official news above. Do not invent transfer rumours. If none, say no official transfer news published yet and fans should follow club news.')
                else:
                    ctx.append('No news articles published yet. No official transfer rumours on site.')
                # Shop
                prods = Product.query.filter_by(is_active=True).order_by(Product.name).limit(15).all()
                if prods:
                    ctx.append('Shop products: ' + '; '.join(
                        '%s (Rs %s)' % (p.name, p.price) for p in prods))
                ctx.append('Custom jersey: fans can order via Make Your Own Jersey (name + number on back).')
                # Membership
                ctx.append('Membership plans: Fan (free), Gold (1 free match ticket), Premium (2 free match tickets). Register on Membership page.')
                # Contact
                email = get_set('contact_email')
                phone = get_set('contact_phone')
                addr = get_set('contact_address')
                if email or phone or addr:
                    ctx.append('Contact: %s %s %s' % (email or '', phone or '', addr or ''))
                # Club
                tag = get_set('site_tagline') or 'The Pride of Pathari'
                ctx.append('Club: Pathari-11 FC, Nepal. Nickname Pathari-11. Tagline: %s. Tech partner BAM Studio.' % tag)

                system += ' LIVE WEBSITE DATA (answer from this; do not invent): ' + ' | '.join(ctx)
                system += ' RULES: Answer from LIVE WEBSITE DATA first. For squad/players list published squad. For news/transfers only use published news — never invent rumours. Be direct and helpful. Short answers. If unknown, say check the relevant page on pathari11fc site.'
            except Exception as e:
                print('chat context:', e)

            def build_body(use_completion_tokens=False, omit_max=False):
                payload = {
                    'model': model,
                    'messages': [
                        {'role': 'system', 'content': system},
                        {'role': 'user', 'content': message},
                    ],
                }
                # Some models (o1/o3/gpt-5*) reject temperature or max_tokens
                mlow = (model or '').lower()
                is_new = (
                    'openai.com' in base
                    or mlow.startswith('gpt-5')
                    or mlow.startswith('o1')
                    or mlow.startswith('o3')
                    or 'luna' in mlow
                )
                if not is_new and not omit_max:
                    payload['temperature'] = 0.7
                if omit_max:
                    pass
                elif use_completion_tokens or is_new:
                    payload['max_completion_tokens'] = 600
                else:
                    payload['max_tokens'] = 600
                return json.dumps(payload).encode('utf-8')

            def do_request(body_bytes):
                req = urllib.request.Request(
                    base + '/chat/completions',
                    data=body_bytes,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + api_key,
                        'User-Agent': 'PathariFC-Pathari/1.0',
                    },
                    method='POST',
                )
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, timeout=50, context=ctx) as resp:
                    return json.loads(resp.read().decode('utf-8'))

            payload = None
            last_err = None
            for attempt in (
                {'use_completion_tokens': False, 'omit_max': False},
                {'use_completion_tokens': True, 'omit_max': False},
                {'use_completion_tokens': False, 'omit_max': True},
            ):
                try:
                    payload = do_request(build_body(**attempt))
                    break
                except urllib.error.HTTPError as e:
                    err_body = ''
                    try:
                        err_body = e.read().decode('utf-8', errors='ignore')[:400]
                    except Exception:
                        pass
                    last_err = (e.code, err_body)
                    # retry on max_tokens / unsupported param
                    if e.code == 400 and ('max_tokens' in err_body or 'unsupported' in err_body.lower() or 'temperature' in err_body.lower()):
                        continue
                    print('Pathari HTTPError', e.code, err_body)
                    return jsonify({
                        'reply': 'AI error %s. Check Settings API Key / Model. %s' % (e.code, err_body[:150]),
                        'bot': 'Pathari',
                        'ai': False,
                    })
            if payload is None:
                code, err_body = last_err or (400, '')
                return jsonify({
                    'reply': 'AI error %s. Check Settings API Key / Model. %s' % (code, (err_body or '')[:150]),
                    'bot': 'Pathari',
                    'ai': False,
                })
            reply = (payload.get('choices') or [{}])[0].get('message', {}).get('content', '').strip()
            if reply:
                return jsonify({'reply': reply, 'bot': 'Pathari', 'ai': True})
            return jsonify({'reply': 'Pathari AI returned empty. Try again.', 'bot': 'Pathari', 'ai': True})
        except urllib.error.HTTPError as e:
            err_body = ''
            try:
                err_body = e.read().decode('utf-8', errors='ignore')[:200]
            except Exception:
                pass
            print('Pathari HTTPError', e.code, err_body)
            return jsonify({
                'reply': 'AI error %s. Check Settings API Key / Model. %s' % (e.code, err_body[:100]),
                'bot': 'Pathari',
                'ai': False,
            })
        except Exception as e:
            print('Pathari AI error:', repr(e))
            return jsonify({
                'reply': 'AI connection failed: %s. Check Admin Settings API key.' % type(e).__name__,
                'bot': 'Pathari',
                'ai': False,
            })

    if not api_key:
        msg = message.lower()
        if 'match' in msg:
            nm = Match.query.filter_by(status='upcoming', is_published=True).order_by(Match.match_date.asc()).first()
            if nm:
                return jsonify({'reply': 'Next match: vs %s.' % nm.opponent, 'bot': 'Pathari'})
            return jsonify({'reply': "Fixtures coming when season starts. Let's Rock Pathri!", "bot": "Pathari"})
        if 'shop' in msg or 'jersey' in msg:
            return jsonify({'reply': 'Open Official Store or Make Your Own Jersey.', 'bot': 'Pathari'})
        if 'member' in msg:
            return jsonify({'reply': 'Membership: Fan free, Gold, Premium. Open Membership page.', 'bot': 'Pathari'})
        return jsonify({
            'reply': 'No AI API key in Admin Settings yet — only short FAQ. Add xAI/OpenAI key under Settings.',
            'bot': 'Pathari',
            'ai': False,
        })

    return jsonify({'reply': 'AI disabled in Settings. Enable AI and Save.', 'bot': 'Pathari'})


@main_bp.route('/sitemap.xml')
def sitemap():
    from flask import make_response
    pages = [
        url_for('main.index', _external=True),
        url_for('main.club', _external=True),
        url_for('main.leadership', _external=True),
        url_for('main.squad', _external=True),
        url_for('main.matches', _external=True),
        url_for('main.news', _external=True),
        url_for('main.gallery', _external=True),
        url_for('shop.shop', _external=True),
        url_for('main.membership', _external=True),
        url_for('main.contact', _external=True),
        url_for('main.fans_frame', _external=True),
        url_for('main.privacy', _external=True),
        url_for('main.terms', _external=True),
        url_for('main.shipping', _external=True),
        url_for('main.returns', _external=True),
    ]
    for a in News.query.filter_by(status='published').limit(100).all():
        pages.append(url_for('main.news_detail', slug=a.slug, _external=True))
    for p in Product.query.filter_by(is_active=True).limit(100).all():
        pages.append(url_for('shop.product', slug=p.slug, _external=True))
    for pl in Player.query.filter_by(is_published=True).limit(50).all():
        pages.append(url_for('main.player', id=pl.id, _external=True))
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in pages:
        xml.append(f'<url><loc>{p}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>')
    xml.append('</urlset>')
    resp = make_response('\n'.join(xml))
    resp.headers['Content-Type'] = 'application/xml; charset=utf-8'
    return resp

@main_bp.route('/privacy')
def privacy():
    return render_template('legal.html', page_title='Privacy Policy', page_key='privacy')

@main_bp.route('/terms')
def terms():
    return render_template('legal.html', page_title='Terms & Conditions', page_key='terms')

@main_bp.route('/shipping')
def shipping():
    return render_template('legal.html', page_title='Shipping Policy', page_key='shipping')

@main_bp.route('/returns')
def returns():
    return render_template('legal.html', page_title='Return Policy', page_key='returns')

@main_bp.route('/fans-frame')
def fans_frame():
    return render_template('fans-frame.html')


@main_bp.route('/robots.txt')
def robots_txt():
    from flask import Response
    host = request.host_url.rstrip('/')
    body = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/

Sitemap: {host}/sitemap.xml
"""
    return Response(body, mimetype='text/plain')
