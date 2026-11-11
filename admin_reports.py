"""Admin moderation queues for marketplace disputes and copyright reports."""
import os
from datetime import datetime
import stripe
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity


def register_admin_routes(app, db, User, Gig, Order, PlatformFee, platform_fee_rate, platform_upi_id):
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()

    class CopyrightReport(db.Model):
        __tablename__ = "copyright_report"
        id = db.Column(db.Integer, primary_key=True)
        gig_id = db.Column(db.Integer, db.ForeignKey("gig.id"), nullable=False)
        reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        claimant_name = db.Column(db.String(160), nullable=False)
        contact_email = db.Column(db.String(160), nullable=False)
        description = db.Column(db.Text, nullable=False)
        evidence_url = db.Column(db.String(1000))
        status = db.Column(db.String(24), default="pending", nullable=False)
        admin_notes = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
        reviewed_at = db.Column(db.DateTime)

    def current_user():
        try:
            return User.query.get(int(get_jwt_identity()))
        except (TypeError, ValueError):
            return None

    def admin_required_user():
        user = current_user()
        allowed = {
            email.strip().lower()
            for email in os.environ.get("ADMIN_EMAILS", "").split(",")
            if email.strip()
        }
        if not user or user.email.strip().lower() not in allowed:
            return None
        return user

    def admin_error():
        return jsonify({"error": "Admin access is not enabled for this account."}), 403

    @app.route("/api/gigs/<int:gig_id>/copyright-report", methods=["POST"])
    @jwt_required()
    def submit_copyright_report(gig_id):
        user = current_user()
        if not user:
            return jsonify({"error": "Account not found"}), 401
        gig = Gig.query.get_or_404(gig_id)
        data = request.get_json(silent=True) or {}
        claimant = (data.get("claimant_name") or "").strip()
        email = (data.get("contact_email") or "").strip().lower()
        description = (data.get("description") or "").strip()
        evidence = (data.get("evidence_url") or "").strip()
        if not claimant or not email or len(description) < 20:
            return jsonify({"error": "Provide your name, contact email, and at least 20 characters explaining the copyright claim."}), 400
        if len(claimant) > 160 or len(email) > 160 or len(description) > 5000 or len(evidence) > 1000:
            return jsonify({"error": "One or more report fields are too long."}), 400
        report = CopyrightReport(
            gig_id=gig.id, reporter_id=user.id, claimant_name=claimant,
            contact_email=email, description=description, evidence_url=evidence or None,
        )
        db.session.add(report)
        db.session.commit()
        return jsonify({"message": "Copyright report submitted for review.", "report_id": report.id}), 201

    @app.route("/api/admin/overview", methods=["GET"])
    @jwt_required()
    def admin_overview():
        admin = admin_required_user()
        if not admin:
            return admin_error()
        return jsonify({
            "counts": {
                "users": User.query.count(),
                "active_gigs": Gig.query.filter_by(is_active=True).count(),
                "orders": Order.query.count(),
                "disputes": Order.query.filter_by(status="disputed").count(),
                "copyright_reports": CopyrightReport.query.filter(CopyrightReport.status.in_(["pending", "under_review"])).count(),
                "moderation_queue": Gig.query.filter(Gig.flagged_fake.is_(True)).count(),
            },
            "admin": {"id": admin.id, "username": admin.username, "email": admin.email},
        })

    @app.route("/api/admin/moderation", methods=["GET"])
    @jwt_required()
    def admin_list_moderation_queue():
        if not admin_required_user():
            return admin_error()
        gigs = Gig.query.filter_by(flagged_fake=True).order_by(Gig.created_at.desc()).limit(200).all()
        return jsonify({"listings": [{
            "id": gig.id, "title": gig.title, "description": (gig.description or "")[:1000],
            "category": gig.category, "is_active": gig.is_active,
            "flagged_fake": gig.flagged_fake, "ai_quality_score": gig.ai_quality_score,
            "ai_scan_notes": gig.ai_scan_notes, "seller": gig.seller.username if gig.seller else "Unknown",
        } for gig in gigs]})

    @app.route("/api/admin/moderation/<int:gig_id>", methods=["PATCH"])
    @jwt_required()
    def admin_update_moderation(gig_id):
        if not admin_required_user():
            return admin_error()
        gig = Gig.query.get_or_404(gig_id)
        data = request.get_json(silent=True) or {}
        action = (data.get("action") or "").strip().lower()
        note = (data.get("note") or "").strip()[:2000]
        if action == "approve":
            gig.flagged_fake = False
            gig.is_active = True
            gig.ai_scan_notes = "Admin approved listing" + (": " + note if note else ".")
        elif action == "remove":
            gig.flagged_fake = True
            gig.is_active = False
            gig.ai_scan_notes = "Removed after admin moderation review" + (": " + note if note else ".")
        else:
            return jsonify({"error": "action must be 'approve' or 'remove'."}), 400
        db.session.commit()
        return jsonify({"message": "Moderation decision saved.", "gig_id": gig.id, "is_active": gig.is_active})

    @app.route("/api/admin/disputes", methods=["GET"])
    @jwt_required()
    def admin_list_disputes():
        if not admin_required_user():
            return admin_error()
        orders = Order.query.filter_by(status="disputed").order_by(Order.created_at.desc()).limit(200).all()
        result = []
        for order in orders:
            buyer = User.query.get(order.buyer_id)
            seller = User.query.get(order.seller_id)
            gig = Gig.query.get(order.gig_id)
            result.append({
                "order_id": order.id, "amount": order.amount, "status": order.status,
                "escrow_status": order.escrow_status, "payment_method": order.payment_method,
                "payment_id": order.payment_id, "buyer_claim": order.buyer_message,
                "seller_response": order.seller_message, "created_at": order.created_at.isoformat() if order.created_at else None,
                "buyer": buyer.username if buyer else "Unknown",
                "seller": seller.username if seller else "Unknown",
                "gig_title": gig.title if gig else "Deleted listing",
            })
        return jsonify({"disputes": result})

    @app.route("/api/orders/<int:order_id>/dispute-response", methods=["POST"])
    @jwt_required()
    def seller_dispute_response(order_id):
        user = current_user()
        order = Order.query.get_or_404(order_id)
        if not user or order.seller_id != user.id:
            return jsonify({"error": "Only the seller on this order can respond."}), 403
        if order.status != "disputed":
            return jsonify({"error": "This order is not currently disputed."}), 409
        data = request.get_json(silent=True) or {}
        response = (data.get("response") or "").strip()
        if not response or len(response) > 5000:
            return jsonify({"error": "Response must be between 1 and 5000 characters."}), 400
        order.seller_message = response
        db.session.commit()
        return jsonify({"message": "Your dispute response was submitted."})

    @app.route("/api/admin/disputes/<int:order_id>/resolve", methods=["POST"])
    @jwt_required()
    def admin_resolve_dispute(order_id):
        if not admin_required_user():
            return admin_error()
        order = Order.query.get_or_404(order_id)
        if order.status != "disputed" or order.escrow_status != "held":
            return jsonify({"error": "Only disputed orders with held funds can be resolved."}), 409
        data = request.get_json(silent=True) or {}
        decision = (data.get("decision") or "").strip().lower()
        note = (data.get("note") or "").strip()[:2000]
        if decision == "refund":
            if order.payment_method != "stripe" or not order.payment_id:
                return jsonify({"error": "This order has no confirmed Stripe Checkout payment to refund."}), 409
            try:
                session = stripe.checkout.Session.retrieve(order.payment_id)
                payment_intent = session.get("payment_intent")
                if not payment_intent:
                    return jsonify({"error": "Stripe has no refundable payment intent for this order."}), 409
                stripe.Refund.create(
                    payment_intent=payment_intent,
                    reason="requested_by_customer",
                    metadata={"order_id": str(order.id), "admin_resolution": "true"},
                    idempotency_key=f"admin-dispute-refund-{order.id}",
                )
            except Exception:
                app.logger.exception("Admin dispute refund failed")
                return jsonify({"error": "Stripe refund could not be created; funds remain held."}), 502
            order.status = "cancelled"
            order.escrow_status = "refunded"
            order.seller_message = (order.seller_message or "")[:4500] + ("\n\nAdmin resolution: " + note if note else "\n\nAdmin resolution: refunded")
        elif decision == "release":
            fee = round(float(order.amount) * float(platform_fee_rate), 2)
            payout = round(float(order.amount) - fee, 2)
            seller = User.query.get(order.seller_id)
            if not seller:
                return jsonify({"error": "Seller account not found; funds remain held."}), 409
            seller.balance = float(seller.balance or 0) + payout
            db.session.add(PlatformFee(order_id=order.id, amount=fee, recipient_upi=platform_upi_id))
            order.status = "completed"
            order.escrow_status = "released"
            order.completed_at = datetime.utcnow()
            order.release_method = "admin_dispute_resolution"
            order.seller_message = (order.seller_message or "")[:4500] + ("\n\nAdmin resolution: " + note if note else "\n\nAdmin resolution: released to seller")
        else:
            return jsonify({"error": "decision must be 'refund' or 'release'."}), 400
        db.session.commit()
        return jsonify({"message": "Dispute resolved.", "order_id": order.id, "status": order.status, "escrow_status": order.escrow_status})

    @app.route("/api/admin/copyright-reports", methods=["GET"])
    @jwt_required()
    def admin_list_copyright_reports():
        if not admin_required_user():
            return admin_error()
        reports = CopyrightReport.query.order_by(CopyrightReport.created_at.desc()).limit(300).all()
        return jsonify({"reports": [{
            "id": report.id, "gig_id": report.gig_id, "reporter_id": report.reporter_id,
            "claimant_name": report.claimant_name, "contact_email": report.contact_email,
            "description": report.description, "evidence_url": report.evidence_url,
            "status": report.status, "admin_notes": report.admin_notes,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "gig_title": Gig.query.get(report.gig_id).title if Gig.query.get(report.gig_id) else "Deleted listing",
        } for report in reports]})

    @app.route("/api/admin/copyright-reports/<int:report_id>", methods=["PATCH"])
    @jwt_required()
    def admin_update_copyright_report(report_id):
        if not admin_required_user():
            return admin_error()
        report = CopyrightReport.query.get_or_404(report_id)
        data = request.get_json(silent=True) or {}
        status = (data.get("status") or "").strip().lower()
        allowed = {"under_review", "action_required", "removed", "rejected"}
        if status not in allowed:
            return jsonify({"error": "Invalid report status."}), 400
        report.status = status
        report.admin_notes = (data.get("admin_notes") or "").strip()[:3000]
        report.reviewed_at = datetime.utcnow()
        if status == "removed":
            gig = Gig.query.get(report.gig_id)
            if gig:
                gig.is_active = False
                gig.ai_scan_notes = "Listing hidden after admin copyright review (report #" + str(report.id) + ")."
        db.session.commit()
        return jsonify({"message": "Copyright report updated.", "status": report.status})
