import os
from datetime import date
from pathlib import Path
from urllib.parse import quote

from flask import Flask, g
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    """
    Flask application factory.

    - Uses Flask-SQLAlchemy for persistence (SQLite by default, PostgreSQL via DATABASE_URL).
    - Uses Flask-Login for admin authentication.
    - Uses a lightweight session-based localization layer (AR/EN/KU with RTL/LTR support).
    """
    app = Flask(__name__, instance_relative_config=True)

    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)

    app.config.from_object("app.config.DefaultConfig")
    app.config.from_mapping(
        # For production: set SECRET_KEY in the environment so admin sessions stay valid across restarts.
        SECRET_KEY=os.environ.get("SECRET_KEY") or os.urandom(32),
        # For PostgreSQL: set DATABASE_URL=postgresql+psycopg://...
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL")
        or f"sqlite:///{(instance_path / 'al_salat.db').as_posix()}",
    )

    uploads_dir = Path("/tmp/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    (uploads_dir / "packages").mkdir(parents=True, exist_ok=True)

    app.config["UPLOAD_FOLDER"] = str(uploads_dir)
    app.config["ALLOWED_IMAGE_EXTENSIONS"] = {"png", "jpg", "jpeg", "svg", "webp"}

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"

    from app.i18n import inject_i18n

    inject_i18n(app)

    @app.context_processor
    def _inject_social_links():
        from app.i18n import t
        from app.models import ContentSetting, SiteConfig, SocialSetting

        rows = SocialSetting.query.order_by(SocialSetting.key.asc()).all()
        settings = {r.key: (r.value or "").strip() for r in rows if (r.value or "").strip()}

        social_keys = {"facebook", "instagram", "telegram", "youtube", "tiktok"}
        links = {k: v for k, v in settings.items() if k in social_keys}

        locale = getattr(g, "locale", app.config.get("DEFAULT_LANG", "ar"))

        cfg = SiteConfig.query.order_by(SiteConfig.id.asc()).first()
        logo_filename = (cfg.logo_filename if cfg else "logo.png") or "logo.png"
        try:
            if logo_filename == "logo.svg" and (uploads_dir / "logo.png").exists():
                logo_filename = "logo.png"
            elif not (uploads_dir / logo_filename).exists():
                logo_filename = "logo.png" if (uploads_dir / "logo.png").exists() else "logo.svg"
        except Exception:
            logo_filename = "logo.png"
        site_name = None
        if cfg:
            site_name = getattr(cfg, f"site_name_{locale}", None)
        current_site_name = (site_name or settings.get(f"site_name_{locale}") or app.config.get("APP_NAME") or "").strip()
        if not current_site_name:
            current_site_name = app.config.get("APP_NAME", "")
        whatsapp_phone = (settings.get("whatsapp_phone") or "").strip().replace("+", "")
        whatsapp_support_url = (
            f"https://wa.me/{whatsapp_phone}?text={quote(t('whatsapp_prefill'))}"
            if whatsapp_phone
            else ""
        )

        content_rows = ContentSetting.query.order_by(ContentSetting.key.asc()).all()
        content_map = {r.key: r for r in content_rows}

        def content(key: str) -> str:
            row = content_map.get(key)
            if row:
                value = getattr(row, f"value_{locale}", "") or ""
                value = value.strip()
                if value:
                    return value
            return t(key)

        company_contact = {
            "phone": settings.get("phone", ""),
            "phone2": settings.get("phone2", ""),
            "email": settings.get("email", ""),
            "address": settings.get(f"address_{locale}") or settings.get("address", ""),
            "whatsapp_support_url": whatsapp_support_url,
        }

        return {
            "social_links": links,
            "current_logo_filename": logo_filename,
            "current_site_name": current_site_name,
            "whatsapp_support_url": whatsapp_support_url,
            "company_contact": company_contact,
            "content": content,
            "current_year": date.today().year,
        }

    from app.public_routes import public_bp
    from app.admin_routes import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    with app.app_context():
        from app import models  # noqa: F401

        db.create_all()
        # Seed a few starter packages so the site is usable immediately.
        from app.seed import seed_packages_if_empty, seed_site_config_if_missing

        seed_packages_if_empty()
        seed_site_config_if_missing()

        from app.models import Booking

        legacy_map = {"Pending": "pending", "Approved": "approved", "Cancelled": "rejected"}
        legacy_bookings = Booking.query.filter(Booking.status.in_(list(legacy_map.keys()))).all()
        for b in legacy_bookings:
            b.status = legacy_map.get(b.status, "pending")
        if legacy_bookings:
            db.session.commit()

        uri = (app.config.get("SQLALCHEMY_DATABASE_URI") or "").lower()
        if uri.startswith("sqlite"):
            from sqlalchemy import text

            pkg_cols = db.session.execute(text("PRAGMA table_info(packages)")).all()
            if pkg_cols and not any((row[1] == "image_filename") for row in pkg_cols):
                db.session.execute(
                    text(
                        "ALTER TABLE packages ADD COLUMN image_filename VARCHAR(255) NOT NULL DEFAULT ''"
                    )
                )
                db.session.commit()

            cfg_cols = db.session.execute(text("PRAGMA table_info(site_config)")).all()
            if cfg_cols and not any((row[1] == "hero_bg_filename") for row in cfg_cols):
                db.session.execute(
                    text(
                        "ALTER TABLE site_config ADD COLUMN hero_bg_filename VARCHAR(255) NOT NULL DEFAULT 'hero_default.svg'"
                    )
                )
                db.session.commit()
            if cfg_cols and not any((row[1] == "site_name_ar") for row in cfg_cols):
                db.session.execute(
                    text(
                        "ALTER TABLE site_config ADD COLUMN site_name_ar VARCHAR(255) NOT NULL DEFAULT 'الصلاة المحمدية والصلاة الإبراهيمية'"
                    )
                )
                db.session.execute(
                    text(
                        "ALTER TABLE site_config ADD COLUMN site_name_en VARCHAR(255) NOT NULL DEFAULT 'Al-Salat Al-Muhammadiya & Al-Salat Al-Ibrahimiya'"
                    )
                )
                db.session.execute(
                    text(
                        "ALTER TABLE site_config ADD COLUMN site_name_ku VARCHAR(255) NOT NULL DEFAULT 'الصلاة المحمدية والصلاة الإبراهيمية'"
                    )
                )
                db.session.commit()

    return app
