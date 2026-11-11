"""Order-scoped buyer/seller chat, AI message guard, and mutual cancellation workflow."""
import os
import re
import requests
from datetime import datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import stripe

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "").strip()
NVIDIA_MODEL = os.environ.get("NVIDIA_MODEL", "moonshotai/kimi-k3")
BLOCK_PATTERNS = [
    (re.compile(r"\b(whatsapp|telegram|discord|snapchat)\b", re.I), "Keep order communication on the marketplace."),
    (re.compile(r"\b(pay\s*(me|you)\s*(direct|outside)|outside\s*(the\s*)?platform|off[- ]platform)\b", re.I), "Off-platform payment requests are not allowed."),
    (re.compile(r"\b(upi\s*id|bank\s*account|crypto\s*wallet|gift\s*card)\b", re.I), "Do not share payment credentials or request off-platform payment."),
    (re.compile(r"\b(call\s*me|text\s*me|my\s*number|phone\s*number)\b", re.I), "Keep personal contact details private and use order chat."),
    (re.compile(r"(https?://|www\.)", re.I), "Links are held for safety review; share deliverables through the order delivery flow."),
]
ABUSE = re.compile(r"\b(kill yourself|doxx|doxing|scammer|idiot|moron|bitch|bastard|f\*\*k you)\b", re.I)

def _moderate(text):
    for pattern, reason in BLOCK_PATTERNS:
        if pattern.search(text):
            return {"allowed": False, "reason": reason, "risk": "high"}
    if ABUSE.search(text):
        return {"allowed": False, "reason": "Harassment or abusive language is not allowed.", "risk": "medium"}
    if NVIDIA_API_KEY:
        try:
            response = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Accept": "application/json"},
                json={
                    "model": NVIDIA_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a marketplace safety classifier. Inspect one buyer-seller chat message. Return only JSON: {\"allow\":true|false,\"risk\":\"low|medium|high\",\"reason\":\"short reason\"}. Block threats, harassment, scams, phishing, requests for off-platform payment, attempts to share personal contact/payment details, malware, and suspicious links. Allow ordinary order discussion and creative feedback."},
                        {"role": "user", "content": text[:3000]},
                    ],
                    "max_tokens": 160,
                    "temperature": 0,
                    "stream": False,
                },
                timeout=12,
            )
            if response.ok:
                raw = response.json()["choices"][0]["message"]["content"]
                import json
                match = re.search(r"\{.*\}", raw, re.S)
                if match:
                    result = json.loads(match.group(0))
                    if result.get("allow") is False:
                        return {"allowed": False, "reason": str(result.get("reason") or "AI safety review blocked this message.")[:240], "risk": result.get("risk", "medium")}
        except Exception:
            # AI provider outage must not prevent normal, non-suspicious chat.
            pass
    return {"allowed": True, "risk": "low", "reason": None}

