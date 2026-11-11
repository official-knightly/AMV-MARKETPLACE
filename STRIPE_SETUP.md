# Stripe setup

The marketplace uses Stripe-hosted Checkout for buyer payments and Stripe Connect-hosted onboarding for seller verification. Card details and identity documents are collected by Stripe, not stored by this app.

## Backend environment

Set these values in the backend hosting provider (never expose secret keys in Next.js variables):

- `STRIPE_SECRET_KEY`: Stripe secret key (`sk_test_...` while testing).
- `STRIPE_WEBHOOK_SECRET`: webhook signing secret (`whsec_...`).
- `STRIPE_CONNECT_COUNTRY`: two-letter country code for seller connected accounts, subject to Stripe approval and availability.
- `FRONTEND_URL`: deployed Next.js origin, for example `https://your-marketplace.example`.

Keep `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` private. Do not put either in a `NEXT_PUBLIC_*` variable.

## Webhook

In Stripe Dashboard, add this endpoint:

`https://YOUR-BACKEND-HOST/api/payment/stripe/webhook`

Subscribe to:

- `checkout.session.completed`

Copy the endpoint signing secret into `STRIPE_WEBHOOK_SECRET`. The success redirect also confirms the Checkout Session from the authenticated buyer's account, so the order can be reconciled even if the webhook arrives slightly later.

## Seller verification

The Seller Wallet's **Verify with Stripe** button creates a Stripe Connect Express account and redirects the seller to Stripe-hosted onboarding. The status endpoint checks Stripe's `details_submitted` and `payouts_enabled` values; returning from onboarding alone does not mean verification succeeded.

## Important availability note for India

Stripe says India-based Stripe accounts and Connect are invite-only. Stripe's India marketplace guidance also lists restrictions on separate charges and transfers and standalone transfers. Therefore, this repository does **not** pretend that a Stripe Connect verification result automatically enables marketplace seller payouts. Get Stripe's written approval for the marketplace's exact funds flow before enabling live payments or payouts. The existing wallet withdrawal process remains separate.

## Testing

1. Configure Stripe test-mode keys and a public HTTPS backend URL.
2. Add the webhook above and use its test signing secret.
3. Test Checkout with Stripe's published test payment details.
4. Complete seller onboarding in test mode and confirm the status endpoint reports the actual Stripe account state.
5. Do not switch to live keys until Stripe approves the business and the complete marketplace funds flow.


## Order chat, cancellation, and AI Guard

- Every paid order has an authenticated buyer/seller chat at the Orders page. Messages are stored against that order and only its two participants can read or send them.
- The chat API applies deterministic checks for contact-detail sharing, off-platform payment requests, suspicious links, and abusive language. If configured, it also asks NVIDIA NIM's OpenAI-compatible Chat Completions endpoint (default model: `moonshotai/kimi-k3`) to classify message safety. Provider outages fall back to deterministic checks.
- Configure `NVIDIA_API_KEY` as a private backend environment variable and optionally `NVIDIA_MODEL`. Never paste the key into source code, browser variables, commits, or public issue reports. If a key was exposed, revoke it and create a replacement.
- Either party can request cancellation. Paid orders are cancelled only after both buyer and seller approve; the backend then requests a refund against the original Stripe Checkout payment. Unpaid pending orders can be cancelled without a refund.
- AI moderation is a safety filter, not a dispute judge. AI does not decide who gets refunded or release money automatically from a chat classification. Use the order dispute/support flow for contested cases.
- Stripe Checkout is the only enabled order checkout route. Legacy Razorpay, direct UPI checkout, and manual wallet-credit refund endpoints are disabled.


## Marketplace discovery assistant

- Set `NVIDIA_API_KEY` as a backend-only secret.
- `NVIDIA_ASSISTANT_MODEL` defaults to `nvidia/nemotron-3.5-lightning-30b-a3b`; the assistant calls NVIDIA's OpenAI-compatible Chat Completions endpoint server-side and returns live gig matches from the database.
- The floating assistant is available across the frontend. It can ask about style, anime/game, budget, and deadline, and links only to real active listings returned by the backend.
- The assistant uses a non-streaming server request for reliable JSON responses to the web client. The API key is never sent to the browser.
