from pathlib import Path
from uuid import uuid4

from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from app import db
from app.i18n import t
from app.models import AdminUser, Article, Booking, ContentSetting, Package, SiteConfig, SocialSetting


admin_bp = Blueprint("admin", __name__)


def _no_admin_exists() -> bool:
    return db.session.query(AdminUser.id).first() is None


@admin_bp.route("/setup", methods=["GET", "POST"])
def setup():
    # One-time bootstrap route: enabled only when there are no admins in the DB.
    if not _no_admin_exists():
        return redirect(url_for("admin.login"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not username or len(password) < 8:
            flash("Invalid username or password too short.", "error")
            return render_template("admin/setup.html")

        admin = AdminUser(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        login_user(admin)
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/setup.html")


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if _no_admin_exists():
        return redirect(url_for("admin.setup"))
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = AdminUser.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash("Invalid credentials.", "error")
            return render_template("admin/login.html")
        login_user(user)
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/login.html")


@admin_bp.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


@admin_bp.get("/")
@login_required
def dashboard():
    total_bookings = Booking.query.count()
    pending_bookings = Booking.query.filter_by(status="pending").count()
    approved = Booking.query.filter_by(status="approved").all()
    revenue = sum(b.total_amount() for b in approved)

    latest_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
    return render_template(
        "admin/dashboard.html",
        total_bookings=total_bookings,
        pending_bookings=pending_bookings,
        revenue=revenue,
        latest_bookings=latest_bookings,
    )


@admin_bp.get("/packages")
@login_required
def packages_list():
    packages = Package.query.order_by(Package.created_at.desc()).all()
    return render_template("admin/packages_list.html", packages=packages)


@admin_bp.route("/packages/new", methods=["GET", "POST"])
@login_required
def package_new():
    if request.method == "POST":
        package = Package()
        _bind_package_from_form(package, request.form)
        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            ext = (Path(filename).suffix or "").lstrip(".").lower()
            allowed = set(current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", set()))
            if ext not in allowed:
                flash(t("invalid_image_type"), "error")
                return render_template("admin/package_form.html", package=package, mode="new")
            upload_dir = Path(current_app.config.get("UPLOAD_FOLDER")) / "packages"
            upload_dir.mkdir(parents=True, exist_ok=True)
            new_name = f"pkg_{uuid4().hex}.{ext}"
            file.save(upload_dir / new_name)
            package.image_filename = new_name
        db.session.add(package)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Could not save package (slug may already exist).", "error")
            return render_template("admin/package_form.html", package=package, mode="new")
        return redirect(url_for("admin.packages_list"))
    return render_template("admin/package_form.html", package=None, mode="new")


@admin_bp.route("/packages/<int:package_id>/edit", methods=["GET", "POST"])
@login_required
def package_edit(package_id: int):
    package = db.session.get(Package, package_id)
    if not package:
        return redirect(url_for("admin.packages_list"))
    if request.method == "POST":
        _bind_package_from_form(package, request.form)
        file = request.files.get("image")
        if file and file.filename:
            filename = secure_filename(file.filename)
            ext = (Path(filename).suffix or "").lstrip(".").lower()
            allowed = set(current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", set()))
            if ext not in allowed:
                flash(t("invalid_image_type"), "error")
                return render_template("admin/package_form.html", package=package, mode="edit")
            upload_dir = Path(current_app.config.get("UPLOAD_FOLDER")) / "packages"
            upload_dir.mkdir(parents=True, exist_ok=True)
            new_name = f"pkg_{uuid4().hex}.{ext}"
            file.save(upload_dir / new_name)
            old = (package.image_filename or "").strip()
            package.image_filename = new_name
            if old and old != new_name:
                old_path = upload_dir / old
                try:
                    if old_path.exists():
                        old_path.unlink()
                except Exception:
                    pass
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Could not save package (slug may already exist).", "error")
            return render_template("admin/package_form.html", package=package, mode="edit")
        return redirect(url_for("admin.packages_list"))
    return render_template("admin/package_form.html", package=package, mode="edit")


@admin_bp.post("/packages/<int:package_id>/delete")
@login_required
def package_delete(package_id: int):
    package = db.session.get(Package, package_id)
    if package:
        old = (package.image_filename or "").strip()
        if old:
            upload_dir = Path(current_app.config.get("UPLOAD_FOLDER")) / "packages"
            old_path = upload_dir / old
            try:
                if old_path.exists():
                    old_path.unlink()
            except Exception:
                pass
        db.session.delete(package)
        db.session.commit()
    return redirect(url_for("admin.packages_list"))


@admin_bp.get("/bookings")
@login_required
def bookings_list():
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    packages = {p.id: p for p in Package.query.all()}
    return render_template("admin/bookings_list.html", bookings=bookings, packages=packages)


@admin_bp.get("/bookings/<int:booking_id>")
@login_required
def booking_view(booking_id: int):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return redirect(url_for("admin.bookings_list"))

    return render_template("admin/booking_view.html", booking=booking)


@admin_bp.route("/bookings/<int:booking_id>/edit", methods=["GET", "POST"])
@login_required
def booking_edit(booking_id: int):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return redirect(url_for("admin.bookings_list"))

    packages = Package.query.order_by(Package.created_at.desc()).all()

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        passport_number = (request.form.get("passport_number") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        status = (request.form.get("status") or "").strip().lower()
        package_id = request.form.get("package_id")
        people_count = request.form.get("people_count")

        if not full_name or not passport_number or not phone:
            flash(t("form_required_error"), "error")
            return render_template("admin/booking_edit.html", booking=booking, packages=packages)

        if status not in {"pending", "approved", "rejected"}:
            flash(t("invalid_status"), "error")
            return render_template("admin/booking_edit.html", booking=booking, packages=packages)

        try:
            people_count = int(people_count)
        except Exception:
            people_count = booking.people_count
        people_count = max(1, min(int(people_count), 50))

        try:
            package_id = int(package_id)
        except Exception:
            package_id = booking.package_id

        package = db.session.get(Package, package_id)
        if not package:
            flash(t("invalid_package"), "error")
            return render_template("admin/booking_edit.html", booking=booking, packages=packages)

        booking.full_name = full_name
        booking.passport_number = passport_number
        booking.phone = phone
        booking.people_count = people_count
        booking.status = status
        booking.package_id = package.id

        db.session.commit()
        flash(t("booking_updated"), "success")
        return redirect(url_for("admin.booking_view", booking_id=booking.id))

    return render_template("admin/booking_edit.html", booking=booking, packages=packages)


@admin_bp.post("/bookings/<int:booking_id>/delete")
@login_required
def booking_delete(booking_id: int):
    booking = db.session.get(Booking, booking_id)
    if booking:
        db.session.delete(booking)
        db.session.commit()
        flash(t("booking_deleted"), "success")
    return redirect(url_for("admin.bookings_list"))


@admin_bp.post("/bookings/<int:booking_id>/update-status")
@login_required
def booking_update_status(booking_id: int):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash(t("not_found"), "error")
        return redirect(url_for("admin.bookings_list"))

    status = (request.form.get("status") or "").strip().lower()
    if status not in {"pending", "approved", "rejected"}:
        flash(t("invalid_status"), "error")
        return redirect(request.referrer or url_for("admin.bookings_list"))

    booking.status = status
    db.session.commit()
    flash(t("status_updated"), "success")
    return redirect(request.referrer or url_for("admin.bookings_list"))


@admin_bp.get("/articles")
@login_required
def articles_list():
    return redirect(url_for("admin.content_management"))


@admin_bp.route("/articles/new", methods=["GET", "POST"])
@login_required
def article_new():
    if request.method == "POST":
        article = Article()
        _bind_article_from_form(article, request.form)
        db.session.add(article)
        db.session.commit()
        flash(t("article_created"), "success")
        return redirect(url_for("admin.content_management"))
    return render_template("admin/article_form.html", article=None, mode="new")


@admin_bp.route("/articles/<int:article_id>/edit", methods=["GET", "POST"])
@login_required
def article_edit(article_id: int):
    article = db.session.get(Article, article_id)
    if not article:
        return redirect(url_for("admin.articles_list"))
    if request.method == "POST":
        _bind_article_from_form(article, request.form)
        db.session.commit()
        flash(t("article_updated"), "success")
        return redirect(url_for("admin.content_management"))
    return render_template("admin/article_form.html", article=article, mode="edit")


@admin_bp.post("/articles/<int:article_id>/delete")
@login_required
def article_delete(article_id: int):
    article = db.session.get(Article, article_id)
    if article:
        db.session.delete(article)
        db.session.commit()
        flash(t("article_deleted"), "success")
    return redirect(url_for("admin.content_management"))


@admin_bp.get("/settings")
@login_required
def settings():
    return redirect(url_for("admin.content_management"))


@admin_bp.route("/content", methods=["GET", "POST"])
@login_required
def content_management():
    social_keys = ["facebook", "instagram", "telegram", "youtube", "tiktok"]
    contact_keys = [
        "phone",
        "phone2",
        "email",
        "whatsapp_phone",
        "address",
        "address_ar",
        "address_en",
        "address_ku",
    ]
    all_keys = social_keys + contact_keys

    existing = {
        s.key: s.value for s in SocialSetting.query.filter(SocialSetting.key.in_(all_keys)).all()
    }

    home_keys = [
        "hero_kicker",
        "hero_title",
        "hero_subtitle",
        "hero_badge_cities",
        "hero_badge_services",
        "hero_badge_support",
        "section_featured",
        "section_articles",
        "section_testimonials",
    ]

    if request.method == "POST":
        file = request.files.get("logo")
        if file and file.filename:
            filename = secure_filename(file.filename)
            ext = (Path(filename).suffix or "").lstrip(".").lower()
            allowed = set(current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", set()))
            if ext not in allowed or ext != "png":
                flash(t("invalid_image_type"), "error")
                return redirect(url_for("admin.content_management"))

            upload_dir = Path(current_app.config.get("UPLOAD_FOLDER"))
            upload_dir.mkdir(parents=True, exist_ok=True)
            new_name = "logo.png"
            target_path = upload_dir / new_name
            file.save(target_path)

            cfg = SiteConfig.query.order_by(SiteConfig.id.asc()).first()
            if cfg is None:
                cfg = SiteConfig(logo_filename="logo.svg")
                db.session.add(cfg)
                db.session.flush()

            old = (cfg.logo_filename or "").strip()
            cfg.logo_filename = new_name

            if old and old not in {"logo.svg", new_name}:
                old_path = upload_dir / old
                try:
                    if old_path.exists():
                        old_path.unlink()
                except Exception:
                    pass

        cfg = SiteConfig.query.order_by(SiteConfig.id.asc()).first()
        if cfg is None:
            cfg = SiteConfig(
                logo_filename="logo.svg",
                hero_bg_filename="hero_default.svg",
            )
            db.session.add(cfg)
            db.session.flush()

        cfg.site_name_ar = (request.form.get("site_name_ar") or "").strip() or cfg.site_name_ar
        cfg.site_name_en = (request.form.get("site_name_en") or "").strip() or cfg.site_name_en
        cfg.site_name_ku = (request.form.get("site_name_ku") or "").strip() or cfg.site_name_ku

        for key in all_keys:
            value = (request.form.get(key) or "").strip()
            row = SocialSetting.query.filter_by(key=key).first()
            if row is None:
                row = SocialSetting(key=key, value=value)
                db.session.add(row)
            else:
                row.value = value

        for key in home_keys:
            row = ContentSetting.query.filter_by(key=key).first()
            if row is None:
                row = ContentSetting(key=key)
                db.session.add(row)
                db.session.flush()

            row.value_ar = (request.form.get(f"content__{key}__ar") or "").strip()
            row.value_en = (request.form.get(f"content__{key}__en") or "").strip()
            row.value_ku = (request.form.get(f"content__{key}__ku") or "").strip()

        db.session.commit()
        flash(t("content_updated"), "success")
        return redirect(url_for("admin.content_management"))

    cfg = SiteConfig.query.order_by(SiteConfig.id.asc()).first()
    logo_filename = (cfg.logo_filename if cfg else "logo.svg") or "logo.svg"
    site_name_ar = (cfg.site_name_ar if cfg else "") or ""
    site_name_en = (cfg.site_name_en if cfg else "") or ""
    site_name_ku = (cfg.site_name_ku if cfg else "") or ""

    content_rows = ContentSetting.query.filter(ContentSetting.key.in_(home_keys)).all()
    content_map = {r.key: r for r in content_rows}

    articles = Article.query.order_by(Article.created_at.desc()).limit(12).all()

    return render_template(
        "admin/settings.html",
        current_logo_filename=logo_filename,
        site_name_ar=site_name_ar,
        site_name_en=site_name_en,
        site_name_ku=site_name_ku,
        social_keys=social_keys,
        contact_keys=contact_keys,
        values=existing,
        home_keys=home_keys,
        content_map=content_map,
        articles=articles,
    )


def _bind_package_from_form(package: Package, form):
    package.slug = (form.get("slug") or "").strip()
    package.title_ar = (form.get("title_ar") or "").strip()
    package.title_en = (form.get("title_en") or "").strip()
    package.title_ku = (form.get("title_ku") or "").strip()
    package.description_ar = (form.get("description_ar") or "").strip()
    package.description_en = (form.get("description_en") or "").strip()
    package.description_ku = (form.get("description_ku") or "").strip()
    package.currency = (form.get("currency") or "USD").strip().upper()[:8]
    package.hotels = (form.get("hotels") or "").strip()
    package.inclusions = (form.get("inclusions") or "").strip()
    package.is_active = form.get("is_active") == "on"

    try:
        package.duration_days = max(1, int(form.get("duration_days") or 7))
    except Exception:
        package.duration_days = 7

    try:
        package.price_per_person = Decimal((form.get("price_per_person") or "0").strip())
    except (InvalidOperation, Exception):
        package.price_per_person = Decimal("0")


def _bind_article_from_form(article: Article, form):
    article.title_ar = (form.get("title_ar") or "").strip()
    article.title_en = (form.get("title_en") or "").strip()
    article.title_ku = (form.get("title_ku") or "").strip()
    article.content_ar = (form.get("content_ar") or "").strip()
    article.content_en = (form.get("content_en") or "").strip()
    article.content_ku = (form.get("content_ku") or "").strip()
    article.image_url = (form.get("image_url") or "").strip()
