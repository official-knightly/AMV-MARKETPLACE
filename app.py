from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

from dotenv import load_dotenv
load_dotenv()
import json
import hashlib
import re
import tempfile
import random
import cv2
import numpy as np
from PIL import Image
import io
import base64
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import razorpay
import stripe
import threading
import time
from ai_manager import ai_manager
from ai_guard import (
    sanitize_text,
    check_rate_limit,
    apply_security_headers,
    scan_listing_for_fake,
    verify_delivery_for_escrow,
    security_audit_log,
    AUTO_VERIFY_HOURS,
    AI_ENGINES,
)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

try:
    from rembg import remove as rembg_remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///vortex.db')
# Render and some hosted Postgres providers may still expose postgres:// URLs.
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Payment Gateway Setup
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
stripe.api_key = STRIPE_SECRET_KEY

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

# Platform fee — 10% goes to this UPI; seller gets 90% in wallet
PLATFORM_UPI_ID = os.environ.get('PLATFORM_UPI_ID', '7407589434@fam')
PLATFORM_FEE_RATE = float(os.environ.get('PLATFORM_FEE_RATE', '0.10'))

# ==================== DATABASE MODELS ====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    full_name = db.Column(db.String(100))
    profile_image = db.Column(db.String(500))
    bio = db.Column(db.Text)
    is_seller = db.Column(db.Boolean, default=False)
    balance = db.Column(db.Float, default=0.0)
    trust_score = db.Column(db.Float, default=5.0)
    google_id = db.Column(db.String(100), unique=True)
    account_type = db.Column(db.String(20), default='buyer')
    stripe_account_id = db.Column(db.String(120), unique=True)
    stripe_onboarding_complete = db.Column(db.Boolean, default=False)
    upi_id = db.Column(db.String(100))
    bank_account = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    gigs = db.relationship('Gig', backref='seller', lazy=True)
    orders_as_buyer = db.relationship('Order', foreign_keys='Order.buyer_id', backref='buyer', lazy=True)
    orders_as_seller = db.relationship('Order', foreign_keys='Order.seller_id', backref='seller', lazy=True)

class Gig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # amv, gaming, tiktok, motion
    price = db.Column(db.Float, nullable=False)
    delivery_days = db.Column(db.Integer, default=3)
    thumbnail = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    tags = db.Column(db.Text)  # JSON array
    rating = db.Column(db.Float, default=0.0)
    total_orders = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    content_hash = db.Column(db.String(64))  # For plagiarism detection
    ai_quality_score = db.Column(db.Float, default=0.0)
    is_verified_listing = db.Column(db.Boolean, default=False)
    flagged_fake = db.Column(db.Boolean, default=False)
    ai_scan_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='gig', lazy=True)
    reviews = db.relationship('Review', backref='gig', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, cancelled, disputed
    escrow_status = db.Column(db.String(20), default='held')  # held, released, refunded
    payment_id = db.Column(db.String(200))
    payment_method = db.Column(db.String(50))  # razorpay, stripe, upi
    delivery_file = db.Column(db.String(500))
    buyer_message = db.Column(db.Text)
    seller_message = db.Column(db.Text)
    delivered_at = db.Column(db.DateTime)
    buyer_confirmed = db.Column(db.Boolean, default=False)
    ai_verified = db.Column(db.Boolean, default=False)
    ai_verification_score = db.Column(db.Float)
    ai_verification_notes = db.Column(db.Text)
    release_method = db.Column(db.String(30))  # buyer_confirm, ai_auto
    package_id = db.Column(db.Integer)
    coupon_code = db.Column(db.String(30))
    discount_amount = db.Column(db.Float, default=0.0)
    revisions_used = db.Column(db.Integer, default=0)
    max_revisions = db.Column(db.Integer, default=1)
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50))  # upi, bank_transfer
    upi_id = db.Column(db.String(100))
    bank_details = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    transaction_id = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    message_type = db.Column(db.String(20), default='text')  # text, file, system

class DeliveryVerification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    verification_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    quality_score = db.Column(db.Float)
    ai_confidence = db.Column(db.Float)
    ai_analysis = db.Column(db.Text)
    issues_found = db.Column(db.Text)  # JSON
    auto_approved = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ContentFingerprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    fingerprint = db.Column(db.Text, nullable=False)  # Perceptual hash
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PlatformFee(db.Model):
    """Platform fee (10%) credited to PLATFORM_UPI_ID on escrow release"""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    recipient_upi = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Full Fiverr-class marketplace APIs (registered before routes use helpers)
_mp_helpers = {'User': User, 'Gig': Gig, 'Order': Order, 'Review': Review, 'AI_ENGINES': AI_ENGINES}
from marketplace_full import register_marketplace
_mp_exports = register_marketplace(app, db, jwt_required, get_jwt_identity, sanitize_text, _mp_helpers)
GigPackage = _mp_exports['GigPackage']

# Stripe Checkout and Stripe Connect seller verification/payouts
from stripe_payments import register_stripe_routes
register_stripe_routes(app, db, User, Order, Gig)

# Secure order chat + AI moderation + mutual cancellation/refund workflow
from order_chat import register_order_chat_routes
register_order_chat_routes(app, db, User, Order, Message)

# Public AI assistant for finding real marketplace listings
from marketplace_assistant import register_marketplace_assistant
register_marketplace_assistant(app, db, Gig)

# ==================== HELPER FUNCTIONS ====================

def _migrate_schema():
    """Add new columns on existing SQLite DBs."""
    from sqlalchemy import text, inspect
    insp = inspect(db.engine)
    cols_order = {c['name'] for c in insp.get_columns('order')} if insp.has_table('order') else set()
    cols_gig = {c['name'] for c in insp.get_columns('gig')} if insp.has_table('gig') else set()
    cols_user = {c['name'] for c in insp.get_columns('user')} if insp.has_table('user') else set()
    alters = []
    order_new = {
        'delivered_at': 'DATETIME', 'buyer_confirmed': 'BOOLEAN DEFAULT 0',
        'ai_verified': 'BOOLEAN DEFAULT 0', 'ai_verification_score': 'FLOAT',
        'ai_verification_notes': 'TEXT', 'release_method': 'VARCHAR(30)',
        'package_id': 'INTEGER', 'coupon_code': 'VARCHAR(30)',
        'discount_amount': 'FLOAT DEFAULT 0', 'revisions_used': 'INTEGER DEFAULT 0',
        'max_revisions': 'INTEGER DEFAULT 1', 'due_date': 'DATETIME',
    }
    gig_new = {
        'ai_quality_score': 'FLOAT DEFAULT 0', 'is_verified_listing': 'BOOLEAN DEFAULT 0',
        'flagged_fake': 'BOOLEAN DEFAULT 0', 'ai_scan_notes': 'TEXT',
    }
    user_new = {
        'account_type': "VARCHAR(20) DEFAULT 'buyer'",
        'stripe_account_id': 'VARCHAR(120)',
        'stripe_onboarding_complete': 'BOOLEAN DEFAULT 0',
    }
    for name, typ in order_new.items():
        if name not in cols_order:
            alters.append(f'ALTER TABLE "order" ADD COLUMN {name} {typ}')
    for name, typ in gig_new.items():
        if name not in cols_gig:
            alters.append(f'ALTER TABLE gig ADD COLUMN {name} {typ}')
    for name, typ in user_new.items():
        if name not in cols_user:
            alters.append(f'ALTER TABLE "user" ADD COLUMN {name} {typ}')
    with db.engine.connect() as conn:
        for sql in alters:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass


def release_escrow_order(order, method):
    """Complete order and pay seller + platform fee."""
    if order.escrow_status != 'held':
        return None
    order.status = 'completed'
    order.escrow_status = 'released'
    order.completed_at = datetime.utcnow()
    order.release_method = method
    platform_fee, seller_payout = split_escrow_payout(order)
    update_gig_rating(order.gig_id)
    update_seller_trust_score(order.seller_id)
    return platform_fee, seller_payout


