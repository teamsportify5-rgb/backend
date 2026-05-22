# AI image storage (Vercel Blob or Supabase)

Generated images are uploaded to cloud storage in production. The API stores a **public HTTPS URL** in `generated_image_url` (works in `<img>` tags without JWT).

## Choose a provider

Set `IMAGE_STORAGE_PROVIDER` to `vercel` or `supabase`, or leave unset for auto-detect:

| Auto-detect order | Required env |
|-------------------|--------------|
| `vercel` | `BLOB_READ_WRITE_TOKEN` |
| `supabase` | `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` |
| `local` (dev only) | Neither set — files under `static/images/ai-generated/` |

## Option A: Vercel Blob (recommended on Vercel)

1. Vercel dashboard → **Storage** → **Create Blob store** → link to this project.
2. Vercel adds `BLOB_READ_WRITE_TOKEN` to the project env (or copy from store settings).
3. Deploy / restart the API.

```env
IMAGE_STORAGE_PROVIDER=vercel
BLOB_READ_WRITE_TOKEN=vercel_blob_rw_...
```

URLs look like: `https://….public.blob.vercel-storage.com/ai-generated/…`

## Option B: Supabase Storage

1. Supabase dashboard → **Storage** → **New bucket** → name: `ai-images` → **Public bucket**.
2. Project Settings → **API** → copy **Project URL** and **service_role** key (server only; never expose to the frontend).

```env
IMAGE_STORAGE_PROVIDER=supabase
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_STORAGE_BUCKET=ai-images
```

URLs look like: `https://YOUR_PROJECT_REF.supabase.co/storage/v1/object/public/ai-images/ai-generated/…`

Optional SQL if the bucket is not public:

```sql
create policy "Public read ai images"
on storage.objects for select
using ( bucket_id = 'ai-images' );
```

## Local development (no cloud)

Omit blob/Supabase vars. Images save under `static/images/ai-generated/` and are served at `/static/...`.

Optional full URL in API responses:

```env
API_PUBLIC_BASE_URL=http://localhost:8000
```

## Verify

1. `POST /ai/image` with Bearer token and `prompt` form field.
2. Response `generated_image_url` should be `https://…` (not `/static/…` when cloud is configured).
3. Open that URL in a browser (no auth) → image loads.
4. `GET /ai/images` returns the same URL.
