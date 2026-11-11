# VORTEX Marketplace — Completion Roadmap

The existing black/white theme, typography, brand identity, and page layouts are protected. Work should repair and complete the current interface rather than introduce a new design system.

## Round 1 — Stabilize the foundation

- Fix duplicate navigation and scattered page chrome.
- Fix authentication/session restoration and production API configuration.
- Keep email/password and Google sign-in; no phone/SMS OTP.
- Align checkout on Stripe and commission at 5%.
- Connect existing AI features to NVIDIA NIM and make AI provider status truthful.
- Fix marketplace search, order chat history, and buyer/seller dispute responses.

## Round 2 — Complete core marketplace flows

- Homepage and live marketplace statistics.
- Marketplace search, categories, filtering, pagination, and empty/loading/error states.
- Product/listing pages with seller information, packages, FAQs, reviews, and copyright report action.
- Reliable seller uploads and listing review.
- Buyer dashboard: purchases, payment confirmation, delivery, revisions, cancellation, dispute, chat, reviews.
- Seller dashboard: listings, order queue, delivery, earnings, Stripe onboarding status, withdrawal history.
- Verify every frontend action has a real backend endpoint and ownership check.

## Round 3 — Admin and trust operations

- Admin access through backend email allowlist.
- Admin overview and queues.
- Dispute review with buyer claim and seller response; Stripe refund or seller-balance release decision.
- Copyright report intake, evidence, review notes, and listing takedown.
- Listing moderation queue and audit trail.
- Prevent users from accessing other users' orders, messages, reports, or admin data.

## Round 4 — Regression and production hardening

- Backend tests for registration, login, listing ownership, order lifecycle, cancellation, chat, AI guard, dispute and copyright report access.
- Frontend production build and mobile layout regression.
- Stripe test-mode checkout and webhook verification.
- Upload size/type validation and persistent storage configuration.
- Verify Render backend health, Vercel frontend build, CORS, environment variables, and database persistence.
- Fix errors from actual deployment logs before calling the build complete.

## Non-negotiable constraints

- Do not change the existing UI colors or brand styling.
- Do not replace the existing UI with a new template.
- Do not add phone number or SMS OTP verification.
- Do not re-enable Razorpay or direct UPI checkout.
- Do not expose API keys in frontend code.
- Do not claim a deployment or payment flow works until it has been verified.
