from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager


class AdminUser(UserMixin, db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(AdminUser, int(user_id))


class Package(db.Model):
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)

    title_ar = db.Column(db.String(200), nullable=False)
    title_en = db.Column(db.String(200), nullable=False)
    title_ku = db.Column(db.String(200), nullable=False)

    description_ar = db.Column(db.Text, nullable=False)
    description_en = db.Column(db.Text, nullable=False)
    description_ku = db.Column(db.Text, nullable=False)

    price_per_person = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    currency = db.Column(db.String(8), nullable=False, default="USD")
    duration_days = db.Column(db.Integer, nullable=False, default=7)
    hotels = db.Column(db.String(255), nullable=False, default="")
    inclusions = db.Column(db.Text, nullable=False, default="")
    image_filename = db.Column(db.String(255), nullable=False, default="")

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    bookings = db.relationship("Booking", back_populates="package", cascade="all, delete")

    def localized(self, lang: str):
        if lang == "en":
            return {"title": self.title_en, "description": self.description_en}
        if lang == "ku":
            return {"title": self.title_ku, "description": self.description_ku}
        return {"title": self.title_ar, "description": self.description_ar}


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=False)

    full_name = db.Column(db.String(160), nullable=False)
    passport_number = db.Column(db.String(40), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    people_count = db.Column(db.Integer, nullable=False, default=1)
    preferred_language = db.Column(db.String(2), nullable=False, default="ar")

    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    package = db.relationship("Package", back_populates="bookings")

    def total_amount(self):
        return float(self.people_count) * float(self.package.price_per_person)

    @property
    def normalized_status(self) -> str:
        raw = (self.status or "").strip().lower()
        mapping = {
            "pending": "pending",
            "p": "pending",
            "wait": "pending",
            "waiting": "pending",
            "approved": "approved",
            "approve": "approved",
            "ok": "approved",
            "rejected": "rejected",
            "reject": "rejected",
            "cancelled": "rejected",
            "canceled": "rejected",
            "cancel": "rejected",
        }
        if raw in mapping:
            return mapping[raw]
        legacy = (self.status or "").strip()
        if legacy == "Pending":
            return "pending"
        if legacy == "Approved":
            return "approved"
        if legacy == "Cancelled":
            return "rejected"
        return "pending"


class Article(db.Model):
    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)

    title_ar = db.Column(db.String(240), nullable=False)
    title_en = db.Column(db.String(240), nullable=False)
    title_ku = db.Column(db.String(240), nullable=False)

    content_ar = db.Column(db.Text, nullable=False)
    content_en = db.Column(db.Text, nullable=False)
    content_ku = db.Column(db.Text, nullable=False)

    image_url = db.Column(db.String(600), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def localized(self, lang: str):
        if lang == "en":
            return {"title": self.title_en, "content": self.content_en}
        if lang == "ku":
            return {"title": self.title_ku, "content": self.content_ku}
        return {"title": self.title_ar, "content": self.content_ar}


class SocialSetting(db.Model):
    __tablename__ = "social_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False)
    value = db.Column(db.String(600), nullable=False, default="")
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class SiteConfig(db.Model):
    __tablename__ = "site_config"

    id = db.Column(db.Integer, primary_key=True)
    logo_filename = db.Column(db.String(255), nullable=False, default="logo.svg")
    hero_bg_filename = db.Column(db.String(255), nullable=False, default="hero_default.svg")
    site_name_ar = db.Column(
        db.String(255),
        nullable=False,
        default="الصلاة المحمدية والصلاة الإبراهيمية",
    )
    site_name_en = db.Column(
        db.String(255),
        nullable=False,
        default="Al-Salat Al-Muhammadiya & Al-Salat Al-Ibrahimiya",
    )
    site_name_ku = db.Column(
        db.String(255),
        nullable=False,
        default="الصلاة المحمدية والصلاة الإبراهيمية",
    )
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ContentSetting(db.Model):
    __tablename__ = "content_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)

    value_ar = db.Column(db.Text, nullable=False, default="")
    value_en = db.Column(db.Text, nullable=False, default="")
    value_ku = db.Column(db.Text, nullable=False, default="")

    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
