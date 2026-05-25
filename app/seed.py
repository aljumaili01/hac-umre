from app import db
from app.models import Package, SiteConfig


def seed_packages_if_empty():
    if db.session.query(Package.id).first():
        return

    packages = [
        Package(
            slug="vip-umrah",
            title_en="VIP Umrah",
            title_ar="عمرة VIP",
            title_ku="عومرە VIP",
            description_en="Premium hotels near the Haram, private transport, and guided support.",
            description_ar="فنادق فاخرة قرب الحرم، نقل خاص، ومرافقة وإرشاد.",
            description_ku="هۆتێلی باش لە نزیک حەرەم، گواستنەوەی تایبەت، و ڕێنمایی.",
            price_per_person=2600,
            currency="USD",
            duration_days=10,
            hotels="Makkah: 5★ / Madinah: 5★",
            inclusions="Flights • Visa • Hotels • Transport • Guide",
            is_active=True,
        ),
        Package(
            slug="economic-umrah",
            title_en="Economic Umrah",
            title_ar="عمرة اقتصادية",
            title_ku="عومرە ئابووری",
            description_en="Affordable plan with comfortable hotels and reliable group transport.",
            description_ar="خطة مناسبة مع فنادق مريحة وتنقل جماعي منظم.",
            description_ku="پلانی گونجاو بە هۆتێلی ئارام و گواستنەوەی گروپی.",
            price_per_person=1350,
            currency="USD",
            duration_days=8,
            hotels="Makkah: 3★ / Madinah: 3★",
            inclusions="Visa • Hotels • Transport • Coordinator",
            is_active=True,
        ),
        Package(
            slug="ramadan-umrah",
            title_en="Ramadan Umrah",
            title_ar="عمرة رمضان",
            title_ku="عومرەی ڕەمەزان",
            description_en="Spiritual Ramadan experience with curated schedules and close hotels.",
            description_ar="تجربة رمضانية روحانية مع برنامج منظم وفنادق قريبة.",
            description_ku="ئەزموونی ڕوحیی ڕەمەزان بە پلانی ڕێکخراو و هۆتێلی نزیک.",
            price_per_person=1950,
            currency="USD",
            duration_days=12,
            hotels="Makkah: 4★ / Madinah: 4★",
            inclusions="Visa • Hotels • Transport • Iftar/Suhoor options",
            is_active=True,
        ),
        Package(
            slug="hajj-standard",
            title_en="Hajj (Standard)",
            title_ar="الحج (قياسي)",
            title_ku="حەج (ستاندارد)",
            description_en="Complete Hajj services including Mina/Arafat arrangements and guidance.",
            description_ar="خدمات حج متكاملة تشمل ترتيبات منى وعرفات وإرشاد.",
            description_ku="خزمەتگوزاری حەجی تەواو لەگەڵ ڕێکخستنی منى و عەرفات و ڕێنمایی.",
            price_per_person=5400,
            currency="USD",
            duration_days=18,
            hotels="Makkah: 4★ / Madinah: 4★",
            inclusions="Visa • Hotels • Transport • Mina/Arafat • Guide",
            is_active=True,
        ),
    ]

    db.session.add_all(packages)
    db.session.commit()


def seed_site_config_if_missing():
    if db.session.query(SiteConfig.id).first():
        return
    cfg = SiteConfig(
        logo_filename="logo.png",
        hero_bg_filename="hero_default.svg",
        site_name_ar="الصلاة المحمدية والصلاة الإبراهيمية",
        site_name_en="Al-Salat Al-Muhammadiya & Al-Salat Al-Ibrahimiya",
        site_name_ku="الصلاة المحمدية والصلاة الإبراهيمية",
    )
    db.session.add(cfg)
    db.session.commit()
