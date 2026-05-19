from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.admin import AdminUser
from app.models.category import Category
from app.models.enums import RecordStatus
from app.models.service import Service
from app.models.staff import Staff, StaffAvailability

ROYAL_DUTCH_SERVICES = [
    {
        "id": 1,
        "category": "Eyebrows & Eyelashes",
        "slug": "eyebrows-eyelashes",
        "services": [
            {
                "id": 101,
                "name": "Eyelash One By One",
                "slug": "eyelash-one-by-one",
                "durationMinutes": 90,
                "price": 300,
                "currency": "AED",
            },
        ],
    },
    {
        "id": 2,
        "category": "Permanent Make-Up (PMU)",
        "slug": "permanent-make-up-pmu",
        "services": [
            {
                "id": 201,
                "name": "Microblading Eyebrows",
                "slug": "microblading-eyebrows",
                "durationMinutes": None,
                "price": 650,
                "currency": "AED",
            },
            {
                "id": 202,
                "name": "Scalp Micropigmentation",
                "slug": "scalp-micropigmentation",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
            {
                "id": 203,
                "name": "Scar Coverup",
                "slug": "scar-coverup",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
        ],
    },
    {
        "id": 3,
        "category": "Candela Laser",
        "slug": "candela-laser",
        "services": [
            {
                "id": 301,
                "name": "Laser Hair Removal",
                "slug": "laser-hair-removal",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
            {
                "id": 302,
                "name": "Laser Rejuvenation",
                "slug": "laser-rejuvenation",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
        ],
    },
    {
        "id": 4,
        "category": "Men Price",
        "slug": "men-price",
        "services": [
            {
                "id": 401,
                "name": "Men Laser Treatment",
                "slug": "men-laser-treatment",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
            {
                "id": 402,
                "name": "Men Facial Treatment",
                "slug": "men-facial-treatment",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
        ],
    },
    {
        "id": 5,
        "category": "Fat Freezing Treatment",
        "slug": "fat-freezing-treatment",
        "services": [
            {
                "id": 501,
                "name": "Cryolipolysis Fat Freezing",
                "slug": "cryolipolysis-fat-freezing",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
            {
                "id": 502,
                "name": "Body Contouring & Slimming",
                "slug": "body-contouring-slimming",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
        ],
    },
    {
        "id": 6,
        "category": "Facials",
        "slug": "facials",
        "services": [
            {
                "id": 601,
                "name": "Facials Hydrafacial",
                "slug": "facials-hydrafacial",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
            {
                "id": 602,
                "name": "Facials Luxe",
                "slug": "facials-luxe",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
            {
                "id": 603,
                "name": "General Facial",
                "slug": "general-facial",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
            {
                "id": 604,
                "name": "Acne Facial",
                "slug": "acne-facial",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
            {
                "id": 605,
                "name": "BB Glow Facial",
                "slug": "bb-glow-facial",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
            {
                "id": 606,
                "name": "Chemical Peeling",
                "slug": "chemical-peeling",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
        ],
    },
    {
        "id": 7,
        "category": "Lightenings Treatments",
        "slug": "lightenings-treatments",
        "services": [
            {
                "id": 701,
                "name": "Skin Lightening",
                "slug": "skin-lightening",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
            {
                "id": 702,
                "name": "Mesotherapy",
                "slug": "mesotherapy",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
            {
                "id": 703,
                "name": "Dermapen Microneedling",
                "slug": "dermapen-microneedling",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
        ],
    },
    {
        "id": 8,
        "category": "Piercing",
        "slug": "piercing",
        "services": [
            {
                "id": 801,
                "name": "Piercing",
                "slug": "piercing",
                "durationMinutes": None,
                "price": None,
                "currency": "AED",
            },
        ],
    },
    {
        "id": 9,
        "category": "Packages",
        "slug": "packages",
        "services": [
            {
                "id": 901,
                "name": "Paid Package Old Owner",
                "slug": "paid-package-old-owner",
                "durationMinutes": None,
                "price": 0,
                "currency": "AED",
            },
            {
                "id": 902,
                "name": "Package Price Do 3 And Get 1 Free",
                "slug": "package-price-do-3-and-get-1-free",
                "durationMinutes": None,
                "price": 1300,
                "currency": "AED",
            },
        ],
    },
]

STAFF = [
    ("Dr. Aisha", "Dermatologist", "PMU, skin treatments and consultation"),
    ("Dr. Sana", "Laser Specialist", "Candela laser and slimming treatments"),
    ("Dr. Farah", "Facial Therapist", "Facials, eyelashes and lightening treatments"),
]


def seed_admin(db: Session) -> None:
    email = "admin@clinicflow.local"
    if db.scalar(select(AdminUser).where(AdminUser.email == email)):
        return
    db.add(
        AdminUser(
            name="ClinicFlow Admin",
            email=email,
            hashed_password=hash_password("Admin@12345"),
        )
    )


def seed_categories_and_services(db: Session) -> list[Service]:
    services: list[Service] = []
    active_category_slugs = {category["slug"] for category in ROYAL_DUTCH_SERVICES}
    active_service_slugs = {
        service["slug"]
        for category in ROYAL_DUTCH_SERVICES
        for service in category["services"]
    }

    for category in db.scalars(select(Category)).all():
        if category.slug not in active_category_slugs:
            category.status = RecordStatus.inactive

    for service in db.scalars(select(Service)).all():
        if service.slug not in active_service_slugs:
            service.status = RecordStatus.inactive

    for category_data in ROYAL_DUTCH_SERVICES:
        category = db.scalar(select(Category).where(Category.slug == category_data["slug"]))
        if not category:
            category = Category(
                external_id=category_data["id"],
                name=category_data["category"],
                slug=category_data["slug"],
                description=f"{category_data['category']} clinic services",
                status=RecordStatus.active,
            )
            db.add(category)
            db.flush()
        else:
            category.external_id = category_data["id"]
            category.name = category_data["category"]
            category.status = RecordStatus.active

        for service_data in category_data["services"]:
            service = db.scalar(select(Service).where(Service.slug == service_data["slug"]))
            if not service:
                service = Service(
                    external_id=service_data["id"],
                    category_id=category.id,
                    name=service_data["name"],
                    slug=service_data["slug"],
                    description=f"{service_data['name']} appointment service",
                    duration_minutes=service_data["durationMinutes"],
                    price=service_data["price"],
                    currency=service_data["currency"],
                    status=RecordStatus.active,
                )
                db.add(service)
                db.flush()
            else:
                service.external_id = service_data["id"]
                service.category_id = category.id
                service.name = service_data["name"]
                service.duration_minutes = service_data["durationMinutes"]
                service.price = service_data["price"]
                service.currency = service_data["currency"]
                service.status = RecordStatus.active
            services.append(service)
    return services


def seed_staff(db: Session, services: list[Service]) -> None:
    all_services = {service.slug: service for service in services}
    assignments = {
        "Dr. Aisha": [
            "microblading-eyebrows",
            "scalp-micropigmentation",
            "scar-coverup",
            "chemical-peeling",
            "skin-lightening",
            "mesotherapy",
            "dermapen-microneedling",
        ],
        "Dr. Sana": [
            "laser-hair-removal",
            "laser-rejuvenation",
            "men-laser-treatment",
            "cryolipolysis-fat-freezing",
            "body-contouring-slimming",
        ],
        "Dr. Farah": [
            "eyelash-one-by-one",
            "men-facial-treatment",
            "facials-hydrafacial",
            "facials-luxe",
            "general-facial",
            "acne-facial",
            "bb-glow-facial",
            "piercing",
            "paid-package-old-owner",
            "package-price-do-3-and-get-1-free",
        ],
    }
    for name, role, specialization in STAFF:
        staff = db.scalar(select(Staff).where(Staff.name == name))
        if not staff:
            staff = Staff(
                name=name,
                email=f"{name.lower().replace('dr. ', '').replace(' ', '.')}@clinicflow.local",
                phone="+971500000000",
                role=role,
                specialization=specialization,
            )
            db.add(staff)
            db.flush()

        staff.services = [all_services[slug] for slug in assignments[name] if slug in all_services]
        if not staff.availability:
            staff.availability = [
                StaffAvailability(
                    day_of_week=day,
                    start_time=time(10, 0),
                    end_time=time(18, 0),
                    break_start_time=time(13, 0),
                    break_end_time=time(14, 0),
                )
                for day in range(6)
            ]


def seed_database(db: Session) -> None:
    seed_admin(db)
    services = seed_categories_and_services(db)
    seed_staff(db, services)
    db.commit()
