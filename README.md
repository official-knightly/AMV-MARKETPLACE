# VORTEX — AMV Marketplace

A full-stack marketplace for buying and selling AMVs, anime edits, gaming montages, TikTok edits, and motion graphics.

## Core features

- Homepage, searchable marketplace, individual listing pages, seller profiles.
- Email/password registration and login, plus optional Google sign-in.
- Buyer and seller dashboards, seller video/thumbnail uploads, order delivery and revisions.
- Stripe Checkout for buyer payments. No phone/SMS OTP and no Razorpay checkout.
- 5% marketplace commission by default; seller receives 95% of the order value before any separate payout fees.
- Buyer/seller order chat with server-side AI safety checks.
- NVIDIA-powered listing review, AI delivery/dispute assistance, and a marketplace discovery assistant.
- Admin dashboard for order disputes and copyright reports.
- Background remover, green-screen processing, and edit fingerprint/plagiarism checks.

## Stack

- Frontend: Next.js 14, React 18, Tailwind CSS, Zustand.
- Backend: Flask, Flask-SQLAlchemy, Flask-JWT-Extended.
- Database: SQLite locally; PostgreSQL recommended for deployment.
- Payments: Stripe Checkout and optional Stripe Connect onboarding.
- AI: NVIDIA NIM OpenAI-compatible Chat Completions API; Nemotron is the configured default.

## Local setup

### Backend

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows; on macOS/Linux use cp
python app.py
```

### Frontend

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Required backend environment

- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `DATABASE_URL`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET` for signed Stripe webhook events
- `FRONTEND_URL`
- `NVIDIA_API_KEY` for NVIDIA AI features
- `ADMIN_EMAILS` — comma-separated email allowlist for admin dashboard access

Optional:
- `NVIDIA_MODEL` (default: `nvidia/nemotron-3.5-lightning-30b-a3b`)
- `NVIDIA_ASSISTANT_MODEL` (default: `nvidia/nemotron-3.5-lightning-30b-a3b`)
- `GOOGLE_CLIENT_ID` and frontend `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
- `PLATFORM_FEE_RATE` (default: `0.05`)

## Deployment notes

- Deploy the Flask service from `render.yaml`.
- Deploy the Next.js frontend to Vercel or Render.
- Set frontend `NEXT_PUBLIC_API_URL` to the deployed Flask service URL.
- Set `FRONTEND_URL` to the deployed frontend origin.
- Configure the Stripe webhook URL as `/api/payment/stripe/webhook`.
- Set `ADMIN_EMAILS` on the backend to enable the admin dashboard for the chosen account.
- Never put NVIDIA or Stripe secret keys in frontend variables or source code.

## Payment and escrow notes

Stripe Checkout collects buyer payments. The application tracks order funds and only releases the seller's internal marketplace balance after buyer confirmation or an authorized admin decision. This application should not be described as a regulated escrow provider. Stripe Connect availability and marketplace transfer support depend on the account's country and Stripe approval; verify the current Stripe account capabilities before enabling automatic seller payouts.

## Build plan

This project is being completed in stages: first stabilize authentication, deployment, and existing buyer/seller flows; then complete the admin moderation workflows; then run end-to-end payment, upload, chat, and mobile regression checks. See `BUILD_ROADMAP.md`.
