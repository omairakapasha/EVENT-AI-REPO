"""
Idempotent seed script for Event-AI backend.

Usage (from packages/backend/):
    uv run python -m src.scripts.seed

Creates:
  - Admin user (from SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD env vars)
  - Demo pro user account
  - Default categories + event types
  - 5 demo vendor accounts with services (Lahore + Karachi)
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config.database import get_settings
from src.models.user import User, SubscriptionStatus
from src.models.category import Category, VendorCategoryLink
from src.models.event import EventType
from src.models.vendor import Vendor, VendorStatus
from src.models.service import Service
from src.models.booking import Booking, BookingStatus, PaymentStatus
from src.services.auth_service import AuthService

# Import all models so SQLAlchemy can resolve relationships
import src.models.vendor  # noqa: F401
import src.models.service  # noqa: F401
import src.models.booking  # noqa: F401
import src.models.availability  # noqa: F401
import src.models.inquiry  # noqa: F401
import src.models.approval  # noqa: F401

log = structlog.get_logger()

DEFAULT_CATEGORIES = [
    {"name": "Wedding",    "display_order": 1},
    {"name": "Mehndi",     "display_order": 2},
    {"name": "Baraat",     "display_order": 3},
    {"name": "Walima",     "display_order": 4},
    {"name": "Corporate",  "display_order": 5},
    {"name": "Conference", "display_order": 6},
    {"name": "Birthday",   "display_order": 7},
    {"name": "Party",      "display_order": 8},
]

DEFAULT_EVENT_TYPES = [
    {"name": "Wedding",        "description": "Nikah, baraat, walima ceremonies",          "display_order": 1},
    {"name": "Mehndi",         "description": "Mehndi/henna ceremony",                     "display_order": 2},
    {"name": "Birthday Party", "description": "Birthday celebrations",                     "display_order": 3},
    {"name": "Corporate",      "description": "Business meetings, conferences, team events","display_order": 4},
    {"name": "Conference",     "description": "Large-scale conferences and seminars",       "display_order": 5},
    {"name": "Party",          "description": "General parties and social gatherings",      "display_order": 6},
    {"name": "Baraat",         "description": "Wedding procession ceremony",                "display_order": 7},
    {"name": "Walima",         "description": "Wedding reception ceremony",                 "display_order": 8},
]


def _validate_settings(settings) -> None:
    """Validate required seed env vars before touching the DB."""
    if not settings.seed_admin_email:
        log.error("seed.error", message="SEED_ADMIN_EMAIL env var is not set")
        sys.exit(1)
    if not settings.seed_admin_password:
        log.error("seed.error", message="SEED_ADMIN_PASSWORD env var is not set")
        sys.exit(1)
    if len(settings.seed_admin_password) < 12:
        log.error(
            "seed.error",
            message="SEED_ADMIN_PASSWORD must be at least 12 characters",
        )
        sys.exit(1)


async def seed_admin(session: AsyncSession, email: str, password: str) -> bool:
    """Create admin user if not exists. Returns True if created, False if skipped."""
    result = await session.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()

    if existing:
        log.info("seed.admin.skipped", email=email, reason="already exists")
        return False

    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=AuthService.hash_password(password),
        first_name="Admin",
        last_name="User",
        role="admin",
        is_active=True,
        email_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(user)
    await session.flush()
    log.info("seed.admin.created", email=email, user_id=str(user.id))
    return True


DEMO_EMAIL = "demo@eventai.pk"
DEMO_PASSWORD = "Demo@EventAI2026!"


async def seed_demo_pro_account(session: AsyncSession) -> bool:
    """Create demo pro user if not exists. Returns True if created."""
    result = await session.execute(select(User).where(User.email == DEMO_EMAIL))
    existing = result.scalar_one_or_none()

    if existing:
        if existing.subscription_status != SubscriptionStatus.pro:
            existing.subscription_status = SubscriptionStatus.pro
            existing.subscription_expires_at = None
            existing.updated_at = datetime.now(timezone.utc)
            log.info("seed.demo.upgraded_to_pro", email=DEMO_EMAIL)
        else:
            log.info("seed.demo.skipped", email=DEMO_EMAIL, reason="already exists with pro")
        return False

    user = User(
        id=uuid.uuid4(),
        email=DEMO_EMAIL,
        password_hash=AuthService.hash_password(DEMO_PASSWORD),
        first_name="Demo",
        last_name="User",
        role="user",
        is_active=True,
        email_verified=True,
        subscription_status=SubscriptionStatus.pro,
        subscription_expires_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(user)
    await session.flush()
    log.info("seed.demo.created", email=DEMO_EMAIL, user_id=str(user.id))
    return True


async def seed_event_types(session: AsyncSession) -> dict:
    """Create default event types if not exists. Returns counts."""
    created = 0
    skipped = 0

    for et_data in DEFAULT_EVENT_TYPES:
        result = await session.execute(
            select(EventType).where(EventType.name == et_data["name"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            log.info("seed.event_type.skipped", name=et_data["name"], reason="already exists")
            skipped += 1
            continue

        event_type = EventType(
            id=uuid.uuid4(),
            name=et_data["name"],
            description=et_data["description"],
            display_order=et_data["display_order"],
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(event_type)
        await session.flush()
        log.info("seed.event_type.created", name=et_data["name"])
        created += 1

    return {"created": created, "skipped": skipped}


async def seed_categories(session: AsyncSession) -> dict:
    """Create default categories if not exists. Returns counts."""
    created = 0
    skipped = 0

    for cat_data in DEFAULT_CATEGORIES:
        result = await session.execute(
            select(Category).where(Category.name == cat_data["name"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            log.info("seed.category.skipped", name=cat_data["name"], reason="already exists")
            skipped += 1
            continue

        category = Category(
            id=uuid.uuid4(),
            name=cat_data["name"],
            display_order=cat_data["display_order"],
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(category)
        await session.flush()
        log.info("seed.category.created", name=cat_data["name"])
        created += 1

    return {"created": created, "skipped": skipped}


DEMO_VENDOR_EMAIL = "bookings@royalphotolahore.pk"
DEMO_VENDOR_PASSWORD = "Vendor@Demo2026!"

DEMO_VENDORS = [
    {
        "email": "catering@lahoribiryani.pk",
        "password": "Vendor@Demo2026!",
        "first_name": "Khalid",
        "last_name": "Mirza",
        "business_name": "Lahori Biryani House",
        "description": "Authentic catering for weddings and corporate events. Specialising in traditional Lahori cuisine, live counter setups, and bulk orders across Punjab.",
        "contact_phone": "+92-300-1234567",
        "city": "Lahore",
        "region": "Punjab",
        "rating": 4.7,
        "total_reviews": 83,
        "category": "Wedding",
        "services": [
            {
                "name": "Wedding Catering Package (300 guests)",
                "description": "Full wedding catering — Nihari, Biryani, BBQ, desserts, drinks. Includes live counter staff.",
                "price_min": 450000,
                "price_max": 650000,
                "capacity": 300,
            },
            {
                "name": "Corporate Lunch Setup",
                "description": "Buffet-style corporate lunch for offices and conferences. 3-course meal with setup and cleanup.",
                "price_min": 80000,
                "price_max": 150000,
                "capacity": 100,
            },
            {
                "name": "Mehndi & Walima Catering",
                "description": "Traditional mehndi food spread including chaat, tikkas, and desserts. Per-head pricing available.",
                "price_min": 250000,
                "price_max": 400000,
                "capacity": 200,
            },
        ],
    },
    {
        "email": "bookings@royalphotolahore.pk",
        "password": "Vendor@Demo2026!",
        "first_name": "Ayesha",
        "last_name": "Qureshi",
        "business_name": "Royal Photography & Videography",
        "description": "Award-winning photography and cinematic videography studio based in Lahore. Specialising in weddings, pre-wedding shoots, and event coverage.",
        "contact_phone": "+92-321-9876543",
        "city": "Lahore",
        "region": "Punjab",
        "rating": 4.9,
        "total_reviews": 142,
        "category": "Wedding",
        "services": [
            {
                "name": "Full Wedding Photography & Cinematic Film",
                "description": "Two photographers + one videographer. Complete event coverage: Mehndi, Baraat, Valima. 4K cinematic edit delivered in 3 weeks.",
                "price_min": 180000,
                "price_max": 350000,
                "capacity": None,
            },
            {
                "name": "Pre-Wedding / Engagement Shoot",
                "description": "4-hour outdoor session, 60 edited high-res photos, one location of your choice.",
                "price_min": 35000,
                "price_max": 60000,
                "capacity": None,
            },
            {
                "name": "Corporate Event Photography",
                "description": "Half-day (4 hrs) or full-day (8 hrs) coverage. 100+ edited photos delivered in 48 hours.",
                "price_min": 25000,
                "price_max": 50000,
                "capacity": None,
            },
        ],
    },
    {
        "email": "events@grandmarquee.pk",
        "password": "Vendor@Demo2026!",
        "first_name": "Imran",
        "last_name": "Sheikh",
        "business_name": "The Grand Marquee",
        "description": "Premium banquet and marquee venue in DHA Lahore. Air-conditioned halls for 200–800 guests, dedicated event coordinator, ample parking.",
        "contact_phone": "+92-42-35123456",
        "city": "Lahore",
        "region": "Punjab",
        "rating": 4.5,
        "total_reviews": 61,
        "category": "Wedding",
        "services": [
            {
                "name": "Main Hall (600 guests)",
                "description": "Grand air-conditioned hall, stage setup, basic lighting, parking for 150 cars. Catering partner available.",
                "price_min": 600000,
                "price_max": 900000,
                "capacity": 600,
            },
            {
                "name": "Garden Marquee (200 guests)",
                "description": "Outdoor garden marquee with fairy lights, seating for 200, lawn access. Ideal for Mehndi and Walima.",
                "price_min": 200000,
                "price_max": 350000,
                "capacity": 200,
            },
            {
                "name": "Corporate Conference Room (50 pax)",
                "description": "Fully equipped conference room — projector, WiFi, whiteboard, tea/coffee service.",
                "price_min": 30000,
                "price_max": 60000,
                "capacity": 50,
            },
        ],
    },
    {
        "email": "hello@floraldreamskarachi.pk",
        "password": "Vendor@Demo2026!",
        "first_name": "Sana",
        "last_name": "Farooq",
        "business_name": "Floral Dreams Decoration",
        "description": "Karachi's most sought-after wedding and event decoration studio. From floral arches to complete stage setups — we bring your vision to life.",
        "contact_phone": "+92-333-5551234",
        "city": "Karachi",
        "region": "Sindh",
        "rating": 4.8,
        "total_reviews": 97,
        "category": "Wedding",
        "services": [
            {
                "name": "Full Wedding Stage & Décor Package",
                "description": "Complete stage design, floral backdrop, table centrepieces, aisle décor, and fairy light canopy. Setup & teardown included.",
                "price_min": 250000,
                "price_max": 500000,
                "capacity": None,
            },
            {
                "name": "Mehndi Décor Setup",
                "description": "Colourful tent, flower strings, cushion seating area, photobooth backdrop. Full Mehndi vibe guaranteed.",
                "price_min": 80000,
                "price_max": 150000,
                "capacity": None,
            },
            {
                "name": "Birthday Party Decoration",
                "description": "Balloon arches, themed table settings, photo corner, customised backdrop. Setup for home or hall.",
                "price_min": 20000,
                "price_max": 50000,
                "capacity": None,
            },
        ],
    },
    {
        "email": "info@soundwaveskarachi.pk",
        "password": "Vendor@Demo2026!",
        "first_name": "Usman",
        "last_name": "Tariq",
        "business_name": "Sound Waves Entertainment",
        "description": "Professional sound, lighting, and DJ services for weddings, corporate galas, and concerts across Karachi. State-of-the-art JBL & Martin audio equipment.",
        "contact_phone": "+92-312-7778889",
        "city": "Karachi",
        "region": "Sindh",
        "rating": 4.6,
        "total_reviews": 54,
        "category": "Corporate",
        "services": [
            {
                "name": "Wedding Sound & Lighting Package",
                "description": "Premium sound system (JBL line array), uplighting, truss + moving head lights, fog machine. DJ optional.",
                "price_min": 120000,
                "price_max": 250000,
                "capacity": 500,
            },
            {
                "name": "Corporate Event AV Setup",
                "description": "PA system, stage monitors, laser lighting, LED backdrop. Includes sound engineer for full event.",
                "price_min": 60000,
                "price_max": 120000,
                "capacity": 300,
            },
            {
                "name": "DJ Night / Private Party",
                "description": "Professional DJ + sound + coloured lighting for 4 hours. Playlist coordination included.",
                "price_min": 40000,
                "price_max": 80000,
                "capacity": 150,
            },
        ],
    },
]


async def seed_demo_vendors(session: AsyncSession) -> dict:
    """Create demo vendor accounts with services if not exists."""
    created = 0
    skipped = 0

    for v_data in DEMO_VENDORS:
        result = await session.execute(select(User).where(User.email == v_data["email"]))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            log.info("seed.vendor.skipped", email=v_data["email"], reason="already exists")
            skipped += 1
            continue

        # Vendor user account
        user = User(
            id=uuid.uuid4(),
            email=v_data["email"],
            password_hash=AuthService.hash_password(v_data["password"]),
            first_name=v_data["first_name"],
            last_name=v_data["last_name"],
            role="vendor",
            is_active=True,
            email_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(user)
        await session.flush()

        # Vendor profile
        vendor = Vendor(
            id=uuid.uuid4(),
            user_id=user.id,
            business_name=v_data["business_name"],
            description=v_data["description"],
            contact_email=v_data["email"],
            contact_phone=v_data["contact_phone"],
            city=v_data["city"],
            region=v_data["region"],
            status=VendorStatus.ACTIVE,
            rating=v_data["rating"],
            total_reviews=v_data["total_reviews"],
        )
        session.add(vendor)
        await session.flush()

        # Link category
        cat_result = await session.execute(
            select(Category).where(Category.name == v_data["category"])
        )
        category = cat_result.scalar_one_or_none()
        if category:
            session.add(VendorCategoryLink(vendor_id=vendor.id, category_id=category.id))
            await session.flush()

        # Services
        for svc_data in v_data["services"]:
            service = Service(
                id=uuid.uuid4(),
                vendor_id=vendor.id,
                name=svc_data["name"],
                description=svc_data["description"],
                price_min=svc_data["price_min"],
                price_max=svc_data["price_max"],
                capacity=svc_data.get("capacity"),
                is_active=True,
            )
            session.add(service)

        await session.flush()
        log.info(
            "seed.vendor.created",
            email=v_data["email"],
            business=v_data["business_name"],
            services=len(v_data["services"]),
        )
        created += 1

    return {"created": created, "skipped": skipped}


async def seed_demo_bookings(session: AsyncSession) -> dict:
    """Seed 3 pending bookings from demo user → demo vendor for showcase."""
    from datetime import date
    from sqlalchemy import func

    user_res = await session.execute(select(User).where(User.email == DEMO_EMAIL))
    demo_user = user_res.scalar_one_or_none()
    if not demo_user:
        log.info("seed.bookings.skipped", reason="demo user not found")
        return {"created": 0, "skipped": 0}

    vendor_user_res = await session.execute(select(User).where(User.email == DEMO_VENDOR_EMAIL))
    vendor_user = vendor_user_res.scalar_one_or_none()
    if not vendor_user:
        log.info("seed.bookings.skipped", reason="demo vendor user not found")
        return {"created": 0, "skipped": 0}

    vendor_res = await session.execute(select(Vendor).where(Vendor.user_id == vendor_user.id))
    vendor = vendor_res.scalar_one_or_none()
    if not vendor:
        log.info("seed.bookings.skipped", reason="demo vendor profile not found")
        return {"created": 0, "skipped": 0}

    existing_count = await session.execute(
        select(func.count()).select_from(Booking).where(
            Booking.vendor_id == vendor.id,
            Booking.user_id == demo_user.id,
        )
    )
    if existing_count.scalar() > 0:
        log.info("seed.bookings.skipped", reason="already seeded")
        return {"created": 0, "skipped": 3}

    services_res = await session.execute(
        select(Service).where(Service.vendor_id == vendor.id, Service.is_active == True)
    )
    services = services_res.scalars().all()
    if not services:
        log.info("seed.bookings.skipped", reason="no services found for demo vendor")
        return {"created": 0, "skipped": 0}

    DEMO_BOOKINGS = [
        {
            "service_idx": 0,
            "event_name": "Ahmed & Sara Wedding — Full Coverage",
            "event_date": date(2026, 8, 20),
            "client_name": "Ahmed Raza",
            "client_email": "ahmed.raza@gmail.com",
            "client_phone": "+92-311-1234567",
            "guest_count": None,
            "special_requirements": "Full day coverage — Baraat morning, Valima evening. Drone shots required.",
            "event_location": {"address": "Gulberg III", "city": "Lahore"},
        },
        {
            "service_idx": 1,
            "event_name": "Fatima & Hamza Engagement Shoot",
            "event_date": date(2026, 9, 5),
            "client_name": "Fatima Khan",
            "client_email": "fatima.k@hotmail.com",
            "client_phone": "+92-333-9876543",
            "guest_count": None,
            "special_requirements": "Outdoor garden location preferred. Sunset timing if possible.",
            "event_location": {"address": "Jilani Park", "city": "Lahore"},
        },
        {
            "service_idx": 2,
            "event_name": "TechSummit 2026 — Corporate Photography",
            "event_date": date(2026, 10, 12),
            "client_name": "Bilal Enterprises",
            "client_email": "events@bilal-ent.pk",
            "client_phone": "+92-42-35001234",
            "guest_count": 150,
            "special_requirements": "Edited photos needed within 24 hrs for press release.",
            "event_location": {"address": "Pearl Continental Hotel", "city": "Lahore"},
        },
    ]

    created = 0
    for b_data in DEMO_BOOKINGS:
        svc = services[min(b_data["service_idx"], len(services) - 1)]
        price = float(svc.price_min or 0)
        booking = Booking(
            id=uuid.uuid4(),
            user_id=demo_user.id,
            vendor_id=vendor.id,
            service_id=svc.id,
            event_name=b_data["event_name"],
            event_date=b_data["event_date"],
            event_location=b_data["event_location"],
            client_name=b_data["client_name"],
            client_email=b_data["client_email"],
            client_phone=b_data["client_phone"],
            guest_count=b_data.get("guest_count"),
            special_requirements=b_data["special_requirements"],
            status=BookingStatus.pending,
            quantity=1,
            unit_price=price,
            total_price=price,
            currency="PKR",
            payment_status=PaymentStatus.pending,
        )
        session.add(booking)
        await session.flush()
        created += 1
        log.info("seed.booking.created", event_name=b_data["event_name"])

    return {"created": created, "skipped": 0}


async def run_seed() -> None:
    settings = get_settings()
    _validate_settings(settings)

    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"ssl": "require"},
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():
            admin_created = await seed_admin(
                session,
                settings.seed_admin_email,
                settings.seed_admin_password,
            )
            demo_created = await seed_demo_pro_account(session)
            cat_counts = await seed_categories(session)
            et_counts = await seed_event_types(session)
            # Vendors must seed after categories (category FK link)
            vendor_counts = await seed_demo_vendors(session)
            # Bookings must seed after vendors + demo user
            booking_counts = await seed_demo_bookings(session)

    await engine.dispose()

    log.info(
        "seed.complete",
        admin_created=admin_created,
        demo_created=demo_created,
        categories_created=cat_counts["created"],
        categories_skipped=cat_counts["skipped"],
        event_types_created=et_counts["created"],
        event_types_skipped=et_counts["skipped"],
        vendors_created=vendor_counts["created"],
        vendors_skipped=vendor_counts["skipped"],
        bookings_created=booking_counts["created"],
        bookings_skipped=booking_counts["skipped"],
    )


if __name__ == "__main__":
    asyncio.run(run_seed())