def serialize_user(user):
    return {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'full_name': user.full_name,
        'is_seller': user.is_seller,
        'balance': user.balance,
        'trust_score': user.trust_score,
        'profile_image': user.profile_image,
        'upi_id': user.upi_id,
        'stripe_verified': bool(user.stripe_onboarding_complete),
        'account_type': user.account_type or ('seller' if user.is_seller else 'buyer'),
    }


def run_ai_escrow_verify(order_id, app_instance):
    """Background: AI verifies delivery and auto-releases if buyer did not confirm."""
    with app_instance.app_context():
        order = Order.query.get(order_id)
        if not order or order.escrow_status != 'held' or order.buyer_confirmed:
            return
        if not order.delivered_at or not order.delivery_file:
            return
        if order.status == 'disputed':
            return
        gig = Gig.query.get(order.gig_id)
        result = verify_delivery_for_escrow(order, gig)
        order.ai_verification_score = result['score']
        order.ai_verification_notes = json.dumps(result)
        if result['passed']:
            order.ai_verified = True
            release_escrow_order(order, 'ai_auto')
            security_audit_log('escrow_ai_release', f'order={order_id} score={result["score"]}')
        else:
            order.status = 'disputed'
            security_audit_log('escrow_ai_dispute', f'order={order_id} {result["reasons"]}')
        db.session.commit()


def background_escrow_worker(app_instance):
    """Scan orders past AUTO_VERIFY_HOURS — AI releases or disputes; remove fake gigs."""
    with app_instance.app_context():
        cutoff = datetime.utcnow() - timedelta(hours=AUTO_VERIFY_HOURS)
        pending = Order.query.filter(
            Order.escrow_status == 'held',
            Order.buyer_confirmed == False,
            Order.ai_verified == False,
            Order.delivered_at != None,
            Order.delivered_at <= cutoff,
            Order.status != 'disputed',
        ).all()
        for order in pending:
            run_ai_escrow_verify(order.id, app_instance)

        for g in Gig.query.filter_by(is_active=True, flagged_fake=False).limit(50).all():
            scan = scan_listing_for_fake(g.title, g.description or '', g.category, g.video_url, g.thumbnail)
            if scan['is_fake']:
                g.flagged_fake = True
                g.is_active = False
                g.ai_scan_notes = json.dumps(scan)
        db.session.commit()


def start_background_workers(flask_app):
    def loop():
        while True:
            try:
                background_escrow_worker(flask_app)
            except Exception as e:
                security_audit_log('worker_error', str(e))
            time.sleep(120)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


@app.before_request
def vortex_security_gate():
    ip = request.remote_addr or 'unknown'
    if not check_rate_limit(ip):
        security_audit_log('rate_limit', ip)
        return jsonify({'error': 'Too many requests — protected by VORTEX AI Guard'}), 429
    if request.method in ('POST', 'PUT', 'PATCH') and request.is_json:
        raw = request.get_data(as_text=True) or ''
        for pat in (r'<script', r'javascript:', r'union\s+select', r'drop\s+table'):
            if re.search(pat, raw, re.I):
                security_audit_log('blocked_request', f'{ip} {request.path}')
                return jsonify({'error': 'Request blocked by AI security'}), 400


@app.after_request
def vortex_security_headers(response):
    return apply_security_headers(response)


def split_escrow_payout(order):
    """Release escrow: seller gets (100 - fee)%, platform fee logged to PLATFORM_UPI_ID"""
    fee = round(order.amount * PLATFORM_FEE_RATE, 2)
    seller_payout = round(order.amount - fee, 2)
    seller = User.query.get(order.seller_id)
    seller.balance += seller_payout
    record = PlatformFee(
        order_id=order.id,
        amount=fee,
        recipient_upi=PLATFORM_UPI_ID,
    )
    db.session.add(record)
    return fee, seller_payout

def calculate_perceptual_hash(image_data):
    """Calculate perceptual hash for plagiarism detection"""
    try:
        img = Image.open(io.BytesIO(image_data))
        img = img.convert('L').resize((8, 8), Image.LANCZOS)
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        bits = ''.join(['1' if pixel > avg else '0' for pixel in pixels])
        return hex(int(bits, 2))[2:].zfill(16)
    except:
        return None

def hamming_distance(hash1, hash2):
    """Calculate similarity between two hashes"""
    if not hash1 or not hash2:
        return 100
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

def detect_plagiarism(content_hash, threshold=5):
    """Check if content is stolen"""
    all_fingerprints = ContentFingerprint.query.all()
    for fp in all_fingerprints:
        distance = hamming_distance(content_hash, fp.fingerprint)
        if distance <= threshold:
            return True, fp.gig_id
    return False, None

