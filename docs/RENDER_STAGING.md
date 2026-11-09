# Render staging deployment

This repository's `render.yaml` creates a **free staging environment only**:

- `padala-nico-staging-web`: public Next.js test site;
- `padala-nico-staging-api`: public FastAPI test endpoint, with browser traffic normally proxied through the web site;
- `padala-nico-staging-db`: private Render PostgreSQL instance.

It intentionally uses `PADALA_ENV=staging`, disables billing and email
verification, and stores uploads in temporary service storage. It must contain
only fictional test accounts, family names, amounts, receipts, and email
addresses. Do not enter a payment credential, an Xendit key, or real family
information.

## Deploy

1. In the Render Dashboard select **New +** then **Blueprint**.
2. Select `Ncambelisa/padala`, branch `main`, and confirm the detected
   `render.yaml` file.
3. Review the three free resources. Confirm that the database access list is
   empty (private network only), then create the Blueprint.
4. Wait for both web services to become live. Confirm that the web URL is
   `https://padala-nico-staging-web.onrender.com`. If Render assigns a different
   `onrender.com` hostname, update the API service's `APP_URL` and
   `ALLOWED_ORIGINS` to that exact `https://` URL, then redeploy the API. No
   secret needs to be entered.
5. Open the **web** service URL, create a fictional household, sign in again,
   add a fictional padala, and upload only a non-sensitive sample image.

The API health endpoint is `/api/v1/health`. It should return `"environment":
"staging"` and `"storage": "database"`.

## Expected limitations

- Free services can sleep, so the first request after inactivity can be slow.
- The staging database and temporary uploads are not a backup or retention
  system. Treat all records as disposable test data.
- Billing, Xendit, outbound email, OCR, background email delivery, persistent
  uploads, production privacy notice, malware scanning, and production rate
  limiting remain intentionally off.
- `render.yaml` is not a production template. Production requires separately
  approved managed storage, secure shared rate limiting, scanner, email,
  domain, legal/privacy configuration, backups, monitoring, and a live Xendit
  verification pass.
