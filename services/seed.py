"""Pathari-11 FC seed — official/public data only. No Jhapa FC content."""
from datetime import datetime, timedelta
from models import (
    MuseumItem, ClubLegend, AllTimeXI, LeagueStanding, TopPerformer,
    db, User, ClubInfo, Match, News, ProductCategory, Product, ProductVariant,
    MembershipPlan, Sponsor, SiteSetting, GalleryImage, Player, Leadership
)
from utils.helpers import slugify


def seed_all(app):
    with app.app_context():
        # ---------- Admin ----------
        admin_email = (app.config.get('ADMIN_EMAIL') or 'admin@patharifc.com').strip().lower()
        admin_pass = app.config.get('ADMIN_PASSWORD') or 'admin123'
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            for legacy in (
                'admin@patharifc.com', 'admin@jhapa-fc.com',
                'admin@jhapafc.com', 'admin@localhost',
            ):
                admin = User.query.filter_by(email=legacy).first()
                if admin:
                    admin.email = admin_email
                    break
        if not admin:
            admin = User(
                email=admin_email,
                name='Pathari-11 FC Admin',
                role='admin',
                is_active=True,
            )
            db.session.add(admin)
        admin.role = 'admin'
        admin.is_active = True
        admin.set_password(admin_pass)
        if hasattr(admin, 'totp_enabled'):
            admin.totp_enabled = False
        db.session.commit()
        print('Admin ready:', admin_email)

        # Fast path: skip full seed when already initialized (Vercel cold starts)
        try:
            flag = SiteSetting.query.filter_by(key='_seed_done').first()
            if flag and flag.value == '1':
                # Still ensure admin password works
                print('Seed skipped (already done) — fast start')
                return
        except Exception:
            pass

        # ---------- Club info (Pathari only) ----------
        club_blocks = {
            'about_title': (
                'More Than A Club',
                'The Pride of Pathari',
            ),
            'about_story': (
                'Our Story',
                'Pathari-11 FC (also Pathri 11 / Intra Pathari-11) is based in '
                'Pathari Shanishchare Municipality, Morang, Koshi Province, Nepal. '
                'The club hosts the Intra Pathari Shanishchare Gold Cup and competes '
                'in regional gold-cup football across eastern Nepal, developing local talent '
                'and representing the community with pride.',
            ),
            'vision': (
                'Vision',
                'To become a leading community football club in eastern Nepal that '
                'inspires youth through excellence, integrity and local pride.',
            ),
            'mission': (
                'Mission',
                'To develop local talent, compete in major regional tournaments and '
                'build a sustainable football culture in Pathari Shanishchare.',
            ),
            'values': ('Values', 'Pride • Unity • Excellence • Respect • Community'),
            'established': ('Established', 'Community club — Pathari Shanishchare, Morang'),
            'home_ground': (
                'Home Ground',
                'Pathari Shanishchare Stadium\n'
                'Location: Pathari Shanishchare, Morang, Nepal\n'
                'Home venue of Pathari-11 FC',
            ),
            'trophy_cabinet': (
                'Trophy Cabinet',
                'Satisa Gold Cup|2025|Champions (4–2 on penalties vs Betana United)\n'
                'Pathari Shanishchare Gold Cup 2082|2025|Finalists / Organisers\n'
                'Ilam Gold Cup|2026|Opening win vs hosts Red Horse (penalties)',
            ),
            'club_timeline': (
                'Club Timeline',
                '2024|Honoured Nepal international Saru Limbu (hometown recognition)\n'
                '2025|Hosted 2nd Intra Pathari Shanishchare Gold Cup (international invitational)\n'
                '2025|Beat Brigade Boys & NRT; reached Gold Cup final\n'
                '2025|Champions — 2nd Satisa Gold Cup (Kerabari, Morang)\n'
                '2026|Winning start at 3rd Ilam Gold Cup',
            ),
            'season_table': (
                'Season by Season',
                '2025|Pathari Shanishchare Gold Cup|—|—|—|—|—|—|Finalists / Hosts\n'
                '2025|Satisa Gold Cup|—|—|—|—|—|—|Champions\n'
                '2026|Ilam Gold Cup|—|—|—|—|—|—|Opening win',
            ),
            'club_records': (
                'Club Records',
                'Satisa Gold Cup champions 2025\n'
                'Best Player of Tournament: Samir Chhetri (GK)\n'
                'Hosts of Intra Pathari Shanishchare Gold Cup',
            ),
        }
        for key, (title, content) in club_blocks.items():
            row = ClubInfo.query.filter_by(key=key).first()
            if not row:
                db.session.add(ClubInfo(key=key, title=title, content=content))
            # Do NOT overwrite existing — admin edits must persist

        # Clear Jhapa leftover club_info keys
        for bad_key in (
            'champions_2022', 'fair_play', 'nsl_campaign',
            'about_achievements',
        ):
            row = ClubInfo.query.filter_by(key=bad_key).first()
            if row:
                db.session.delete(row)

        # ---------- Site settings ----------
        settings = {
            'site_title': 'Pathari-11 FC | Official Football Club',
            'site_tagline': 'ONE CLUB. ONE PRIDE.',
            'contact_address': 'Pathari Shanishchare, Morang, Koshi Province, Nepal',
            'contact_email': 'info@pathari11fc.com',
            'bam_name': 'BAM Studio',
            'bam_url': 'https://argan.com.np/',
        }
        for key, val in settings.items():
            if not SiteSetting.query.filter_by(key=key).first():
                db.session.add(SiteSetting(key=key, value=val))
        db.session.commit()
        print('Club info + settings ready')

        # ---------- Matches (Pathari documented only) — only if empty ----------
        pathari_matches = [
            dict(
                opponent='Brigade Boys Club',
                competition='Pathari Shanishchare Gold Cup 2082',
                match_date=datetime(2025, 11, 2, 14, 0),
                venue='Pathari Shanishchare Stadium, Morang',
                status='finished',
                home_score=1, away_score=0, is_home=True, is_published=True, match_report="Organiser Pathari-11 beat Brigade Boys 1-0. Scorer: Mixan Das (50'). Man of the Match: Mixan Das.",
            ),
            dict(
                opponent='New Road Team (NRT)',
                competition='Pathari Shanishchare Gold Cup 2082',
                match_date=datetime(2025, 11, 6, 14, 0),
                venue='Pathari Shanishchare Stadium, Morang',
                status='finished',
                home_score=1, away_score=0, is_home=True, is_published=True, match_report="Semi-final. Scorer: Saurya Raut (25'). Man of the Match: Saurya Raut.",
            ),
            dict(
                opponent='Salhesh Yuwa Club (Siraha)',
                competition='Pathari Shanishchare Gold Cup 2082',
                match_date=datetime(2025, 11, 8, 14, 0),
                venue='Pathari Shanishchare Stadium, Morang',
                status='finished',
                home_score=None, away_score=None, is_home=True, is_published=True, match_report='Final of 2nd Intra Pathari Shanishchare Gold Cup 2082 (international invitational).',
            ),
            dict(
                opponent='Betana United FC (Belbari)',
                competition='Satisa Gold Cup',
                match_date=datetime(2025, 12, 24, 14, 0),
                venue='Satisa Sporting Club Ground, Kerabari, Morang',
                status='finished',
                home_score=0, away_score=0, is_home=False, is_published=True, match_report='Final: 0-0 then Pathari-11 won 4-2 on penalties. Best Player of Tournament: GK Samir Chhetri. Prize: Rs 202,222.',
            ),
            dict(
                opponent='Red Horse FC (Ilam)',
                competition='Ilam Gold Cup',
                match_date=datetime(2026, 4, 18, 15, 0),
                venue='Thulo Tundikhel, Ilam',
                status='finished',
                home_score=0, away_score=0, is_home=False, is_published=True, match_report='Opening match of 3rd Ilam Gold Cup. Pathari-11 won 4-2 on penalties. Player of the Match: Ashish Lawati.',
            ),
        ]
        if Match.query.count() == 0:
            for m in pathari_matches:
                db.session.add(Match(**m, is_demo=False))
            print('Seeded Pathari matches')
        # League table: only clear if empty seed path — never wipe admin table data every boot
        # LeagueStanding left as admin-managed

        # ---------- Squad (documented Pathari names only) ----------
        # Only ADD missing players — never unpublish admin work
        known_players = [
            dict(
                name='Samir Chhetri', number=1, position='Goalkeeper (GK)',
                nationality='Nepal', order=1,
                career='Best Player — Satisa Gold Cup 2025 · Pathari-11 · later linked with Machhindra FC',
            ),
            dict(
                name='Saurya Raut', number=10, position='Forward / Midfielder',
                nationality='Nepal', order=2,
                career='Scored winner vs NRT in Pathari Shanishchare Gold Cup 2082 semi-final',
            ),
            dict(
                name='Mixan Das', number=11, position='Forward',
                nationality='Nepal', order=3,
                career='Jersey #11 · Scored vs Brigade Boys · Man of the Match',
            ),
            dict(
                name='Ashish Lawati', number=None, position='Midfielder',
                nationality='Nepal', order=4,
                career='Player of the Match — Ilam Gold Cup vs Red Horse FC',
            ),
            dict(
                name='Apson Gurung', number=None, position='Player',
                nationality='Nepal', order=5,
                career='Player of the Match (club reports)',
            ),
        ]
        for pl in known_players:
            row = Player.query.filter_by(name=pl['name']).first()
            if not row:
                row = Player(
                    name=pl['name'],
                    position=pl['position'],
                    number=pl.get('number'),
                    nationality=pl.get('nationality', 'Nepal'),
                    career=pl.get('career'),
                    order=pl['order'],
                    is_published=True,
                )
                db.session.add(row)
            # existing rows: never overwrite admin fields

        # ---------- Top performers (only if empty) ----------
        if TopPerformer.query.count() == 0:
          for i, (name, cat, val, season) in enumerate([
            ('Samir Chhetri', 'Best Player', 1, 'Satisa 2025'),
            ('Saurya Raut', 'Goals', 1, 'Gold Cup 2082'),
            ('Mixan Das', 'Goals', 1, 'Gold Cup 2082'),
            ('Ashish Lawati', 'Player of Match', 1, 'Ilam Gold Cup'),
        ]):
            photo = None
            pl = Player.query.filter_by(name=name).first()
            if pl and pl.photo:
                photo = pl.photo
            db.session.add(TopPerformer(
                name=name, category=cat, value=val, team='Pathari-11 FC',
                photo=photo, order=i, is_published=True, season=season,
            ))

        # ---------- Leadership (only if empty) ----------
        leaders = [
            dict(
                name='Suman Bik', position='President',
                section='Club Leadership', order=1,
                bio='President of Pathari-11 Football Club (Pathari Shanishchare, Morang).',
                is_published=True,
            ),
            dict(
                name='Keshar Rai', position='Secretary',
                section='Club Leadership', order=2,
                bio='Secretary of Pathari-11 Football Club.',
                is_published=True,
            ),
            dict(
                name='BAM Developers', position='Full Stack Developer',
                section='Technology Partner Team', order=20,
                bio='Official technology partner team — website, shop, membership platform.',
                is_published=True,
            ),
            dict(
                name='BAM Developers', position='UI/UX Designer',
                section='Technology Partner Team', order=21,
                bio='Design system, neon glassmorphism UI for Pathari-11 FC digital platform.',
                is_published=True,
            ),
            dict(
                name='BAM Developers', position='Video Editor',
                section='Technology Partner Team', order=22,
                bio='Matchday and club content production support.',
                is_published=True,
            ),
            dict(
                name='BAM Developers', position='Full Stack Engineer',
                section='Technology Partner Team', order=23,
                bio='Infrastructure, database and deployment (Vercel / Neon / Cloudinary).',
                is_published=True,
            ),
        ]
        if Leadership.query.count() == 0:
            for L in leaders:
                db.session.add(Leadership(**L))
            print('Seeded leadership')

        # ---------- Hall of Fame (only if empty) ----------
        if ClubLegend.query.count() == 0:
          for i, L in enumerate([
            dict(
                name='Samir Chhetri', role='Player', position='Goalkeeper',
                nationality='Nepal', era='2025',
                achievement='Best Player of Tournament — Satisa Gold Cup 2025',
                tags='Players,Achievements',
                biography='Pathari-11 goalkeeper adjudged Best Player at the 2nd Satisa Gold Cup.',
                category='Hall of Fame', order=0, is_published=True,
            ),
            dict(
                name='Saru Limbu', role='Player', position='Midfielder',
                nationality='Nepal', era='Hometown honour 2024',
                achievement="Honoured by Pathari-11 FC — Nepal women's national team",
                tags='Players,Club Legends',
                biography='Nepal women\'s national midfielder from Pathari Shanishchare; '
                          'honoured by the club with certificate and cash (2024).',
                category='Hall of Fame', order=1, is_published=True,
            ),
            dict(
                name='Suman Bik', role='Staff', position='President',
                nationality='Nepal', era='2024–',
                achievement='Club President',
                tags='Club Legends',
                biography='President of Pathari-11 Football Club.',
                category='Hall of Fame', order=2, is_published=True,
            ),
        ]):
            db.session.add(ClubLegend(**L))

        # ---------- All-Time XI (only if empty) ----------
        if AllTimeXI.query.count() == 0:
          for pos, order, name, note in [
            ('GK', 1, 'Samir Chhetri', 'Satisa Gold Cup Best Player'),
            ('MF', 2, 'Saurya Raut', 'Winner vs NRT'),
            ('FW', 3, 'Mixan Das', '#11 · vs Brigade Boys'),
            ('MF', 4, 'Ashish Lawati', 'Ilam Gold Cup PoM'),
        ]:
            db.session.add(AllTimeXI(
                position=pos, slot=order, name=name, note=note,
                order=order, is_published=True,
            ))

        # ---------- News ----------
        if News.query.filter(News.title.ilike('%Pathari%')).count() == 0:
            news_items = [
                (
                    'Pathari-11 lift Satisa Gold Cup',
                    'Match',
                    'Intra Pathari-11 defeated Betana United 4-2 on penalties to win the second Satisa Gold Cup.',
                    'Pathari-11 FC won the second Satisa Gold Cup open knockout tournament in Kerabari, Morang. '
                    'After a goalless draw, Pathari-11 prevailed 4-2 in the tiebreaker. '
                    'Goalkeeper Samir Chhetri was named Best Player of the tournament.',
                    datetime(2025, 12, 24),
                ),
                (
                    'Pathari-11 beat NRT to reach Gold Cup final',
                    'Match',
                    'Saurya Raut scored the only goal as hosts Pathari-11 eliminated New Road Team.',
                    'In the second semi-final of the Intra Pathari Shanishchare Gold Cup 2082, '
                    'Pathari-11 defeated Kathmandu\'s NRT 1-0. Saurya Raut scored in the 25th minute '
                    'and was named Man of the Match.',
                    datetime(2025, 11, 6),
                ),
                (
                    'Pathari-11 honour Nepal international Saru Limbu',
                    'Club',
                    'Club president Suman Bik and secretary Keshar Rai honoured national midfielder Saru Limbu.',
                    'Pathari-11 Football Club honoured Nepal women\'s national team midfielder Saru Limbu '
                    'in her hometown Pathari Shanishchare with a certificate and cash award of Rs 25,000.',
                    datetime(2024, 11, 10),
                ),
            ]
            for title, cat, excerpt, content, pdt in news_items:
                slug = slugify(title)
                if not News.query.filter_by(slug=slug).first():
                    db.session.add(News(
                        title=title, slug=slug, category=cat,
                        excerpt=excerpt, content=content,
                        author='Pathari-11 FC Media',
                        publish_date=pdt, status='published', is_demo=True,
                    ))

        # ---------- Shop categories & demo products ----------
        cats = [
            'Jerseys', 'Training', 'Tracksuits', 'T-Shirts',
            'Hoodies', 'Caps', 'Scarves', 'Accessories',
        ]
        for i, name in enumerate(cats):
            if not ProductCategory.query.filter_by(name=name).first():
                db.session.add(ProductCategory(
                    name=name, slug=slugify(name), order=i,
                ))
        db.session.flush()

        if Product.query.count() == 0:
            products_data = [
                ('Pathari-11 FC Home Jersey', 'Jerseys', 2999,
                 'Official home kit. Premium fabric, embroidered crest.', True),
                ('Pathari-11 FC Away Jersey', 'Jerseys', 2999,
                 'Official away kit. Clean design for the road.', True),
                ('Training Top', 'Training', 1999,
                 'Lightweight training top for the pitch.', True),
                ('Full Tracksuit', 'Tracksuits', 4499,
                 'Premium tracksuit jacket and pants set.', True),
                ('Club T-Shirt', 'T-Shirts', 1299,
                 'Everyday cotton t-shirt with club crest motif.', True),
                ('Hoodie – Pathari-11', 'Hoodies', 2499,
                 'Warm hoodie featuring Pride of Pathari design.', True),
                ('Official Cap', 'Caps', 799,
                 'Adjustable cap with embroidered logo.', False),
                ('Supporters Scarf', 'Scarves', 999,
                 'Classic woven scarf in club colours.', False),
            ]
            for name, cat_name, price, desc, featured in products_data:
                cat = ProductCategory.query.filter_by(name=cat_name).first()
                prod = Product(
                    name=name, slug=slugify(name), description=desc,
                    price=price, category_id=cat.id if cat else None,
                    stock=50, is_demo=True, is_active=True, is_featured=featured,
                )
                db.session.add(prod)
                db.session.flush()
                for size in ['S', 'M', 'L', 'XL', 'XXL']:
                    db.session.add(ProductVariant(
                        product_id=prod.id, size=size, stock=15,
                        sku=f'{prod.slug[:10]}-{size}',
                    ))

        # ---------- Membership ----------
        NL = chr(10)
        desired = [
            ('Free', 0,
             'FREE membership' + NL + 'Digital membership card' + NL +
             'Matchday updates' + NL + 'Fan community access', 0, 0),
            ('Bronze', 200,
             'All Free benefits' + NL + '5% shop discount' + NL +
             'Member newsletters' + NL + 'Priority match updates', 0, 1),
            ('Silver', 500,
             'All Bronze benefits' + NL + '10% shop discount' + NL +
             '1 FREE match ticket per season' + NL + 'Member-only content', 1, 2),
            ('Gold', 1000,
             'All Silver benefits' + NL + '15% shop discount' + NL +
             '2 FREE match tickets per season' + NL + 'Exclusive events' + NL +
             'Personalised digital card', 2, 3),
        ]
        for name, price, benefits, tickets, order in desired:
            plan = MembershipPlan.query.filter_by(name=name).first()
            if not plan:
                plan = MembershipPlan(name=name, slug=slugify(name))
                db.session.add(plan)
            plan.slug = slugify(name)
            plan.price = price
            plan.benefits = benefits
            plan.free_tickets = tickets
            plan.order = order
            plan.is_active = True
        keep = {d[0] for d in desired}
        for plan in MembershipPlan.query.all():
            if plan.name not in keep:
                plan.is_active = False
        print('Membership: Free0 / Bronze200 / Silver500 / Gold1000')

        # ---------- Sponsor / tech partner ----------
        if not Sponsor.query.filter_by(name='BAM Studio').first():
            db.session.add(Sponsor(
                name='BAM Studio',
                category='Web & Technology Partner',
                website='https://argan.com.np/',
                is_published=True,
                order=0,
            ))

        # ---------- Gallery placeholders ----------
        if GalleryImage.query.count() == 0:
            for cat in ['Matchday', 'Training', 'Fans', 'Events', 'Behind the Scenes']:
                for i in range(2):
                    db.session.add(GalleryImage(
                        title=f'{cat} {i + 1}',
                        category=cat,
                        image='/static/img/placeholder.png',
                        caption=f'Pathari-11 FC — {cat}',
                        is_demo=True,
                        is_published=True,
                    ))

        db.session.commit()
        print('Pathari-11 FC seed complete (no Jhapa data)')
        try:
            flag = SiteSetting.query.filter_by(key='_seed_done').first()
            if not flag:
                db.session.add(SiteSetting(key='_seed_done', value='1'))
            else:
                flag.value = '1'
            db.session.commit()
        except Exception:
            pass