def extract_video_frame_hashes(video_path, max_frames=12):
    """Sample frames from video for stolen-edit detection"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    step = max(1, total // max_frames)
    hashes = []
    for i in range(0, min(total, max_frames * step), step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            break
        _, buf = cv2.imencode('.jpg', frame)
        h = calculate_perceptual_hash(buf.tobytes())
        if h:
            hashes.append(h)
    cap.release()
    return hashes

def detect_video_plagiarism(frame_hashes, threshold=6):
    """Match video frames against stored fingerprints"""
    if not frame_hashes:
        return False, None, 0.0
    all_fingerprints = ContentFingerprint.query.all()
    best_match = None
    best_score = 0
    for fp in all_fingerprints:
        matches = sum(1 for h in frame_hashes if hamming_distance(h, fp.fingerprint) <= threshold)
        score = matches / len(frame_hashes)
        if score > best_score:
            best_score = score
            best_match = fp.gig_id
    if best_score >= 0.35:
        return True, best_match, round(best_score, 2)
    return False, None, best_score

def remove_background_cv2(img_bytes):
    """Fallback background removal using GrabCut"""
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    mask = np.zeros(img.shape[:2], np.uint8)
    rect = (10, 10, img.shape[1] - 20, img.shape[0] - 20)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(img, mask, rect, bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
    rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = mask2 * 255
    _, buf = cv2.imencode('.png', rgba)
    return buf.tobytes()

def apply_chroma_key(img_bytes, key_color=(0, 255, 0), tolerance=40, feather=3):
    """Remove green screen from image"""
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    key = np.uint8([[key_color]])
    key_hsv = cv2.cvtColor(key, cv2.COLOR_BGR2HSV)[0][0]
    lower = np.array([max(0, key_hsv[0] - tolerance // 2), 40, 40])
    upper = np.array([min(179, key_hsv[0] + tolerance // 2), 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    if feather > 0:
        mask = cv2.GaussianBlur(mask, (feather * 2 + 1, feather * 2 + 1), 0)
    rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = 255 - mask
    _, buf = cv2.imencode('.png', rgba)
    return buf.tobytes()

def search_relevance_score(gig, query_tokens):
    """Score gig relevance for powerful search"""
    if not query_tokens:
        return gig.rating * 10 + gig.total_orders
    title = (gig.title or '').lower()
    desc = (gig.description or '').lower()
    tags = (gig.tags or '').lower()
    seller = User.query.get(gig.seller_id)
    seller_name = (seller.username if seller else '').lower()
    score = gig.rating * 2 + min(gig.total_orders, 50) * 0.1
    for token in query_tokens:
        if token in title:
            score += 25
        if title.startswith(token):
            score += 10
        if token in desc:
            score += 8
        if token in tags:
            score += 12
        if token in seller_name:
            score += 6
        if token in (gig.category or '').lower():
            score += 15
    return score

def update_gig_rating(gig_id):
    """Recalculate gig rating based on reviews"""
    reviews = Review.query.filter_by(gig_id=gig_id).all()
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        gig = Gig.query.get(gig_id)
        gig.rating = round(avg_rating, 1)
        db.session.commit()

def update_seller_trust_score(user_id):
    """Calculate seller trust score based on performance"""
    user = User.query.get(user_id)
    orders = Order.query.filter_by(seller_id=user_id, status='completed').all()
    
    if not orders:
        return
    
    total_orders = len(orders)
    on_time_delivery = sum(1 for o in orders if o.completed_at and 
                           (o.completed_at - o.created_at).days <= 
                           Gig.query.get(o.gig_id).delivery_days)
    
    reviews = Review.query.join(Order).filter(Order.seller_id == user_id).all()
    avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 5.0
    
    delivery_rate = (on_time_delivery / total_orders) * 100 if total_orders > 0 else 100
    trust_score = (avg_rating * 0.6) + (delivery_rate / 100 * 5 * 0.4)
    
    user.trust_score = round(trust_score, 1)
    db.session.commit()

# ==================== AUTH ROUTES ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not email or not username or not password:
        return jsonify({'error': 'Email, username and password are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 400
    user = User(
        email=email,
        username=username,
        full_name=(data.get('full_name') or '').strip(),
        password_hash=generate_password_hash(password),
        account_type='buyer'
    )
    db.session.add(user)
    db.session.commit()
    access_token = create_access_token(identity=user.id, expires_delta=timedelta(days=30))
    return jsonify({'token': access_token, 'user': serialize_user(user)}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    identifier = (data.get('email') or '').strip()
    user = User.query.filter_by(email=identifier).first()
    if not user:
        user = User.query.filter_by(username=identifier).first()
    
    if not user or not user.password_hash or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    access_token = create_access_token(identity=user.id, expires_delta=timedelta(days=30))
    
    return jsonify({
        'token': access_token,
        'user': serialize_user(user)
    })

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    """Google OAuth login"""
    try:
        if not GOOGLE_CLIENT_ID:
            return jsonify({'error': 'Google OAuth is not configured on the server'}), 400
        token = request.json['token']
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        
        google_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')
        
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                user.google_id = google_id
            else:
                username = email.split('@')[0] + str(User.query.count() + 1)
                user = User(
                    email=email,
                    username=username,
                    full_name=name,
                    google_id=google_id,
                    profile_image=picture,
                    account_type='buyer'
                )
                db.session.add(user)
        
        db.session.commit()
        
        access_token = create_access_token(identity=user.id, expires_delta=timedelta(days=30))
        
        return jsonify({
            'token': access_token,
            'user': serialize_user(user)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    return jsonify(serialize_user(user))


# ==================== FILE UPLOAD ROUTES ====================

@app.route('/api/upload/video', methods=['POST'])
@jwt_required()
def upload_video():
    """Upload video file"""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    video = request.files['video']
    if video.filename == '':
        return jsonify({'error': 'No video selected'}), 400
    
    # Check file extension
    allowed_extensions = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
    ext = video.filename.rsplit('.', 1)[1].lower() if '.' in video.filename else ''
    if ext not in allowed_extensions:
        return jsonify({'error': 'Invalid video format'}), 400
    
    # Generate unique filename
    user_id = get_jwt_identity()
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"video_{user_id}_{timestamp}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    # Save file
    video.save(filepath)
    
    # Return URL
    video_url = f"/uploads/{filename}"
    return jsonify({'url': video_url, 'filename': filename})

@app.route('/api/upload/image', methods=['POST'])
@jwt_required()
def upload_image():
    """Upload image file (thumbnail)"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    image = request.files['image']
    if image.filename == '':
        return jsonify({'error': 'No image selected'}), 400
    
    # Check file extension
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    ext = image.filename.rsplit('.', 1)[1].lower() if '.' in image.filename else ''
    if ext not in allowed_extensions:
        return jsonify({'error': 'Invalid image format'}), 400
    
    # Generate unique filename
    user_id = get_jwt_identity()
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"thumb_{user_id}_{timestamp}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    # Save file
    image.save(filepath)
    
    # Return URL
    image_url = f"/uploads/{filename}"
    return jsonify({'url': image_url, 'filename': filename})

@app.route('/uploads/<filename>')
def serve_upload(filename):
    """Serve uploaded files"""
    return send_file(os.path.join(UPLOAD_FOLDER, filename))

# ==================== AI ANALYSIS ROUTES ====================

@app.route('/api/ai/analyze-gig', methods=['POST'])
@jwt_required()
def analyze_gig():
    """AI analyzes gig before publishing"""
    data = request.json
    
    try:
        title = sanitize_text(data.get('title', ''), 200)
        description = sanitize_text(data.get('description', ''), 8000)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    # Run AI analysis
    scan = scan_listing_for_fake(
        title,
        description,
        data.get('category', 'amv'),
        data.get('video_url'),
        data.get('thumbnail'),
    )
    
    # Add quality score and suggestions
    quality_score = scan.get('score', 5.0)
    
    # Generate AI suggestions
    suggestions = []
    if quality_score < 8:
        if len(title) < 20:
            suggestions.append("Make your title more descriptive (at least 20 characters)")
        if len(description) < 100:
            suggestions.append("Add more details to your description (at least 100 characters)")
        if not data.get('video_url'):
            suggestions.append("Add a portfolio video to showcase your work")
        if data.get('price', 0) < 100:
            suggestions.append("Consider pricing your service at least ₹100 for quality work")
    
    if scan.get('is_fake'):
        suggestions.extend(scan.get('reasons', []))
    
    return jsonify({
        'passed': scan.get('passed', True),
        'is_fake': scan.get('is_fake', False),
        'quality_score': quality_score,
        'confidence': scan.get('confidence', 0.8),
        'suggestions': suggestions,
        'reasons': scan.get('reasons', []),
        'analysis': scan.get('analysis', 'AI analysis complete'),
    })

# ==================== GIG ROUTES ====================

@app.route('/api/gigs', methods=['GET'])
def get_gigs():
    category = request.args.get('category', 'all')
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 12))
    
    query = Gig.query.filter_by(is_active=True, flagged_fake=False)
    
    if category != 'all':
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(Gig.title.contains(search) | Gig.description.contains(search))
    
    gigs = query.order_by(Gig.rating.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'gigs': [{
            'id': g.id,
            'title': g.title,
            'description': g.description,
            'category': g.category,
            'price': g.price,
            'delivery_days': g.delivery_days,
            'thumbnail': g.thumbnail,
            'rating': g.rating,
            'total_orders': g.total_orders,
            'seller': {
                'id': g.seller.id,
                'username': g.seller.username,
                'profile_image': g.seller.profile_image,
                'trust_score': g.seller.trust_score
            }
        } for g in gigs.items],
        'total': gigs.total,
        'pages': gigs.pages,
        'current_page': page
    })

@app.route('/api/gigs/<int:gig_id>', methods=['GET'])
def get_gig(gig_id):
    gig = Gig.query.get_or_404(gig_id)
    reviews = Review.query.filter_by(gig_id=gig_id).order_by(Review.created_at.desc()).limit(10).all()
    
    return jsonify({
        'id': gig.id,
        'title': gig.title,
        'description': gig.description,
        'category': gig.category,
        'price': gig.price,
        'delivery_days': gig.delivery_days,
        'thumbnail': gig.thumbnail,
        'video_url': gig.video_url,
        'rating': gig.rating,
        'total_orders': gig.total_orders,
        'tags': json.loads(gig.tags) if gig.tags else [],
        'seller': {
            'id': gig.seller.id,
            'username': gig.seller.username,
            'full_name': gig.seller.full_name,
            'profile_image': gig.seller.profile_image,
            'trust_score': gig.seller.trust_score,
            'bio': gig.seller.bio
        },
        'reviews': [{
            'id': r.id,
            'rating': r.rating,
            'comment': r.comment,
            'created_at': r.created_at.isoformat(),
            'reviewer': User.query.get(r.reviewer_id).username
        } for r in reviews],
        'packages': [{
            'id': p.id, 'tier': p.tier, 'title': p.title,
            'price': p.price, 'delivery_days': p.delivery_days, 'revisions': p.revisions,
        } for p in GigPackage.query.filter_by(gig_id=gig.id).order_by(GigPackage.price).all()],
        'seller_level': _mp_helpers['seller_level_for'](gig.seller_id),
    })

