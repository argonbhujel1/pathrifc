# Pathari-11 FC Website — Feature Guide

## Public site
| Page | What it shows |
|------|----------------|
| **Home** | Hero (logo + bg from Settings), Next Match, Top Performers, News, About, Squad preview, Store, Sponsors, BAM Tech Partner |
| **Club** | Story, vision, mission, values (Admin can edit Club Info / Settings) |
| **Leadership** | Shield cards grouped by section: Executive Board, Advisory Council (coaches), Technical Team (BAM ×4) |
| **Our Squad** | Published players (Admin → Players). Photos + number + position |
| **Matches** | Fixtures, results, league table, top performers |
| **News** | Published articles with featured images |
| **Gallery** | Published photos by category |
| **Shop** | Products, cart, checkout, custom jersey |
| **Membership** | Fan (free), Gold (1 ticket), Premium (2 tickets). After join → **My Membership** in nav |
| **Fans Frame** | Upload photo + name + frame style → download |
| **Contact** | Form + email/phone/address/social from Admin → Settings |
| **Legal** | Privacy, Terms, Shipping, Returns (footer links) |

## Admin (`/admin/login`)
| Section | Use |
|---------|-----|
| **Settings** | Club logo (used everywhere), BAM logo, home/loading/hero/about images, contact, social |
| **Sponsors** | Title / Principal / Official partner logos (clickable) |
| **Players / Leadership** | Photos, publish toggle |
| **Matches** | Opponent + **opponent logo** |
| **News / Products / Gallery** | Image upload (Cloudinary on Vercel) |
| **Members / Orders / Messages** | Verify payments, orders, replies |

## Logo
Upload once in **Admin → Settings → Club Logo**. It appears on: navbar, favicon, loading screen, membership card, chat, match crest, admin tab icon.

## Membership nav
- Before join: **Membership** + **Join Now**
- After join: **My Membership** only (session stores membership_number)

## Theme
Automatic **dark ↔ gold** every 10 seconds (no toggle button).
