# Pathari-11 FC — Deploy to Vercel + Neon + Cloudinary

## 1. Neon (PostgreSQL)

1. Create project at https://console.neon.tech
2. Copy **Connection string** (URI)
3. Example:
   `postgresql://user:password@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`

## 2. Cloudinary (images)

1. Sign up at https://cloudinary.com
2. Dashboard → copy **Cloud name**, **API Key**, **API Secret**
3. All admin uploads go to Cloudinary (required on Vercel — disk is ephemeral)

## 3. Vercel

```bash
cd pathari-11-fc
npx vercel login
npx vercel
```

Or connect GitHub repo in Vercel Dashboard → Import.

### Environment variables (Vercel → Project → Settings → Environment Variables)

| Name | Value |
|------|--------|
| `SECRET_KEY` | long random string |
| `DATABASE_URL` | Neon connection URI |
| `CLOUDINARY_CLOUD_NAME` | from Cloudinary |
| `CLOUDINARY_API_KEY` | from Cloudinary |
| `CLOUDINARY_API_SECRET` | from Cloudinary |
| `CLOUDINARY_FOLDER` | `pathari-11-fc` |
| `ADMIN_EMAIL` | your admin email |
| `ADMIN_PASSWORD` | strong password |
| `SEED_ON_START` | `true` (first deploy), then `false` |
| `SESSION_COOKIE_SECURE` | `true` |

Redeploy after setting env vars.

### First deploy

1. Set all env vars
2. Deploy
3. Open site → tables auto-create + seed (players, leadership, admin)
4. Login `/admin/login`
5. Set `SEED_ON_START=false` for later deploys (optional)

## 4. Local with Neon + Cloudinary

```bash
# .env
DATABASE_URL=postgresql://...@neon.tech/neondb?sslmode=require
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...

pip install -r requirements.txt
python app.py
```

## Notes

- **SQLite** still works locally if `DATABASE_URL` is empty
- **Logo / gallery / players** images must use Cloudinary on Vercel
- Admin: `/admin/login`