@app.route('/api/gigs', methods=['POST'])
@jwt_required()
def create_gig():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user.is_seller:
        user.is_seller = True
        db.session.commit()
    
    data = request.json

    try:
        title = sanitize_text(data['title'], 200)
        description = sanitize_text(data['description'], 8000)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    ai_scan = scan_listing_for_fake(
        title, description, data['category'],
        data.get('video_url'), data.get('thumbnail'),
    )
    if ai_scan['is_fake']:
        security_audit_log('blocked_fake_gig', f"user={user_id} {ai_scan['reasons']}")
        return jsonify({
            'error': 'Listing blocked — AI detected fake or low-quality AMV',
            'ai_scan': ai_scan,
        }), 400
    
    # Check for plagiarism if thumbnail provided
    if data.get('thumbnail_data'):
        content_hash = calculate_perceptual_hash(base64.b64decode(data['thumbnail_data']))
        is_stolen, original_gig_id = detect_plagiarism(content_hash)
        
        if is_stolen:
            return jsonify({'error': 'Content appears to be plagiarized', 'original_gig_id': original_gig_id}), 400
    
    gig = Gig(
        seller_id=user_id,
        title=title,
        description=description,
        category=data['category'],
        price=float(data['price']),
        delivery_days=int(data.get('delivery_days', 3)),
        thumbnail=data.get('thumbnail'),
        video_url=data.get('video_url'),
        tags=json.dumps(data.get('tags', [])),
        ai_quality_score=ai_scan['score'],
        is_verified_listing=ai_scan['passed'],
        flagged_fake=False,
        ai_scan_notes=json.dumps(ai_scan),
    )
    
    db.session.add(gig)
    db.session.flush()

    if _mp_helpers.get('ensure_default_packages'):
        _mp_helpers['ensure_default_packages'](gig)

    db.session.commit()
    
    # Store content fingerprint
    if data.get('thumbnail_data'):
        fingerprint = ContentFingerprint(
            gig_id=gig.id,
            fingerprint=content_hash
        )
        db.session.add(fingerprint)
        db.session.commit()
    
    return jsonify({'id': gig.id, 'message': 'Gig created successfully'}), 201

@app.route('/api/gigs/<int:gig_id>', methods=['PUT'])
@jwt_required()
def update_gig(gig_id):
    user_id = get_jwt_identity()
    gig = Gig.query.get_or_404(gig_id)
    
    if gig.seller_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    
    gig.title = data.get('title', gig.title)
    gig.description = data.get('description', gig.description)
    gig.price = float(data.get('price', gig.price))
    gig.delivery_days = int(data.get('delivery_days', gig.delivery_days))
    gig.is_active = data.get('is_active', gig.is_active)
    
    db.session.commit()
    
    return jsonify({'message': 'Gig updated successfully'})

# ==================== ORDER & PAYMENT ROUTES ====================

@app.route('/api/orders/create', methods=['POST'])
@jwt_required()
def create_order():
    buyer_id = get_jwt_identity()
    data = request.json
    
    gig = Gig.query.get_or_404(data['gig_id'])
    
    if gig.seller_id == buyer_id:
        return jsonify({'error': 'Cannot order your own gig'}), 400
    
    order = Order(
        buyer_id=buyer_id,
        seller_id=gig.seller_id,
        gig_id=gig.id,
        amount=gig.price,
        buyer_message=data.get('message', '')
    )
    
    db.session.add(order)
    db.session.commit()
    
    return jsonify({
        'order_id': order.id,
        'amount': order.amount,
        'message': 'Order created, proceed to payment'
    }), 201

@app.route('/api/payment/razorpay/create', methods=['POST'])
@jwt_required()
def create_razorpay_payment():
    return jsonify({'error': 'Razorpay is disabled. Use Stripe Checkout for all marketplace payments.'}), 410
    data = request.json
    order = Order.query.get_or_404(data['order_id'])
    
    try:
        if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
            return jsonify({'error': 'Razorpay is not configured on the server'}), 400
        razorpay_order = razorpay_client.order.create({
            'amount': int(order.amount * 100),  # Convert to paise
            'currency': 'INR',
            'payment_capture': 1
        })
        
        return jsonify({
            'razorpay_order_id': razorpay_order['id'],
            'amount': order.amount,
            'currency': 'INR',
            'key_id': RAZORPAY_KEY_ID
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/payment/razorpay/verify', methods=['POST'])
@jwt_required()
def verify_razorpay_payment():
    return jsonify({'error': 'Razorpay is disabled. Use Stripe Checkout for all marketplace payments.'}), 410
    data = request.json
    order = Order.query.get_or_404(data['order_id'])
    
    try:
        if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
            return jsonify({'error': 'Razorpay is not configured on the server'}), 400
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        })
        
        order.payment_id = data['razorpay_payment_id']
        order.payment_method = 'razorpay'
        order.status = 'in_progress'
        order.escrow_status = 'held'
        
        gig = Gig.query.get(order.gig_id)
        gig.total_orders += 1
        
        db.session.commit()
        
        return jsonify({'message': 'Payment successful', 'order_id': order.id})
    except Exception as e:
        return jsonify({'error': 'Payment verification failed', 'details': str(e)}), 400

@app.route('/api/payment/upi/create', methods=['POST'])
@jwt_required()
def create_upi_payment():
    """Legacy direct UPI checkout disabled; Stripe Checkout is the only order payment path."""
    return jsonify({'error': 'Direct UPI checkout is disabled. Use Stripe Checkout.'}), 410
    data = request.json
    order = Order.query.get_or_404(data['order_id'])
    
    amount = order.amount
    platform_fee = round(amount * PLATFORM_FEE_RATE, 2)
    upi_link = (
        f"upi://pay?pa={PLATFORM_UPI_ID}&pn=Vortex&am={amount}&cu=INR"
        f"&tn=Order{order.id}"
    )
    
    return jsonify({
        'upi_link': upi_link,
        'order_id': order.id,
        'amount': amount,
        'platform_fee': platform_fee,
        'platform_upi': PLATFORM_UPI_ID,
        'seller_payout_on_release': round(amount - platform_fee, 2),
        'qr_data': upi_link,
    })

@app.route('/api/orders/<int:order_id>/complete', methods=['POST'])
@jwt_required()
def complete_order(order_id):
    user_id = get_jwt_identity()
    order = Order.query.get_or_404(order_id)
    
    if order.buyer_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    if not order.delivery_file:
        return jsonify({'error': 'Seller has not delivered yet — escrow still held'}), 400

    if order.status == 'disputed':
        return jsonify({'error': 'Order is in dispute — contact support'}), 400

    order.buyer_confirmed = True
    payout = release_escrow_order(order, 'buyer_confirm')
    if not payout:
        return jsonify({'error': 'Escrow already settled'}), 400
    platform_fee, seller_payout = payout
    db.session.commit()
    security_audit_log('buyer_confirm', f'order={order_id}')

    return jsonify({
        'message': 'You confirmed receipt — payment released to seller',
        'seller_payout': seller_payout,
        'platform_fee': platform_fee,
        'platform_upi': PLATFORM_UPI_ID,
        'release_method': 'buyer_confirm',
    })

@app.route('/api/orders/<int:order_id>/deliver', methods=['POST'])
@jwt_required()
def deliver_order(order_id):
    user_id = get_jwt_identity()
    order = Order.query.get_or_404(order_id)
    
    if order.seller_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    try:
        file_url = sanitize_text(data.get('file_url', ''), 2000)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    order.delivery_file = file_url
    order.seller_message = data.get('message', '')
    order.delivered_at = datetime.utcnow()
    order.status = 'in_progress'

    db.session.commit()
    security_audit_log('delivery', f'order={order_id}')

    return jsonify({
        'message': 'Delivery submitted. Buyer must confirm they received the AMV. If not, AI verifies in background.',
        'auto_ai_verify_hours': AUTO_VERIFY_HOURS,
        'escrow_status': 'held',
        'ai_engines': list(AI_ENGINES),
    })