def register_order_chat_routes(app, db, User, Order, Message):
    class OrderCancellation(db.Model):
        __tablename__ = "order_cancellation"
        id = db.Column(db.Integer, primary_key=True)
        order_id = db.Column(db.Integer, db.ForeignKey("order.id"), unique=True, nullable=False)
        requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        reason = db.Column(db.String(500), nullable=False)
        buyer_approved = db.Column(db.Boolean, default=False, nullable=False)
        seller_approved = db.Column(db.Boolean, default=False, nullable=False)
        status = db.Column(db.String(20), default="requested", nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def participant(order, uid):
        try:
            uid = int(uid)
        except (TypeError, ValueError):
            return False
        return order.buyer_id == uid or order.seller_id == uid

    @app.route("/api/chat/messages/<int:order_id>", methods=["GET"])
    @jwt_required()
    def get_order_chat_messages(order_id):
        uid = get_jwt_identity()
        order = Order.query.get_or_404(order_id)
        if not participant(order, uid):
            return jsonify({"error": "You are not part of this order"}), 403
        messages = Message.query.filter_by(order_id=order_id).order_by(Message.timestamp.asc(), Message.id.asc()).all()
        items = []
        for message in messages:
            sender = User.query.get(message.sender_id)
            items.append({
                "id": message.id,
                "order_id": message.order_id,
                "content": message.content,
                "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                "is_read": bool(message.is_read),
                "message_type": message.message_type or "text",
                "sender": {
                    "id": sender.id if sender else message.sender_id,
                    "username": sender.username if sender else "Participant",
                    "profile_image": sender.profile_image if sender else None,
                },
            })
        return jsonify({"messages": items})

    @app.route("/api/chat/messages/<int:order_id>", methods=["POST"])
    @jwt_required()
    def send_order_chat_message(order_id):
        uid = get_jwt_identity()
        order = Order.query.get_or_404(order_id)
        if not participant(order, uid):
            return jsonify({"error": "You are not part of this order"}), 403
        if order.status in ("completed", "cancelled"):
            return jsonify({"error": "Chat is read-only because this order is closed"}), 409
        data = request.get_json(silent=True) or {}
        content = (data.get("content") or "").strip()
        if not content or len(content) > 3000:
            return jsonify({"error": "Message must be between 1 and 3000 characters"}), 400
        result = _moderate(content)
        if not result["allowed"]:
            return jsonify({"error": result["reason"], "ai_guard": {"blocked": True, "risk": result["risk"]}}), 422
        uid = int(uid)
        message = Message(order_id=order_id, sender_id=uid, content=content, timestamp=datetime.utcnow(), message_type="text")
        db.session.add(message)
        db.session.commit()
        sender = User.query.get(uid)
        return jsonify({"message": {
            "id": message.id, "order_id": order_id, "content": message.content,
            "timestamp": message.timestamp.isoformat(), "is_read": False,
            "sender": {"id": sender.id, "username": sender.username, "profile_image": sender.profile_image},
            "message_type": "text"
        }, "ai_guard": {"blocked": False, "risk": result["risk"]}}), 201

    @app.route("/api/orders/<int:order_id>/cancel", methods=["POST"])
    @jwt_required()
    def request_order_cancellation(order_id):
        uid = int(get_jwt_identity())
        order = Order.query.get_or_404(order_id)
        if not participant(order, uid):
            return jsonify({"error": "You are not part of this order"}), 403
        if order.status in ("completed", "cancelled") or order.escrow_status in ("released", "refunded"):
            return jsonify({"error": "This order is already settled"}), 409
        data = request.get_json(silent=True) or {}
        reason = (data.get("reason") or "Cancellation requested").strip()[:500]
        action = OrderCancellation.query.filter_by(order_id=order_id).first()
        if not action:
            action = OrderCancellation(order_id=order_id, requested_by=uid, reason=reason)
            db.session.add(action)
        if uid == order.buyer_id:
            action.buyer_approved = True
        else:
            action.seller_approved = True
        # For unpaid pending orders, buyer cancellation is enough; seller can agree too.
        if order.status == "pending" and not order.payment_id:
            action.buyer_approved = True
            action.seller_approved = True
        action.status = "approved" if action.buyer_approved and action.seller_approved else "requested"
        refund_requested = False
        if action.status == "approved":
            if order.payment_method == "stripe" and order.payment_id:
                try:
                    session = stripe.checkout.Session.retrieve(order.payment_id)
                    if session.get("payment_status") == "paid":
                        payment_intent = session.get("payment_intent")
                        if not payment_intent:
                            return jsonify({"error": "Stripe has no refundable payment intent for this order; contact support."}), 409
                        stripe.Refund.create(
                            payment_intent=payment_intent,
                            reason="requested_by_customer",
                            metadata={"order_id": str(order.id)},
                            idempotency_key=f"order-cancel-refund-{order.id}",
                        )
                        refund_requested = True
                    elif session.get("status") == "open":
                        stripe.checkout.Session.expire(order.payment_id)
                    else:
                        return jsonify({"error": "Stripe payment is still processing. Please retry after its status updates."}), 409
                except Exception:
                    app.logger.exception("Stripe cancellation/refund failed")
                    return jsonify({"error": "Stripe could not safely cancel or refund this checkout. The order remains open; contact support."}), 502
            elif order.payment_id:
                return jsonify({"error": "This order was not paid through Stripe. Contact support for a safe refund."}), 409
            order.status = "cancelled"
            order.escrow_status = "refunded" if refund_requested else "held"
        db.session.commit()
        return jsonify({
            "message": "Order cancelled and Stripe refund requested." if refund_requested else ("Order cancelled." if action.status == "approved" else "Cancellation request sent. The other party must also approve."),
            "status": order.status, "cancellation_status": action.status,
            "buyer_approved": action.buyer_approved, "seller_approved": action.seller_approved
        })

    @app.route("/api/orders/<int:order_id>/cancel", methods=["GET"])
    @jwt_required()
    def get_order_cancellation(order_id):
        uid = get_jwt_identity()
        order = Order.query.get_or_404(order_id)
        if not participant(order, uid):
            return jsonify({"error": "Unauthorized"}), 403
        action = OrderCancellation.query.filter_by(order_id=order_id).first()
        if not action:
            return jsonify({"status": "none"})
        return jsonify({"status": action.status, "reason": action.reason,
                        "buyer_approved": action.buyer_approved, "seller_approved": action.seller_approved})

    @app.route("/api/ai/guard/moderate-chat", methods=["POST"])
    @jwt_required()
    def preview_chat_moderation():
        data = request.get_json(silent=True) or {}
        content = (data.get("content") or "").strip()
        if not content or len(content) > 3000:
            return jsonify({"error": "Message must be between 1 and 3000 characters"}), 400
        result = _moderate(content)
        return jsonify({"allowed": result["allowed"], "risk": result["risk"], "reason": result["reason"]})
