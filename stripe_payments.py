"""Stripe Checkout payments and Stripe Connect seller verification/payouts.

Stripe-hosted Checkout collects buyer payment details. Stripe Connect Express onboarding
collects seller identity and payout details; this app never handles raw card or identity data.
"""
import os
import stripe
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
STRIPE_CONNECT_COUNTRY = os.environ.get("STRIPE_CONNECT_COUNTRY", "IN").upper()


def register_stripe_routes(app, db, User, Order, Gig):
    if STRIPE_SECRET_KEY:
        stripe.api_key = STRIPE_SECRET_KEY

    def stripe_ready():
        if not STRIPE_SECRET_KEY:
            return jsonify({"error": "Stripe is not configured. Add STRIPE_SECRET_KEY to the backend environment."}), 503
        return None

    def complete_checkout(session):
        if session.get("payment_status") != "paid":
            return False
        metadata = session.get("metadata") or {}
        order_id = metadata.get("order_id") or session.get("client_reference_id")
        if not order_id:
            return False
        order = Order.query.get(int(order_id))
        if not order:
            return False
        if order.payment_id == session.get("id") and order.status == "in_progress":
            return True
        if order.status != "pending":
            return False
        if order.payment_id and order.payment_id != session.get("id"):
            return False
        order.payment_id = session.get("id")
        order.payment_method = "stripe"
        order.status = "in_progress"
        order.escrow_status = "held"
        gig = Gig.query.get(order.gig_id)
        if gig:
            gig.total_orders = (gig.total_orders or 0) + 1
        db.session.commit()
        return True

    @app.route("/api/payment/stripe/create-checkout-session", methods=["POST"])
    @jwt_required()
    def stripe_create_checkout_session():
        unavailable = stripe_ready()
        if unavailable:
            return unavailable
        data = request.get_json(silent=True) or {}
        if not data.get("order_id"):
            return jsonify({"error": "order_id is required"}), 400
        order = Order.query.get_or_404(data["order_id"])
        user_id = get_jwt_identity()
        if order.buyer_id != user_id:
            return jsonify({"error": "You are not allowed to pay for this order"}), 403
        if order.status != "pending":
            return jsonify({"error": "This order is not awaiting payment"}), 409
        if order.payment_id:
            if order.payment_method != "stripe":
                return jsonify({"error": "This order already has a different payment method"}), 409
            try:
                existing = stripe.checkout.Session.retrieve(order.payment_id)
                if existing.get("status") == "open":
                    return jsonify({"checkout_url": existing.url, "session_id": existing.id})
                if existing.get("payment_status") == "paid":
                    return jsonify({"error": "Payment is complete and awaiting confirmation"}), 409
                if existing.get("status") != "expired":
                    return jsonify({"error": "The previous checkout is still processing"}), 409
                order.payment_id = None
                order.payment_method = None
                db.session.commit()
            except stripe.error.StripeError as exc:
                return jsonify({"error": str(exc.user_message or exc)}), 400
        if order.amount <= 0:
            return jsonify({"error": "Invalid order amount"}), 400
        gig = Gig.query.get(order.gig_id)
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "inr",
                        "unit_amount": int(round(order.amount * 100)),
                        "product_data": {
                            "name": (gig.title if gig else "AMV Marketplace order")[:120],
                            "description": f"Marketplace order #{order.id}",
                        },
                    },
                    "quantity": 1,
                }],
                metadata={"order_id": str(order.id), "buyer_id": str(user_id)},
                client_reference_id=str(order.id),
                success_url=f"{FRONTEND_URL}/orders?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{FRONTEND_URL}/gig/{order.gig_id}?payment=cancelled",
            )
            order.payment_id = session.id
            order.payment_method = "stripe"
            db.session.commit()
            return jsonify({"checkout_url": session.url, "session_id": session.id})
        except stripe.error.StripeError as exc:
            return jsonify({"error": str(exc.user_message or exc)}), 400
        except Exception:
            app.logger.exception("Stripe Checkout session creation failed")
            return jsonify({"error": "Could not start Stripe Checkout"}), 500

    @app.route("/api/payment/stripe/confirm", methods=["POST"])
    @jwt_required()
    def stripe_confirm_checkout():
        unavailable = stripe_ready()
        if unavailable:
            return unavailable
        data = request.get_json(silent=True) or {}
        session_id = (data.get("session_id") or "").strip()
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            order_id = (session.get("metadata") or {}).get("order_id")
            order = Order.query.get_or_404(int(order_id)) if order_id else None
            if not order or order.buyer_id != get_jwt_identity():
                return jsonify({"error": "Checkout session does not belong to this account"}), 403
            if not complete_checkout(session):
                return jsonify({"error": "Payment has not completed yet"}), 409
            return jsonify({"message": "Payment confirmed and held in escrow", "order_id": order.id})
        except stripe.error.StripeError as exc:
            return jsonify({"error": str(exc.user_message or exc)}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid Stripe checkout session"}), 400

    @app.route("/api/payment/stripe/webhook", methods=["POST"])
    def stripe_webhook():
        if not STRIPE_WEBHOOK_SECRET:
            return jsonify({"error": "Stripe webhook is not configured"}), 503
        payload = request.get_data()
        signature = request.headers.get("Stripe-Signature", "")
        try:
            event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
        except (ValueError, stripe.error.SignatureVerificationError):
            return jsonify({"error": "Invalid Stripe webhook signature"}), 400
        if event["type"] in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            complete_checkout(event["data"]["object"])
        return jsonify({"received": True})

    @app.route("/api/stripe/connect/onboarding", methods=["POST"])
    @jwt_required()
    def stripe_connect_onboarding():
        unavailable = stripe_ready()
        if unavailable:
            return unavailable
        user = User.query.get(get_jwt_identity())
        if not user:
            return jsonify({"error": "Account not found"}), 404
        if not (user.is_seller or user.account_type == "seller"):
            return jsonify({"error": "Choose the seller account type before setting up payouts"}), 403
        try:
            if not user.stripe_account_id:
                account = stripe.Account.create(
                    type="express",
                    country=STRIPE_CONNECT_COUNTRY,
                    email=user.email,
                    capabilities={"transfers": {"requested": True}},
                    metadata={"marketplace_user_id": str(user.id)},
                )
                user.stripe_account_id = account.id
                db.session.commit()
            link = stripe.AccountLink.create(
                account=user.stripe_account_id,
                refresh_url=f"{FRONTEND_URL}/wallet?stripe=refresh",
                return_url=f"{FRONTEND_URL}/wallet?stripe=return",
                type="account_onboarding",
            )
            return jsonify({"url": link.url, "account_id": user.stripe_account_id})
        except stripe.error.StripeError as exc:
            return jsonify({"error": str(exc.user_message or exc)}), 400

    @app.route("/api/stripe/connect/status", methods=["GET"])
    @jwt_required()
    def stripe_connect_status():
        unavailable = stripe_ready()
        if unavailable:
            return unavailable
        user = User.query.get(get_jwt_identity())
        if not user:
            return jsonify({"error": "Account not found"}), 404
        if not user.stripe_account_id:
            return jsonify({"connected": False, "verified": False, "payouts_enabled": False})
        try:
            account = stripe.Account.retrieve(user.stripe_account_id)
            verified = bool(account.details_submitted and account.payouts_enabled)
            user.stripe_onboarding_complete = verified
            db.session.commit()
            return jsonify({
                "connected": True,
                "verified": verified,
                "details_submitted": bool(account.details_submitted),
                "payouts_enabled": bool(account.payouts_enabled),
                "charges_enabled": bool(account.charges_enabled),
            })
        except stripe.error.StripeError as exc:
            return jsonify({"error": str(exc.user_message or exc)}), 400
