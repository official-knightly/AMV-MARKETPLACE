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