@app.route('/api/orders/my-orders', methods=['GET'])
@jwt_required()
def get_my_orders():
    user_id = get_jwt_identity()
    role = request.args.get('role', 'buyer')  # buyer or seller
    
    if role == 'buyer':
        orders = Order.query.filter_by(buyer_id=user_id).order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.filter_by(seller_id=user_id).order_by(Order.created_at.desc()).all()
    
    return jsonify({
        'orders': [{
            'id': o.id,
            'gig_title': Gig.query.get(o.gig_id).title,
            'amount': o.amount,
            'status': o.status,
            'escrow_status': o.escrow_status,
            'due_date': o.due_date.isoformat() if o.due_date else None,
            'max_revisions': o.max_revisions,
            'revisions_used': o.revisions_used,
            'delivery_file': o.delivery_file,
            'delivered_at': o.delivered_at.isoformat() if o.delivered_at else None,
            'buyer_confirmed': o.buyer_confirmed,
            'ai_verified': o.ai_verified,
            'ai_verification_score': o.ai_verification_score,
            'release_method': o.release_method,
            'created_at': o.created_at.isoformat(),
            'buyer': User.query.get(o.buyer_id).username,
            'seller': User.query.get(o.seller_id).username,
        } for o in orders]
    })

# ==================== WITHDRAWAL ROUTES ====================

@app.route('/api/withdrawal/request', methods=['POST'])
@jwt_required()
def request_withdrawal():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.json
    
    amount = float(data['amount'])
    
    if amount > user.balance:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    if amount < 10:
        return jsonify({'error': 'Minimum withdrawal is ₹10'}), 400
    
    withdrawal = Withdrawal(
        user_id=user_id,
        amount=amount,
        method=data['method'],
        upi_id=data.get('upi_id'),
        bank_details=json.dumps(data.get('bank_details', {}))
    )
    
    user.balance -= amount
    
    db.session.add(withdrawal)
    db.session.commit()
    
    return jsonify({'message': 'Withdrawal request submitted', 'withdrawal_id': withdrawal.id}), 201

@app.route('/api/withdrawal/history', methods=['GET'])
@jwt_required()
def withdrawal_history():
    user_id = get_jwt_identity()
    withdrawals = Withdrawal.query.filter_by(user_id=user_id).order_by(Withdrawal.created_at.desc()).all()
    
    return jsonify({
        'withdrawals': [{
            'id': w.id,
            'amount': w.amount,
            'method': w.method,
            'status': w.status,
            'created_at': w.created_at.isoformat()
        } for w in withdrawals]
    })

# ==================== AI TOOLS ROUTES ====================

