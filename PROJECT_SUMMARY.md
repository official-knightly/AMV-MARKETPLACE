# VORTEX Marketplace — Project Summary

VORTEX is a marketplace for buyers to commission AMVs, anime edits, gaming montages, TikTok edits, and motion graphics from independent video editors.

## Main product areas

- Homepage and searchable marketplace.
- Listing/product detail pages and seller profiles.
- Email/password and Google authentication.
- Seller uploads and listing management.
- Buyer and seller dashboards.
- Stripe Checkout, order status, seller earnings, and payout onboarding.
- Buyer/seller order chat, revisions, cancellation, and delivery confirmation.
- AI Guard for listing and chat safety.
- NVIDIA-powered marketplace assistant and AI-assisted listing/dispute workflows.
- Admin dashboard for disputes and copyright reports.
- Image background removal, green-screen processing, and edit fingerprint checks.

## Technology

- Next.js 14, React 18, Tailwind CSS, Zustand.
- Flask, SQLAlchemy, Flask-JWT-Extended.
- SQLite for local development; PostgreSQL for hosted deployment.
- Stripe Checkout and optional Stripe Connect onboarding.
- NVIDIA NIM through the OpenAI-compatible Chat Completions API.

## Payment model

- Stripe Checkout is the buyer checkout provider.
- Default platform commission is 5% (`PLATFORM_FEE_RATE=0.05`).
- Seller receives 95% of the order value before separate payout costs.
- Phone/SMS OTP, Razorpay checkout, and direct UPI checkout are not part of the active flow.
- The app tracks held/released/refunded order states; it is not a regulated escrow provider. Stripe Connect marketplace transfers depend on Stripe account eligibility and country support.

## Important backend routes

- `/api/auth/register`, `/api/auth/login`, `/api/auth/google`, `/api/auth/me`
- `/api/gigs`, `/api/gigs/<id>`, `/api/upload/video`, `/api/upload/image`
- `/api/orders/create`, `/api/orders/my-orders`, `/api/orders/<id>/deliver`, `/api/orders/<id>/complete`
- `/api/payment/stripe/create-checkout-session`, `/api/payment/stripe/confirm`, `/api/payment/stripe/webhook`
- `/api/chat/messages/<order_id>`, `/api/orders/<id>/cancel`
- `/api/ai/marketplace-assistant`, `/api/ai/guard/status`
- `/api/gigs/<id>/copyright-report`
- `/api/admin/overview`, `/api/admin/disputes`, `/api/admin/copyright-reports`

## Deployment configuration

Backend secrets/settings:
- `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `FRONTEND_URL`
- `NVIDIA_API_KEY`, `NVIDIA_MODEL`, `NVIDIA_ASSISTANT_MODEL`
- `ADMIN_EMAILS` — comma-separated allowlist for admin access
- `PLATFORM_FEE_RATE=0.05`

Frontend:
- `NEXT_PUBLIC_API_URL` — deployed Flask API origin
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` — optional Google sign-in

See `README.md` for setup and `BUILD_ROADMAP.md` for the staged completion plan.
