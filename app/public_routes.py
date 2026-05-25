from urllib.parse import quote

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from app import db
from app.i18n import RTL_LANGS, get_locale, t
from app.models import Article, Booking, Package, SocialSetting


public_bp = Blueprint("public", __name__)


@public_bp.get("/")
def home():
    locale = get_locale()
    packages = (
        Package.query.filter_by(is_active=True).order_by(Package.created_at.desc()).limit(4).all()
    )
    articles = Article.query.order_by(Article.created_at.desc()).limit(3).all()
    return render_template(
        "home.html",
        packages=packages,
        articles=articles,
        locale=locale,
        is_rtl=locale in RTL_LANGS,
    )


@public_bp.get("/packages")
def packages():
    locale = get_locale()
    packages = Package.query.filter_by(is_active=True).order_by(Package.created_at.desc()).all()
    return render_template(
        "packages.html",
        packages=packages,
        locale=locale,
        is_rtl=locale in RTL_LANGS,
    )


@public_bp.get("/booking")
def booking():
    locale = get_locale()
    packages = Package.query.filter_by(is_active=True).order_by(Package.created_at.desc()).all()
    selected_slug = request.args.get("package")
    selected = None
    if selected_slug:
        selected = Package.query.filter_by(slug=selected_slug, is_active=True).first()
    return render_template(
        "booking.html",
        packages=packages,
        selected_package=selected,
        locale=locale,
        is_rtl=locale in RTL_LANGS,
    )


@public_bp.get("/about")
def about():
    locale = get_locale()
    return render_template("about.html", locale=locale, is_rtl=locale in RTL_LANGS)


@public_bp.get("/contact")
def contact():
    locale = get_locale()
    keys = [
        "phone",
        "phone2",
        "email",
        "address",
        "address_ar",
        "address_en",
        "address_ku",
        "whatsapp_phone",
    ]
    settings = {
        s.key: s.value
        for s in SocialSetting.query.filter(SocialSetting.key.in_(keys)).all()
        if (s.value or "").strip()
    }

    whatsapp_phone = (settings.get("whatsapp_phone") or "").strip().replace("+", "")
    prefill = quote(t("whatsapp_prefill"))
    whatsapp_url = f"https://wa.me/{whatsapp_phone}?text={prefill}" if whatsapp_phone else ""

    return render_template(
        "contact.html",
        locale=locale,
        is_rtl=locale in RTL_LANGS,
        contact_settings=settings,
        contact_address=(settings.get(f"address_{locale}") or settings.get("address") or ""),
        whatsapp_url=whatsapp_url,
    )


@public_bp.get("/articles")
def articles_list():
    locale = get_locale()
    articles = Article.query.order_by(Article.created_at.desc()).all()
    return render_template(
        "articles.html",
        locale=locale,
        is_rtl=locale in RTL_LANGS,
        articles=articles,
    )


@public_bp.get("/articles/<int:article_id>")
def article_detail(article_id: int):
    locale = get_locale()
    article = db.session.get(Article, article_id)
    if not article:
        return redirect(url_for("public.articles_list"))
    return render_template(
        "article_detail.html",
        locale=locale,
        is_rtl=locale in RTL_LANGS,
        article=article,
    )


@public_bp.get("/guide")
def guide():
    locale = get_locale()
    return render_template("guide.html", locale=locale, is_rtl=locale in RTL_LANGS)


@public_bp.post("/api/set-language")
def api_set_language():
    # Persists language selection in the session; templates pick it up automatically.
    data = request.get_json(silent=True) or {}
    lang = (data.get("lang") or "").strip().lower()
    supported = set(current_app.config.get("SUPPORTED_LANGS", ("ar", "en", "ku")))
    if lang not in supported:
        return jsonify({"ok": False, "error": "Unsupported language"}), 400
    session["lang"] = lang
    return jsonify({"ok": True, "lang": lang})


@public_bp.get("/api/packages")
def api_packages():
    lang = get_locale()
    packages = Package.query.filter_by(is_active=True).order_by(Package.created_at.desc()).all()
    return jsonify(
        {
            "ok": True,
            "lang": lang,
            "packages": [
                {
                    "id": p.id,
                    "slug": p.slug,
                    "title": p.localized(lang)["title"],
                    "description": p.localized(lang)["description"],
                    "price_per_person": float(p.price_per_person),
                    "currency": p.currency,
                    "duration_days": p.duration_days,
                    "hotels": p.hotels,
                    "inclusions": p.inclusions,
                }
                for p in packages
            ],
        }
    )


@public_bp.post("/api/bookings")
def api_bookings():
    data = request.get_json(silent=True) or {}

    package_slug = (data.get("package") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    passport_number = (data.get("passport_number") or "").strip()
    phone = (data.get("phone") or "").strip()
    people_count = data.get("people_count")

    if not package_slug or not full_name or not passport_number or not phone:
        return jsonify({"ok": False, "error": "Missing required fields"}), 400

    try:
        people_count = int(people_count)
    except Exception:
        people_count = 1
    people_count = max(1, min(people_count, 50))

    package = Package.query.filter_by(slug=package_slug, is_active=True).first()
    if not package:
        return jsonify({"ok": False, "error": "Invalid package"}), 400

    lang = get_locale()
    booking = Booking(
        package_id=package.id,
        full_name=full_name,
        passport_number=passport_number,
        phone=phone,
        people_count=people_count,
        preferred_language=lang,
        status="pending",
    )
    db.session.add(booking)
    db.session.commit()

    return jsonify({"ok": True, "booking_id": booking.id})