@app.route('/api/ai/remove-background', methods=['POST'])
def remove_background():
    """AI Background removal — image or video (first frame preview for video)"""
    media_type = request.form.get('type', 'image')
    file = request.files.get('image') or request.files.get('video') or request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    raw = file.read()
    if media_type == 'video' or (file.filename and file.filename.lower().endswith(('.mp4', '.webm', '.mov', '.avi'))):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4', dir=UPLOAD_FOLDER)
        tmp.write(raw)
        tmp.close()
        cap = cv2.VideoCapture(tmp.name)
        ret, frame = cap.read()
        cap.release()
        os.unlink(tmp.name)
        if not ret:
            return jsonify({'error': 'Could not read video'}), 400
        _, buf = cv2.imencode('.jpg', frame)
        raw = buf.tobytes()

    try:
        if REMBG_AVAILABLE:
            out = rembg_remove(raw)
        else:
            out = remove_background_cv2(raw)
        if not out:
            return jsonify({'error': 'Processing failed'}), 500
        b64 = base64.b64encode(out).decode('utf-8')
        return jsonify({
            'message': 'Background removed',
            'processed_image': f'data:image/png;base64,{b64}',
            'engine': 'rembg' if REMBG_AVAILABLE else 'opencv'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/green-screen', methods=['POST'])
def green_screen():
    """Remove green screen from image or video frame"""
    file = request.files.get('image') or request.files.get('video') or request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    tolerance = int(request.form.get('tolerance', 40))
    feather = int(request.form.get('feather', 3))
    key_r = int(request.form.get('key_r', 0))
    key_g = int(request.form.get('key_g', 255))
    key_b = int(request.form.get('key_b', 0))

    raw = file.read()
    if file.filename and file.filename.lower().endswith(('.mp4', '.webm', '.mov', '.avi')):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4', dir=UPLOAD_FOLDER)
        tmp.write(raw)
        tmp.close()
        cap = cv2.VideoCapture(tmp.name)
        ret, frame = cap.read()
        cap.release()
        os.unlink(tmp.name)
        if not ret:
            return jsonify({'error': 'Could not read video'}), 400
        _, buf = cv2.imencode('.jpg', frame)
        raw = buf.tobytes()

    out = apply_chroma_key(raw, key_color=(key_b, key_g, key_r), tolerance=tolerance, feather=feather)
    if not out:
        return jsonify({'error': 'Processing failed'}), 500
    b64 = base64.b64encode(out).decode('utf-8')
    return jsonify({
        'message': 'Green screen removed',
        'processed_image': f'data:image/png;base64,{b64}'
    })

@app.route('/api/ai/detect-plagiarism', methods=['POST'])
def detect_plagiarism_api():
    """Check if image or video edit is stolen"""
    file = request.files.get('image') or request.files.get('video') or request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    raw = file.read()
    is_video = file.filename and file.filename.lower().endswith(('.mp4', '.webm', '.mov', '.avi'))

    if is_video:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4', dir=UPLOAD_FOLDER)
        tmp.write(raw)
        tmp.close()
        frame_hashes = extract_video_frame_hashes(tmp.name)
        os.unlink(tmp.name)
        is_stolen, original_gig_id, confidence = detect_video_plagiarism(frame_hashes)
    else:
        content_hash = calculate_perceptual_hash(raw)
        is_stolen, original_gig_id = detect_plagiarism(content_hash)
        confidence = 0.92 if is_stolen else 0.0

    if is_stolen:
        original_gig = Gig.query.get(original_gig_id)
        return jsonify({
            'is_plagiarized': True,
            'confidence': confidence,
            'media_type': 'video' if is_video else 'image',
            'original_gig': {
                'id': original_gig.id,
                'title': original_gig.title,
                'seller': original_gig.seller.username
            } if original_gig else None
        })

    return jsonify({
        'is_plagiarized': False,
        'confidence': confidence,
        'media_type': 'video' if is_video else 'image'
    })

@app.route('/api/escrow/<int:order_id>/dispute', methods=['POST'])
@jwt_required()
def dispute_escrow(order_id):
    """Buyer opens escrow dispute — funds stay held"""
    user_id = get_jwt_identity()
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    if order.escrow_status != 'held':
        return jsonify({'error': 'Escrow not in held state'}), 400
    data = request.json or {}
    order.status = 'disputed'
    order.buyer_message = data.get('reason', order.buyer_message or 'Dispute opened')
    db.session.commit()
    return jsonify({'message': 'Dispute opened. Escrow funds remain held until resolved.', 'order_id': order.id})

@app.route('/api/escrow/<int:order_id>/refund', methods=['POST'])
@jwt_required()
def refund_escrow(order_id):
    """Legacy wallet-credit refund disabled; Stripe refunds must be created against the original payment."""
    return jsonify({'error': 'Manual wallet refunds are disabled. Use the order cancellation flow so the original Stripe payment can be refunded.'}), 410
    user_id = get_jwt_identity()
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != user_id and order.seller_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    if order.escrow_status != 'held':
        return jsonify({'error': 'Escrow already settled'}), 400
    buyer = User.query.get(order.buyer_id)
    buyer.balance += order.amount
    order.escrow_status = 'refunded'
    order.status = 'cancelled'
    db.session.commit()
    return jsonify({'message': 'Escrow refunded to buyer balance'})

@app.route('/api/reviews', methods=['POST'])
@jwt_required()
def create_review():
    user_id = get_jwt_identity()
    data = request.json
    
    order = Order.query.get_or_404(data['order_id'])
    
    if order.buyer_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if order.status != 'completed':
        return jsonify({'error': 'Order must be completed first'}), 400
    
    # AI-powered review analysis
    analysis = ai_manager.analyze_review(
        data.get('comment', ''),
        float(data['rating'])
    )
    
    # Check if review seems fake
    if not analysis['is_genuine']:
        return jsonify({
            'error': 'Review appears suspicious',
            'reason': 'AI detected potential fake review'
        }), 400
    
    review = Review(
        order_id=order.id,
        gig_id=order.gig_id,
        reviewer_id=user_id,
        rating=float(data['rating']),
        comment=data.get('comment', '')
    )
    
    db.session.add(review)
    db.session.commit()
    
    update_gig_rating(order.gig_id)
    update_seller_trust_score(order.seller_id)
    
    return jsonify({
        'message': 'Review submitted successfully',
        'ai_analysis': {
            'sentiment': analysis['sentiment'],
            'key_points': analysis['key_points']
        }
    }), 201

# ==================== SEARCH ROUTES ====================

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    category = request.args.get('category', 'all')
    min_price = float(request.args.get('min_price', 0))
    max_price = float(request.args.get('max_price', 100000))
    min_rating = float(request.args.get('min_rating', 0))
    sort = request.args.get('sort', 'relevance')  # relevance, price_asc, price_desc, rating, orders
    delivery_max = request.args.get('delivery_max')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 24))

    gigs_query = Gig.query.filter_by(is_active=True, flagged_fake=False)

    if category != 'all':
        gigs_query = gigs_query.filter_by(category=category)

    gigs_query = gigs_query.filter(
        Gig.price >= min_price,
        Gig.price <= max_price,
        Gig.rating >= min_rating
    )

    if delivery_max:
        gigs_query = gigs_query.filter(Gig.delivery_days <= int(delivery_max))

    all_gigs = gigs_query.all()
    tokens = [t.lower() for t in re.split(r'\W+', query) if len(t) > 1]

    if tokens:
        filtered = []
        for g in all_gigs:
            blob = f"{g.title} {g.description} {g.tags or ''} {g.category}".lower()
            if any(t in blob for t in tokens):
                filtered.append(g)
        all_gigs = filtered

    scored = [(g, search_relevance_score(g, tokens)) for g in all_gigs]
    if sort == 'price_asc':
        scored.sort(key=lambda x: x[0].price)
    elif sort == 'price_desc':
        scored.sort(key=lambda x: -x[0].price)
    elif sort == 'rating':
        scored.sort(key=lambda x: (-x[0].rating, -x[0].total_orders))
    elif sort == 'orders':
        scored.sort(key=lambda x: (-x[0].total_orders, -x[0].rating))
    else:
        scored.sort(key=lambda x: -x[1])

    start = (page - 1) * per_page
    page_items = scored[start:start + per_page]

    return jsonify({
        'query': query,
        'total': len(scored),
        'pages': max(1, (len(scored) + per_page - 1) // per_page),
        'current_page': page,
        'results': [{
            'id': g.id,
            'title': g.title,
            'description': (g.description or '')[:200],
            'category': g.category,
            'price': g.price,
            'delivery_days': g.delivery_days,
            'rating': g.rating,
            'total_orders': g.total_orders,
            'thumbnail': g.thumbnail,
            'relevance': round(score, 1),
            'seller': {
                'id': g.seller.id,
                'username': g.seller.username,
                'profile_image': g.seller.profile_image,
                'trust_score': g.seller.trust_score
            }
        } for g, score in page_items]
    })

@app.route('/api/orders/<int:order_id>/request-ai-verify', methods=['POST'])
@jwt_required()
def request_ai_verify(order_id):
    """Buyer requests immediate AI escrow verification (Claude + Codex + Cursor engines)."""
    user_id = get_jwt_identity()
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != user_id and order.seller_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    if not order.delivery_file:
        return jsonify({'error': 'No delivery to verify yet'}), 400
    if order.escrow_status != 'held':
        return jsonify({'error': 'Escrow already settled'}), 400

    gig = Gig.query.get(order.gig_id)
    result = verify_delivery_for_escrow(order, gig)
    order.ai_verification_score = result['score']
    order.ai_verification_notes = json.dumps(result)

    if result['passed']:
        order.ai_verified = True
        if order.buyer_id == user_id or order.seller_id == user_id:
            release_escrow_order(order, 'ai_auto')
        msg = 'AI verified delivery — escrow released to seller'
    else:
        order.status = 'disputed'
        msg = 'AI could not verify delivery — dispute opened, escrow held'

    db.session.commit()
    return jsonify({
        'message': msg,
        'ai_result': result,
        'engines': list(AI_ENGINES),
    })


@app.route('/api/ai/guard/status', methods=['GET'])
def ai_guard_status():
    return jsonify({
        'active': bool(ai_manager.status().get('configured') or os.environ.get('NVIDIA_API_KEY')),
        'provider': ai_manager.status().get('provider'),
        'engines': list(AI_ENGINES),
        'auto_verify_hours': AUTO_VERIFY_HOURS,
        'features': [
            'escrow_buyer_confirm_first',
            'ai_background_escrow_verify',
            'fake_amv_listing_block',
            'rate_limit_and_injection_block',
            'fiverr_full_marketplace',
            'packages_extras_messaging_revisions',
        ],
    })


@app.route('/api/ai/scan-marketplace', methods=['POST'])
@jwt_required()
def scan_marketplace_fake():
    """Background-style sweep: deactivate fake AMVs (admin/seller with JWT)."""
    removed = 0
    gigs = Gig.query.filter_by(is_active=True, flagged_fake=False).all()
    for g in gigs:
        scan = scan_listing_for_fake(g.title, g.description or '', g.category, g.video_url, g.thumbnail)
        if scan['is_fake']:
            g.flagged_fake = True
            g.is_active = False
            g.ai_scan_notes = json.dumps(scan)
            removed += 1
    db.session.commit()
    return jsonify({'removed_fake_listings': removed})


_worker_started = False
_worker_lock = threading.Lock()


def init_vortex():
    with app.app_context():
        db.create_all()
        _migrate_schema()


def ensure_background_workers():
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            start_background_workers(app)
            _worker_started = True


@app.before_request
def _boot_workers_once():
    ensure_background_workers()


init_vortex()

if __name__ == '__main__':
    try:
        # Initialize chat system with SocketIO
        from chat_system import init_chat_system
        socketio = init_chat_system(app, db)
        print("✓ Chat system initialized")
        
        # Initialize email service
        from email_service import init_email_service
        init_email_service(app)
        print("✓ Email service initialized")
        
        print("\n🚀 Server starting on http://localhost:5000")
        print("📊 AI-powered marketplace ready!")
        print("💬 Real-time chat enabled")
        print("🤖 AI verification active")
        
        # Run with SocketIO support for real-time chat
        socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"❌ Server startup error: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to regular Flask if SocketIO fails
        app.run(debug=True, host='0.0.0.0', port=5000)



# ==================== AI-POWERED ENDPOINTS ====================

@app.route('/api/ai/optimize-gig', methods=['POST'])
@jwt_required()
def ai_optimize_gig():
    """AI-powered gig optimization"""
    data = request.json
    
    optimization = ai_manager.optimize_gig_description(
        data['title'],
        data['description'],
        data['category']
    )
    
    return jsonify(optimization)

@app.route('/api/ai/moderate-content', methods=['POST'])
@jwt_required()
def ai_moderate_content():
    """AI content moderation"""
    data = request.json
    
    moderation = ai_manager.moderate_content(data['text'])
    
    return jsonify(moderation)

@app.route('/api/ai/pricing-recommendation', methods=['POST'])
@jwt_required()
def ai_pricing_recommendation():
    """AI-powered pricing recommendations"""
    data = request.json
    
    # Get similar gigs for market analysis
    similar_gigs = Gig.query.filter_by(
        category=data['category'],
        is_active=True
    ).order_by(Gig.rating.desc()).limit(10).all()
    
    market_data = [{
        'title': g.title,
        'price': g.price,
        'rating': g.rating,
        'total_orders': g.total_orders
    } for g in similar_gigs]
    
    recommendation = ai_manager.recommend_pricing(data, market_data)
    
    return jsonify(recommendation)

@app.route('/api/ai/recommendations', methods=['GET'])
@jwt_required()
def ai_get_recommendations():
    """AI-powered personalized gig recommendations"""
    user_id = get_jwt_identity()
    
    # Get user's order history
    orders = Order.query.filter_by(buyer_id=user_id).all()
    history = [{
        'gig_title': Gig.query.get(o.gig_id).title,
        'category': Gig.query.get(o.gig_id).category,
        'rating': Review.query.filter_by(order_id=o.id).first().rating if Review.query.filter_by(order_id=o.id).first() else None
    } for o in orders]
    
    # Get available gigs
    gigs = Gig.query.filter_by(is_active=True).limit(50).all()
    gigs_list = [{
        'id': g.id,
        'title': g.title,
        'category': g.category,
        'price': g.price
    } for g in gigs]
    
    recommended_ids = ai_manager.get_personalized_recommendations(history, gigs_list)
    
    # Get full gig details
    recommended_gigs = [Gig.query.get(gid) for gid in recommended_ids if Gig.query.get(gid)]
    
    return jsonify({
        'recommendations': [{
            'id': g.id,
            'title': g.title,
            'description': g.description,
            'category': g.category,
            'price': g.price,
            'rating': g.rating,
            'seller': g.seller.username
        } for g in recommended_gigs[:10]]
    })

@app.route('/api/ai/analyze-dispute', methods=['POST'])
@jwt_required()
def ai_analyze_dispute():
    """AI-powered dispute analysis"""
    data = request.json
    order = Order.query.get_or_404(data['order_id'])
    
    analysis = ai_manager.analyze_dispute(
        data['buyer_claim'],
        data['seller_response'],
        {
            'amount': order.amount,
            'delivery_days': Gig.query.get(order.gig_id).delivery_days,
            'status': order.status
        }
    )
    
    return jsonify(analysis)

@app.route('/api/ai/score-delivery', methods=['POST'])
@jwt_required()
def ai_score_delivery():
    """AI-powered delivery quality scoring"""
    data = request.json
    
    score = ai_manager.score_delivery_quality(
        data['delivery_notes'],
        data.get('expected_quality', 'high')
    )
    
    return jsonify(score)


# ==================== USER ROLE MANAGEMENT ====================

@app.route('/api/user/set-role', methods=['POST'])
@jwt_required()
def set_user_role():
    """Set user account type (buyer/seller)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.json
    
    role = data.get('role', 'buyer')
    
    if role == 'seller':
        user.is_seller = True
    elif role == 'buyer':
        user.is_seller = user.is_seller
    else:
        return jsonify({'error': 'Invalid role'}), 400

    user.account_type = role
    
    db.session.commit()
    
    return jsonify({
        'message': f'Role set to {role}',
        'user': serialize_user(user)
    })

@app.route('/api/user/switch-role', methods=['POST'])
@jwt_required()
def switch_user_role():
    """Switch between buyer and seller roles"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.json
    
    new_role = data.get('role')
    
    if new_role == 'seller':
        user.is_seller = True
    elif new_role != 'buyer':
        return jsonify({'error': 'Invalid role'}), 400
    user.account_type = new_role
    
    db.session.commit()
    
    return jsonify({
        'message': f'Switched to {new_role} mode',
        'user': serialize_user(user)
    })

@app.route('/api/user/profile', methods=['PUT'])
@jwt_required()
def update_user_profile():
    """Update user profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.json
    
    if 'full_name' in data:
        user.full_name = data['full_name']
    if 'bio' in data:
        user.bio = data['bio']
    if 'upi_id' in data:
        user.upi_id = data['upi_id']
    if 'profile_image' in data:
        user.profile_image = data['profile_image']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Profile updated successfully',
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'bio': user.bio,
            'upi_id': user.upi_id,
            'profile_image': user.profile_image
        }
    })


# ==================== CHAT SYSTEM ENDPOINTS ====================

@app.route('/api/chat/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """Get count of unread messages"""
    user_id = get_jwt_identity()
    
    # Get all orders where user is involved
    orders = Order.query.filter(
        (Order.buyer_id == user_id) | (Order.seller_id == user_id)
    ).all()
    
    order_ids = [o.id for o in orders]
    
    # Count unread messages
    unread_count = Message.query.filter(
        Message.order_id.in_(order_ids),
        Message.sender_id != user_id,
        Message.is_read == False
    ).count()
    
    return jsonify({'unread_count': unread_count})

# ==================== AI-POWERED DELIVERY VERIFICATION ====================

@app.route('/api/orders/<int:order_id>/deliver-with-verification', methods=['POST'])
@jwt_required()
def deliver_order_with_ai_verification(order_id):
    """Deliver order with automatic AI verification"""
    user_id = get_jwt_identity()
    order = Order.query.get_or_404(order_id)
    
    if order.seller_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    
    # Update order with delivery
    order.delivery_file = data.get('file_url')
    order.seller_message = data.get('message', '')
    
    # Get gig details for verification
    gig = Gig.query.get(order.gig_id)
    
    # Prepare data for AI verification
    from ai_verification import ai_verification
    
    delivery_data = {
        'file_url': data.get('file_url'),
        'file_type': data.get('file_type', 'video'),
        'delivery_notes': data.get('message', ''),
        'gig_requirements': gig.description,
        'expected_quality': 'professional',
        'delivery_time': (datetime.utcnow() - order.created_at).days,
        'promised_time': gig.delivery_days
    }
    
    # AI verification
    verification_result = ai_verification.verify_delivery(delivery_data)
    
    # Save verification result
    verification = DeliveryVerification(
        order_id=order.id,
        verification_status='approved' if verification_result['approved'] else 'pending',
        quality_score=verification_result['quality_score'],
        ai_confidence=verification_result['confidence'],
        ai_analysis=verification_result['analysis'],
        issues_found=json.dumps(verification_result['issues']),
        auto_approved=verification_result['auto_release_payment'],
        verified_at=datetime.utcnow()
    )
    
    db.session.add(verification)
    
    # Auto-release payment if AI approves
    if verification_result['auto_release_payment']:
        order.status = 'completed'
        order.escrow_status = 'released'
        order.completed_at = datetime.utcnow()
        
        # Release payment to seller (85% after platform fee)
        seller = User.query.get(order.seller_id)
        seller.balance += order.amount * 0.85
        
        # Send system message
        system_msg = Message(
            order_id=order.id,
            sender_id=user_id,
            content=f"✅ Delivery automatically verified by AI! Quality Score: {verification_result['quality_score']}/10. Payment released to seller.",
            message_type='system'
        )
        db.session.add(system_msg)
    else:
        # Requires manual buyer confirmation
        system_msg = Message(
            order_id=order.id,
            sender_id=user_id,
            content=f"📋 Delivery submitted for buyer review. Quality Score: {verification_result['quality_score']}/10. Awaiting buyer confirmation.",
            message_type='system'
        )
        db.session.add(system_msg)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Delivery submitted successfully',
        'verification': {
            'approved': verification_result['approved'],
            'quality_score': verification_result['quality_score'],
            'confidence': verification_result['confidence'],
            'analysis': verification_result['analysis'],
            'auto_released': verification_result['auto_release_payment']
        },
        'order_status': order.status
    })

@app.route('/api/orders/<int:order_id>/verification', methods=['GET'])
@jwt_required()
def get_delivery_verification(order_id):
    """Get AI verification details for an order"""
    user_id = get_jwt_identity()
    order = Order.query.get_or_404(order_id)
    
    if order.buyer_id != user_id and order.seller_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    verification = DeliveryVerification.query.filter_by(order_id=order_id).first()
    
    if not verification:
        return jsonify({'error': 'No verification found'}), 404
    
    return jsonify({
        'verification_status': verification.verification_status,
        'quality_score': verification.quality_score,
        'ai_confidence': verification.ai_confidence,
        'ai_analysis': verification.ai_analysis,
        'issues_found': json.loads(verification.issues_found) if verification.issues_found else [],
        'auto_approved': verification.auto_approved,
        'verified_at': verification.verified_at.isoformat() if verification.verified_at else None
    })

@app.route('/api/orders/<int:order_id>/request-revision', methods=['POST'])
@jwt_required()
def request_revision(order_id):
    """Buyer requests revision after AI verification"""
    user_id = get_jwt_identity()
    order = Order.query.get_or_404(order_id)
    
    if order.buyer_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    
    # Add revision request message
    msg = Message(
        order_id=order.id,
        sender_id=user_id,
        content=f"🔄 Revision requested: {data.get('reason', 'No reason provided')}",
        message_type='system'
    )
    
    db.session.add(msg)
    order.status = 'in_progress'
    
    db.session.commit()
    
    return jsonify({'message': 'Revision requested successfully'})


# ==================== SELLER WALLET SYSTEM ====================

@app.route('/api/wallet/balance', methods=['GET'])
@jwt_required()
def get_wallet_balance():
    """Get seller's wallet balance and earnings breakdown"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user.is_seller:
        return jsonify({'error': 'Only sellers have wallets'}), 403
    
    # Calculate earnings breakdown
    completed_orders = Order.query.filter_by(
        seller_id=user_id,
        status='completed',
        escrow_status='released'
    ).all()
    
    total_earned = sum(o.amount * 0.85 for o in completed_orders)  # After 15% fee
    
    # Pending earnings (orders in progress)
    pending_orders = Order.query.filter_by(
        seller_id=user_id,
        status='in_progress',
        escrow_status='held'
    ).all()
    
    pending_earnings = sum(o.amount * 0.85 for o in pending_orders)
    
    # Withdrawn amount
    completed_withdrawals = Withdrawal.query.filter_by(
        user_id=user_id,
        status='completed'
    ).all()
    
    total_withdrawn = sum(w.amount for w in completed_withdrawals)
    
    # Pending withdrawals
    pending_withdrawals = Withdrawal.query.filter_by(
        user_id=user_id,
        status='pending'
    ).all()
    
    pending_withdrawal_amount = sum(w.amount for w in pending_withdrawals)
    
    return jsonify({
        'available_balance': user.balance,
        'total_earned': total_earned,
        'pending_earnings': pending_earnings,
        'total_withdrawn': total_withdrawn,
        'pending_withdrawals': pending_withdrawal_amount,
        'total_orders': len(completed_orders),
        'currency': 'INR'
    })

@app.route('/api/wallet/transactions', methods=['GET'])
@jwt_required()
def get_wallet_transactions():
    """Get all wallet transactions for seller"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user.is_seller:
        return jsonify({'error': 'Only sellers have wallets'}), 403
    
    # Get all completed orders (earnings)
    orders = Order.query.filter_by(
        seller_id=user_id,
        status='completed',
        escrow_status='released'
    ).order_by(Order.completed_at.desc()).all()
    
    earnings = [{
        'id': o.id,
        'type': 'earning',
        'amount': o.amount * 0.85,
        'gross_amount': o.amount,
        'platform_fee': o.amount * 0.15,
        'description': f"Payment for: {Gig.query.get(o.gig_id).title}",
        'buyer': User.query.get(o.buyer_id).username,
        'date': o.completed_at.isoformat() if o.completed_at else None,
        'status': 'completed'
    } for o in orders]
    
    # Get all withdrawals
    withdrawals = Withdrawal.query.filter_by(
        user_id=user_id
    ).order_by(Withdrawal.created_at.desc()).all()
    
    withdrawal_transactions = [{
        'id': w.id,
        'type': 'withdrawal',
        'amount': -w.amount,  # Negative for withdrawals
        'description': f"Withdrawal to {w.method.upper()}",
        'method': w.method,
        'date': w.created_at.isoformat(),
        'status': w.status,
        'processed_at': w.processed_at.isoformat() if w.processed_at else None
    } for w in withdrawals]
    
    # Combine and sort by date
    all_transactions = earnings + withdrawal_transactions
    all_transactions.sort(key=lambda x: x['date'], reverse=True)
    
    return jsonify({
        'transactions': all_transactions,
        'total_count': len(all_transactions)
    })

@app.route('/api/wallet/earnings-stats', methods=['GET'])
@jwt_required()
def get_earnings_stats():
    """Get earnings statistics for seller"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user.is_seller:
        return jsonify({'error': 'Only sellers have wallets'}), 403
    
    from datetime import timedelta
    
    # This month's earnings
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_orders = Order.query.filter(
        Order.seller_id == user_id,
        Order.status == 'completed',
        Order.completed_at >= month_start
    ).all()
    
    month_earnings = sum(o.amount * 0.85 for o in month_orders)
    
    # Last 7 days
    week_start = datetime.utcnow() - timedelta(days=7)
    week_orders = Order.query.filter(
        Order.seller_id == user_id,
        Order.status == 'completed',
        Order.completed_at >= week_start
    ).all()
    
    week_earnings = sum(o.amount * 0.85 for o in week_orders)
    
    # Average order value
    all_orders = Order.query.filter_by(
        seller_id=user_id,
        status='completed'
    ).all()
    
    avg_order_value = (sum(o.amount for o in all_orders) / len(all_orders)) if all_orders else 0
    
    return jsonify({
        'this_month': month_earnings,
        'last_7_days': week_earnings,
        'average_order_value': avg_order_value,
        'total_orders': len(all_orders),
        'currency': 'INR'
    })

@app.route('/api/wallet/withdraw-methods', methods=['GET'])
@jwt_required()
def get_withdrawal_methods():
    """Get available withdrawal methods"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    return jsonify({
        'methods': [
            {
                'id': 'upi',
                'name': 'UPI',
                'description': 'Instant transfer to your UPI ID',
                'processing_time': 'Instant',
                'min_amount': 100,
                'max_amount': 100000,
                'fee': 0,
                'available': True,
                'saved_details': {
                    'upi_id': user.upi_id if user.upi_id else None
                }
            },
            {
                'id': 'bank_transfer',
                'name': 'Bank Transfer',
                'description': 'Direct transfer to your bank account',
                'processing_time': '1-3 business days',
                'min_amount': 500,
                'max_amount': 500000,
                'fee': 0,
                'available': True,
                'saved_details': {
                    'account_number': user.bank_account if user.bank_account else None
                }
            }
        ]
    })

@app.route('/api/wallet/save-payment-method', methods=['POST'])
@jwt_required()
def save_payment_method():
    """Save UPI ID or bank details for withdrawals"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.json
    
    if data.get('method') == 'upi':
        user.upi_id = data.get('upi_id')
    elif data.get('method') == 'bank_transfer':
        user.bank_account = json.dumps({
            'account_number': data.get('account_number'),
            'ifsc_code': data.get('ifsc_code'),
            'account_holder': data.get('account_holder'),
            'bank_name': data.get('bank_name')
        })
    
    db.session.commit()
    
    return jsonify({'message': 'Payment method saved successfully'})

# ==================== EMAIL NOTIFICATIONS ====================

from email_service import init_email_service

# Initialize email service
email_service = init_email_service(app)

# Update order creation to send email
@app.route('/api/orders/create-with-notification', methods=['POST'])
@jwt_required()
def create_order_with_notification():
    buyer_id = get_jwt_identity()
    data = request.json
    
    gig = Gig.query.get_or_404(data['gig_id'])
    
    if gig.seller_id == buyer_id:
        return jsonify({'error': 'Cannot order your own gig'}), 400
    
    order = Order(
        buyer_id=buyer_id,
        seller_id=gig.seller_id,
        gig_id=gig.id,
        amount=gig.price,
        buyer_message=data.get('message', '')
    )
    
    db.session.add(order)
    db.session.commit()
    
    # Send email notification to seller
    seller = User.query.get(gig.seller_id)
    buyer = User.query.get(buyer_id)
    
    email_service.send_order_notification_to_seller(
        seller_email=seller.email,
        seller_name=seller.full_name or seller.username,
        order_data={
            'order_id': order.id,
            'gig_title': gig.title,
            'buyer_name': buyer.username,
            'amount': order.amount,
            'delivery_days': gig.delivery_days,
            'buyer_message': data.get('message', '')
        }
    )
    
    return jsonify({
        'order_id': order.id,
        'amount': order.amount,
        'message': 'Order created, seller notified via email'
    }), 201
