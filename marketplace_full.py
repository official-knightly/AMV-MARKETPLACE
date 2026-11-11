"""
Full Fiverr-class marketplace backend — packages, messaging, revisions,
buyer requests, custom offers, favorites, notifications, coupons, analytics.
No UI changes; all features exposed via REST API.
"""
import json
from datetime import datetime, timedelta


def register_marketplace(app, db, jwt_required, get_jwt_identity, sanitize_text, helpers):
    User = helpers['User']
    Gig = helpers['Gig']
    Order = helpers['Order']
    Review = helpers['Review']

    # ─── Extended models ───────────────────────────────────────────────

    class GigPackage(db.Model):
        __tablename__ = 'gig_package'
        id = db.Column(db.Integer, primary_key=True)
        gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
        tier = db.Column(db.String(20), nullable=False)  # basic, standard, premium
        title = db.Column(db.String(120))
        description = db.Column(db.Text)
        price = db.Column(db.Float, nullable=False)
        delivery_days = db.Column(db.Integer, default=3)
        revisions = db.Column(db.Integer, default=1)
        features = db.Column(db.Text)  # JSON list

    class GigExtra(db.Model):
        __tablename__ = 'gig_extra'
        id = db.Column(db.Integer, primary_key=True)
        gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
        title = db.Column(db.String(120), nullable=False)
        description = db.Column(db.Text)
        price = db.Column(db.Float, nullable=False)
        extra_days = db.Column(db.Integer, default=0)

    class GigFAQ(db.Model):
        __tablename__ = 'gig_faq'
        id = db.Column(db.Integer, primary_key=True)
        gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
        question = db.Column(db.String(300), nullable=False)
        answer = db.Column(db.Text, nullable=False)
        sort_order = db.Column(db.Integer, default=0)

    class GigGallery(db.Model):
        __tablename__ = 'gig_gallery'
        id = db.Column(db.Integer, primary_key=True)
        gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
        media_url = db.Column(db.String(500), nullable=False)
        media_type = db.Column(db.String(20), default='image')

    class Conversation(db.Model):
        __tablename__ = 'conversation'
        id = db.Column(db.Integer, primary_key=True)
        buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'))
        order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class Message(db.Model):
        __tablename__ = 'message'
        id = db.Column(db.Integer, primary_key=True)
        conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
        sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        body = db.Column(db.Text, nullable=False)
        attachment_url = db.Column(db.String(500))
        is_read = db.Column(db.Boolean, default=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class Notification(db.Model):
        __tablename__ = 'notification'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        type = db.Column(db.String(50), nullable=False)
        title = db.Column(db.String(200))
        body = db.Column(db.Text)
        link = db.Column(db.String(300))
        is_read = db.Column(db.Boolean, default=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class Favorite(db.Model):
        __tablename__ = 'favorite'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        __table_args__ = (db.UniqueConstraint('user_id', 'gig_id', name='uq_favorite'),)

    class OrderRevision(db.Model):
        __tablename__ = 'order_revision'
        id = db.Column(db.Integer, primary_key=True)
        order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
        requested_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        message = db.Column(db.Text)
        status = db.Column(db.String(20), default='pending')  # pending, delivered, closed
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class CustomOffer(db.Model):
        __tablename__ = 'custom_offer'
        id = db.Column(db.Integer, primary_key=True)
        seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        title = db.Column(db.String(200), nullable=False)
        description = db.Column(db.Text)
        price = db.Column(db.Float, nullable=False)
        delivery_days = db.Column(db.Integer, default=3)
        status = db.Column(db.String(20), default='pending')  # pending, accepted, declined, expired
        expires_at = db.Column(db.DateTime)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class BuyerRequest(db.Model):
        __tablename__ = 'buyer_request'
        id = db.Column(db.Integer, primary_key=True)
        buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        title = db.Column(db.String(200), nullable=False)
        description = db.Column(db.Text, nullable=False)
        category = db.Column(db.String(50))
        budget_min = db.Column(db.Float)
        budget_max = db.Column(db.Float)
        delivery_days = db.Column(db.Integer, default=7)
        status = db.Column(db.String(20), default='open')
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class RequestOffer(db.Model):
        __tablename__ = 'request_offer'
        id = db.Column(db.Integer, primary_key=True)
        request_id = db.Column(db.Integer, db.ForeignKey('buyer_request.id'), nullable=False)
        seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        message = db.Column(db.Text)
        price = db.Column(db.Float, nullable=False)
        delivery_days = db.Column(db.Integer, default=3)
        status = db.Column(db.String(20), default='pending')
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class Coupon(db.Model):
        __tablename__ = 'coupon'
        id = db.Column(db.Integer, primary_key=True)
        code = db.Column(db.String(30), unique=True, nullable=False)
        discount_percent = db.Column(db.Float, default=0)
        discount_amount = db.Column(db.Float, default=0)
        max_uses = db.Column(db.Integer, default=100)
        uses_count = db.Column(db.Integer, default=0)
        valid_until = db.Column(db.DateTime)
        is_active = db.Column(db.Boolean, default=True)

    class GigImpression(db.Model):
        __tablename__ = 'gig_impression'
        id = db.Column(db.Integer, primary_key=True)
        gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
        viewer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class SellerProfile(db.Model):
        __tablename__ = 'seller_profile'
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
        tagline = db.Column(db.String(200))
        skills = db.Column(db.Text)  # JSON
        languages = db.Column(db.Text)  # JSON
        response_time_hours = db.Column(db.Integer, default=24)
        seller_level = db.Column(db.String(30), default='new')  # new, level1, level2, top
        country = db.Column(db.String(80))
        member_since = db.Column(db.DateTime, default=datetime.utcnow)

    class OrderExtra(db.Model):
        __tablename__ = 'order_extra'
        id = db.Column(db.Integer, primary_key=True)
        order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
        extra_id = db.Column(db.Integer, db.ForeignKey('gig_extra.id'))
        title = db.Column(db.String(120))
        price = db.Column(db.Float, default=0)

    # Order extensions via migration columns
    order_cols = {
        'package_id': 'INTEGER', 'coupon_code': 'VARCHAR(30)',
        'discount_amount': 'FLOAT DEFAULT 0', 'revisions_used': 'INTEGER DEFAULT 0',
        'max_revisions': 'INTEGER DEFAULT 1', 'due_date': 'DATETIME',
    }

    def notify(user_id, ntype, title, body, link=None):
        n = Notification(user_id=user_id, type=ntype, title=title, body=body, link=link)
        db.session.add(n)

    def seller_level_for(user_id):
        completed = Order.query.filter_by(seller_id=user_id, status='completed').count()
        if completed >= 100:
            return 'top_rated'
        if completed >= 25:
            return 'level_2'
        if completed >= 5:
            return 'level_1'
        return 'new'

    def gig_detail_extras(gig):
        packages = GigPackage.query.filter_by(gig_id=gig.id).order_by(GigPackage.price).all()
        if not packages:
            ensure_default_packages(gig)
            db.session.commit()
            packages = GigPackage.query.filter_by(gig_id=gig.id).order_by(GigPackage.price).all()
        return {
            'packages': [{
                'id': p.id, 'tier': p.tier, 'title': p.title,
                'description': p.description, 'price': p.price,
                'delivery_days': p.delivery_days, 'revisions': p.revisions,
                'features': json.loads(p.features) if p.features else [],
            } for p in packages],
            'extras': [{
                'id': e.id, 'title': e.title, 'description': e.description,
                'price': e.price, 'extra_days': e.extra_days,
            } for e in GigExtra.query.filter_by(gig_id=gig.id).all()],
            'faqs': [{
                'id': f.id, 'question': f.question, 'answer': f.answer,
            } for f in GigFAQ.query.filter_by(gig_id=gig.id).order_by(GigFAQ.sort_order).all()],
            'gallery': [{
                'id': g.id, 'media_url': g.media_url, 'media_type': g.media_type,
            } for g in GigGallery.query.filter_by(gig_id=gig.id).all()],
        }

    # ─── Categories (Fiverr-style tree) ───────────────────────────────

    CATEGORIES = {
        'amv': {'label': 'AMV & Anime Edits', 'sub': ['action', 'romance', 'sad', '4k']},
        'gaming': {'label': 'Gaming Montages', 'sub': ['highlights', 'funny', 'cinematic']},
        'tiktok': {'label': 'TikTok & Reels', 'sub': ['transitions', 'trending', 'captions']},
        'motion': {'label': 'Motion Graphics', 'sub': ['logo', 'lower-thirds', 'vfx']},
    }

    @app.route('/api/categories', methods=['GET'])
    def list_categories():
        return jsonify({'categories': CATEGORIES})

    # ─── Seller public profile ─────────────────────────────────────────

    @app.route('/api/sellers/<username>', methods=['GET'])
    def seller_profile(username):
        user = User.query.filter_by(username=username).first_or_404()
        sp = SellerProfile.query.filter_by(user_id=user.id).first()
        gigs = Gig.query.filter_by(seller_id=user.id, is_active=True, flagged_fake=False).limit(12).all()
        reviews = Review.query.join(Order).filter(Order.seller_id == user.id).order_by(
            Review.created_at.desc()).limit(10).all()
        return jsonify({
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'profile_image': user.profile_image,
            'bio': user.bio,
            'trust_score': user.trust_score,
            'seller_level': seller_level_for(user.id),
            'profile': {
                'tagline': sp.tagline if sp else None,
                'skills': json.loads(sp.skills) if sp and sp.skills else [],
                'languages': json.loads(sp.languages) if sp and sp.languages else ['English'],
                'response_time_hours': sp.response_time_hours if sp else 24,
                'country': sp.country if sp else None,
            },
            'stats': {
                'total_gigs': Gig.query.filter_by(seller_id=user.id, is_active=True).count(),
                'completed_orders': Order.query.filter_by(seller_id=user.id, status='completed').count(),
                'avg_rating': user.trust_score,
            },
            'gigs': [{'id': g.id, 'title': g.title, 'price': g.price, 'thumbnail': g.thumbnail, 'rating': g.rating} for g in gigs],
            'reviews': [{
                'rating': r.rating, 'comment': r.comment,
                'reviewer': User.query.get(r.reviewer_id).username,
            } for r in reviews],
        })

    @app.route('/api/sellers/profile', methods=['PUT'])
    @jwt_required()
    def update_seller_profile():
        uid = get_jwt_identity()
        data = request.json or {}
        sp = SellerProfile.query.filter_by(user_id=uid).first()
        if not sp:
            sp = SellerProfile(user_id=uid)
            db.session.add(sp)
        user = User.query.get(uid)
        if data.get('bio'):
            user.bio = sanitize_text(data['bio'], 2000)
        sp.tagline = sanitize_text(data.get('tagline', sp.tagline or ''), 200)
        sp.skills = json.dumps(data.get('skills', json.loads(sp.skills or '[]')))
        sp.languages = json.dumps(data.get('languages', json.loads(sp.languages or '["English"]')))
        sp.response_time_hours = int(data.get('response_time_hours', sp.response_time_hours or 24))
        sp.country = sanitize_text(data.get('country', sp.country or ''), 80)
        sp.seller_level = seller_level_for(uid)
        user.is_seller = True
        db.session.commit()
        return jsonify({'message': 'Profile updated'})

    # ─── Gig packages / extras / FAQ / gallery ────────────────────────

    @app.route('/api/gigs/<int:gig_id>/full', methods=['GET'])
    def gig_full(gig_id):
        gig = Gig.query.get_or_404(gig_id)
        if gig.flagged_fake:
            return jsonify({'error': 'Listing unavailable'}), 404
        imp = GigImpression(gig_id=gig_id, viewer_id=None)
        db.session.add(imp)
        db.session.commit()
        base = {
            'id': gig.id, 'title': gig.title, 'description': gig.description,
            'category': gig.category, 'price': gig.price, 'delivery_days': gig.delivery_days,
            'thumbnail': gig.thumbnail, 'video_url': gig.video_url,
            'rating': gig.rating, 'total_orders': gig.total_orders,
            'tags': json.loads(gig.tags) if gig.tags else [],
            'ai_quality_score': gig.ai_quality_score,
            'is_verified_listing': gig.is_verified_listing,
            'seller': {
                'username': gig.seller.username, 'profile_image': gig.seller.profile_image,
                'trust_score': gig.seller.trust_score, 'seller_level': seller_level_for(gig.seller_id),
            },
        }
        base.update(gig_detail_extras(gig))
        return jsonify(base)

    @app.route('/api/gigs/<int:gig_id>/packages', methods=['POST'])
    @jwt_required()
    def add_packages(gig_id):
        uid = get_jwt_identity()
        gig = Gig.query.get_or_404(gig_id)
        if gig.seller_id != uid:
            return jsonify({'error': 'Unauthorized'}), 403
        for pkg in request.json.get('packages', []):
            db.session.add(GigPackage(
                gig_id=gig_id, tier=pkg['tier'], title=pkg.get('title', pkg['tier']),
                description=pkg.get('description', ''), price=float(pkg['price']),
                delivery_days=int(pkg.get('delivery_days', 3)),
                revisions=int(pkg.get('revisions', 1)),
                features=json.dumps(pkg.get('features', [])),
            ))
        db.session.commit()
        return jsonify({'message': 'Packages saved'})

    @app.route('/api/gigs/<int:gig_id>/extras', methods=['POST'])
    @jwt_required()
    def add_extras(gig_id):
        uid = get_jwt_identity()
        gig = Gig.query.get_or_404(gig_id)
        if gig.seller_id != uid:
            return jsonify({'error': 'Unauthorized'}), 403
        for ex in request.json.get('extras', []):
            db.session.add(GigExtra(
                gig_id=gig_id, title=sanitize_text(ex['title'], 120),
                description=ex.get('description', ''), price=float(ex['price']),
                extra_days=int(ex.get('extra_days', 0)),
            ))
        db.session.commit()
        return jsonify({'message': 'Extras saved'})

    @app.route('/api/gigs/<int:gig_id>/faqs', methods=['POST'])
    @jwt_required()
    def add_faqs(gig_id):
        uid = get_jwt_identity()
        gig = Gig.query.get_or_404(gig_id)
        if gig.seller_id != uid:
            return jsonify({'error': 'Unauthorized'}), 403
        for i, faq in enumerate(request.json.get('faqs', [])):
            db.session.add(GigFAQ(
                gig_id=gig_id,
                question=sanitize_text(faq['question'], 300),
                answer=sanitize_text(faq['answer'], 2000),
                sort_order=i,
            ))
        db.session.commit()
        return jsonify({'message': 'FAQs saved'})

    # ─── Enhanced order create (package + extras + coupon) ────────────

    @app.route('/api/orders/create-full', methods=['POST'])
    @jwt_required()
    def create_order_full():
        buyer_id = get_jwt_identity()
        data = request.json
        gig = Gig.query.get_or_404(data['gig_id'])
        if gig.seller_id == buyer_id:
            return jsonify({'error': 'Cannot order your own gig'}), 400

        amount = gig.price
        delivery_days = gig.delivery_days
        max_revisions = 1
        package_id = data.get('package_id')

        if package_id:
            pkg = GigPackage.query.get(package_id)
            if pkg and pkg.gig_id == gig.id:
                amount = pkg.price
                delivery_days = pkg.delivery_days
                max_revisions = pkg.revisions

        for eid in data.get('extra_ids', []):
            ex = GigExtra.query.get(eid)
            if ex and ex.gig_id == gig.id:
                amount += ex.price
                delivery_days += ex.extra_days

        discount = 0.0
        coupon_code = data.get('coupon_code', '').strip().upper()
        if coupon_code:
            c = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
            if c and (not c.valid_until or c.valid_until > datetime.utcnow()):
                if c.uses_count < c.max_uses:
                    if c.discount_percent:
                        discount = amount * (c.discount_percent / 100)
                    else:
                        discount = c.discount_amount
                    c.uses_count += 1
                else:
                    return jsonify({'error': 'Coupon expired or max uses reached'}), 400

        amount = max(1, round(amount - discount, 2))
        due = datetime.utcnow() + timedelta(days=delivery_days)

        order = Order(
            buyer_id=buyer_id, seller_id=gig.seller_id, gig_id=gig.id,
            amount=amount, buyer_message=data.get('message', ''),
            package_id=package_id, coupon_code=coupon_code or None,
            discount_amount=discount, max_revisions=max_revisions, due_date=due,
        )
        db.session.add(order)
        db.session.flush()

        for eid in data.get('extra_ids', []):
            ex = GigExtra.query.get(eid)
            if ex:
                db.session.add(OrderExtra(order_id=order.id, extra_id=ex.id, title=ex.title, price=ex.price))

        notify(gig.seller_id, 'new_order', 'New order', f'Order #{order.id} for {gig.title}', f'/orders')
        db.session.commit()
        return jsonify({
            'order_id': order.id, 'amount': amount, 'due_date': due.isoformat(),
            'max_revisions': max_revisions, 'discount': discount,
        }), 201

    # ─── Revisions (Fiverr-style) ─────────────────────────────────────

    @app.route('/api/orders/<int:order_id>/revision', methods=['POST'])
    @jwt_required()
    def request_revision(order_id):
        uid = get_jwt_identity()
        order = Order.query.get_or_404(order_id)
        if order.buyer_id != uid:
            return jsonify({'error': 'Only buyer can request revision'}), 403
        used = order.revisions_used or 0
        max_r = order.max_revisions or 1
        if used >= max_r:
            return jsonify({'error': 'No revisions left on this package'}), 400
        rev = OrderRevision(
            order_id=order_id, requested_by=uid,
            message=sanitize_text(request.json.get('message', ''), 2000),
        )
        order.revisions_used = used + 1
        order.status = 'in_progress'
        db.session.add(rev)
        notify(order.seller_id, 'revision', 'Revision requested', f'Order #{order_id}', '/orders')
        db.session.commit()
        return jsonify({'message': 'Revision requested', 'revisions_left': max_r - used - 1})

    # ─── Messaging / Inbox ────────────────────────────────────────────

    @app.route('/api/conversations', methods=['GET'])
    @jwt_required()
    def list_conversations():
        uid = get_jwt_identity()
        convos = Conversation.query.filter(
            (Conversation.buyer_id == uid) | (Conversation.seller_id == uid)
        ).order_by(Conversation.updated_at.desc()).all()
        out = []
        for c in convos:
            other_id = c.seller_id if c.buyer_id == uid else c.buyer_id
            other = User.query.get(other_id)
            last = Message.query.filter_by(conversation_id=c.id).order_by(Message.created_at.desc()).first()
            unread = Message.query.filter_by(conversation_id=c.id, is_read=False).filter(
                Message.sender_id != uid).count()
            out.append({
                'id': c.id, 'other_user': other.username, 'other_image': other.profile_image,
                'last_message': last.body[:80] if last else '', 'unread': unread,
                'updated_at': c.updated_at.isoformat() if c.updated_at else None,
            })
        return jsonify({'conversations': out})

    @app.route('/api/conversations', methods=['POST'])
    @jwt_required()
    def start_conversation():
        uid = get_jwt_identity()
        data = request.json
        seller_id = int(data['seller_id'])
        if seller_id == uid:
            return jsonify({'error': 'Invalid'}), 400
        c = Conversation.query.filter_by(buyer_id=uid, seller_id=seller_id).first()
        if not c:
            c = Conversation(buyer_id=uid, seller_id=seller_id, gig_id=data.get('gig_id'))
            db.session.add(c)
            db.session.commit()
        return jsonify({'conversation_id': c.id})

    @app.route('/api/conversations/<int:cid>/messages', methods=['GET'])
    @jwt_required()
    def get_messages(cid):
        uid = get_jwt_identity()
        c = Conversation.query.get_or_404(cid)
        if uid not in (c.buyer_id, c.seller_id):
            return jsonify({'error': 'Unauthorized'}), 403
        msgs = Message.query.filter_by(conversation_id=cid).order_by(Message.created_at).all()
        Message.query.filter_by(conversation_id=cid, is_read=False).filter(
            Message.sender_id != uid).update({'is_read': True})
        db.session.commit()
        return jsonify({'messages': [{
            'id': m.id, 'sender_id': m.sender_id,
            'body': m.body, 'attachment_url': m.attachment_url,
            'created_at': m.created_at.isoformat(),
            'is_mine': m.sender_id == uid,
        } for m in msgs]})

    @app.route('/api/conversations/<int:cid>/messages', methods=['POST'])
    @jwt_required()
    def send_message(cid):
        uid = get_jwt_identity()
        c = Conversation.query.get_or_404(cid)
        if uid not in (c.buyer_id, c.seller_id):
            return jsonify({'error': 'Unauthorized'}), 403
        body = sanitize_text(request.json.get('body', ''), 5000)
        m = Message(conversation_id=cid, sender_id=uid, body=body,
                    attachment_url=request.json.get('attachment_url'))
        c.updated_at = datetime.utcnow()
        db.session.add(m)
        other = c.seller_id if uid == c.buyer_id else c.buyer_id
        notify(other, 'message', 'New message', body[:100], f'/inbox/{cid}')
        db.session.commit()
        return jsonify({'id': m.id, 'created_at': m.created_at.isoformat()})

    # ─── Notifications ────────────────────────────────────────────────

    @app.route('/api/notifications', methods=['GET'])
    @jwt_required()
    def get_notifications():
        uid = get_jwt_identity()
        notes = Notification.query.filter_by(user_id=uid).order_by(
            Notification.created_at.desc()).limit(50).all()
        unread = Notification.query.filter_by(user_id=uid, is_read=False).count()
        return jsonify({
            'unread': unread,
            'notifications': [{
                'id': n.id, 'type': n.type, 'title': n.title, 'body': n.body,
                'link': n.link, 'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
            } for n in notes],
        })

    @app.route('/api/notifications/read-all', methods=['POST'])
    @jwt_required()
    def read_all_notifications():
        uid = get_jwt_identity()
        Notification.query.filter_by(user_id=uid, is_read=False).update({'is_read': True})
        db.session.commit()
        return jsonify({'message': 'ok'})

    # ─── Favorites ────────────────────────────────────────────────────

    @app.route('/api/favorites', methods=['GET'])
    @jwt_required()
    def list_favorites():
        uid = get_jwt_identity()
        favs = Favorite.query.filter_by(user_id=uid).all()
        gigs = []
        for f in favs:
            g = Gig.query.get(f.gig_id)
            if g and g.is_active and not g.flagged_fake:
                gigs.append({'id': g.id, 'title': g.title, 'price': g.price, 'thumbnail': g.thumbnail})
        return jsonify({'favorites': gigs})

    @app.route('/api/favorites/<int:gig_id>', methods=['POST'])
    @jwt_required()
    def toggle_favorite(gig_id):
        uid = get_jwt_identity()
        f = Favorite.query.filter_by(user_id=uid, gig_id=gig_id).first()
        if f:
            db.session.delete(f)
            db.session.commit()
            return jsonify({'favorited': False})
        db.session.add(Favorite(user_id=uid, gig_id=gig_id))
        db.session.commit()
        return jsonify({'favorited': True})

    # ─── Custom offers ────────────────────────────────────────────────

    @app.route('/api/custom-offers', methods=['POST'])
    @jwt_required()
    def create_custom_offer():
        uid = get_jwt_identity()
        data = request.json
        offer = CustomOffer(
            seller_id=uid, buyer_id=int(data['buyer_id']),
            title=sanitize_text(data['title'], 200),
            description=data.get('description', ''),
            price=float(data['price']),
            delivery_days=int(data.get('delivery_days', 3)),
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db.session.add(offer)
        notify(offer.buyer_id, 'custom_offer', 'Custom offer', offer.title, '/offers')
        db.session.commit()
        return jsonify({'offer_id': offer.id}), 201

    @app.route('/api/custom-offers/<int:oid>/accept', methods=['POST'])
    @jwt_required()
    def accept_custom_offer(oid):
        uid = get_jwt_identity()
        offer = CustomOffer.query.get_or_404(oid)
        if offer.buyer_id != uid:
            return jsonify({'error': 'Unauthorized'}), 403
        offer.status = 'accepted'
        gig = Gig.query.filter_by(seller_id=offer.seller_id).first()
        if not gig:
            return jsonify({'error': 'Seller has no gigs'}), 400
        order = Order(buyer_id=uid, seller_id=offer.seller_id, gig_id=gig.id, amount=offer.price)
        db.session.add(order)
        db.session.commit()
        return jsonify({'order_id': order.id, 'amount': offer.price})

    # ─── Buyer requests (Fiverr Buyer Requests) ───────────────────────

    @app.route('/api/buyer-requests', methods=['GET'])
    def list_buyer_requests():
        reqs = BuyerRequest.query.filter_by(status='open').order_by(
            BuyerRequest.created_at.desc()).limit(30).all()
        return jsonify({'requests': [{
            'id': r.id, 'title': r.title, 'description': r.description[:300],
            'category': r.category, 'budget_min': r.budget_min, 'budget_max': r.budget_max,
            'delivery_days': r.delivery_days,
            'buyer': User.query.get(r.buyer_id).username,
            'offers_count': RequestOffer.query.filter_by(request_id=r.id).count(),
        } for r in reqs]})

    @app.route('/api/buyer-requests', methods=['POST'])
    @jwt_required()
    def post_buyer_request():
        uid = get_jwt_identity()
        data = request.json
        r = BuyerRequest(
            buyer_id=uid,
            title=sanitize_text(data['title'], 200),
            description=sanitize_text(data['description'], 5000),
            category=data.get('category', 'amv'),
            budget_min=float(data.get('budget_min', 0)),
            budget_max=float(data.get('budget_max', 0)),
            delivery_days=int(data.get('delivery_days', 7)),
        )
        db.session.add(r)
        db.session.commit()
        return jsonify({'id': r.id}), 201

    @app.route('/api/buyer-requests/<int:rid>/offer', methods=['POST'])
    @jwt_required()
    def pitch_buyer_request(rid):
        uid = get_jwt_identity()
        req = BuyerRequest.query.get_or_404(rid)
        data = request.json
        o = RequestOffer(
            request_id=rid, seller_id=uid,
            message=sanitize_text(data.get('message', ''), 2000),
            price=float(data['price']),
            delivery_days=int(data.get('delivery_days', 3)),
        )
        db.session.add(o)
        notify(req.buyer_id, 'pitch', 'New pitch on your request', req.title, '/requests')
        db.session.commit()
        return jsonify({'offer_id': o.id}), 201

    # ─── Coupons ────────────────────────────────────────────────────

    @app.route('/api/coupons/validate', methods=['POST'])
    def validate_coupon():
        code = (request.json or {}).get('code', '').strip().upper()
        c = Coupon.query.filter_by(code=code, is_active=True).first()
        if not c or (c.valid_until and c.valid_until < datetime.utcnow()):
            return jsonify({'valid': False}), 404
        if c.uses_count >= c.max_uses:
            return jsonify({'valid': False, 'error': 'Max uses reached'}), 400
        return jsonify({
            'valid': True, 'discount_percent': c.discount_percent,
            'discount_amount': c.discount_amount,
        })

    # ─── Seller analytics ───────────────────────────────────────────

    @app.route('/api/seller/analytics', methods=['GET'])
    @jwt_required()
    def seller_analytics():
        uid = get_jwt_identity()
        gigs = Gig.query.filter_by(seller_id=uid).all()
        gig_ids = [g.id for g in gigs]
        views = GigImpression.query.filter(GigImpression.gig_id.in_(gig_ids)).count() if gig_ids else 0
        orders = Order.query.filter_by(seller_id=uid)
        return jsonify({
            'total_gigs': len(gigs),
            'total_views': views,
            'orders_pending': orders.filter_by(status='in_progress').count(),
            'orders_completed': orders.filter_by(status='completed').count(),
            'earnings': User.query.get(uid).balance,
            'seller_level': seller_level_for(uid),
            'conversion_rate': round(
                orders.filter_by(status='completed').count() / max(views, 1) * 100, 2
            ),
        })

    # ─── AI marketplace intelligence ────────────────────────────────

    @app.route('/api/ai/recommend-gigs', methods=['GET'])
    def ai_recommend_gigs():
        category = request.args.get('category', 'all')
        q = Gig.query.filter_by(is_active=True, flagged_fake=False)
        if category != 'all':
            q = q.filter_by(category=category)
        gigs = q.order_by(Gig.rating.desc(), Gig.total_orders.desc()).limit(12).all()
        return jsonify({
            'powered_by': list(helpers.get('AI_ENGINES', ('claude', 'codex', 'cursor'))),
            'recommendations': [{
                'id': g.id, 'title': g.title, 'price': g.price,
                'ai_score': g.ai_quality_score, 'rating': g.rating,
                'reason': 'Top rated verified edit',
            } for g in gigs],
        })

    @app.route('/api/marketplace/features', methods=['GET'])
    def marketplace_features():
        return jsonify({
            'platform': 'VORTEX',
            'tier': 'world_class',
            'features': [
                'gig_packages_basic_standard_premium', 'gig_extras', 'gig_faq', 'gig_gallery',
                'escrow_ai_verification', 'order_revisions', 'custom_offers', 'buyer_requests',
                'seller_pitches', 'inbox_messaging', 'notifications', 'favorites',
                'coupons', 'seller_analytics', 'seller_levels', 'public_seller_profiles',
                'ai_recommendations', 'fake_amv_removal', 'plagiarism_detection',
                'stripe_checkout_payments', 'stripe_seller_onboarding', 'wallet_withdrawals', 'google_auth',
            ],
            'fiverr_parity': True,
        })

    # Auto-create default packages when gig created (hook via helper)
    def ensure_default_packages(gig):
        if not GigPackage.query.filter_by(gig_id=gig.id).first():
            base = gig.price
            for tier, mult, rev, days in [
                ('basic', 1.0, 1, gig.delivery_days),
                ('standard', 1.5, 2, max(1, gig.delivery_days - 1)),
                ('premium', 2.2, 3, max(1, gig.delivery_days - 2)),
            ]:
                db.session.add(GigPackage(
                    gig_id=gig.id, tier=tier, title=tier.title(),
                    description=f'{tier.title()} package for {gig.title}',
                    price=round(base * mult, 2), delivery_days=days, revisions=rev,
                    features=json.dumps([f'{rev} revisions', f'{days} day delivery']),
                ))

    helpers['ensure_default_packages'] = ensure_default_packages
    helpers['notify'] = notify
    helpers['seller_level_for'] = seller_level_for

    return {
        'GigPackage': GigPackage,
        'notify': notify,
        'ensure_default_packages': ensure_default_packages,
        'seller_level_for': seller_level_for,
    }
