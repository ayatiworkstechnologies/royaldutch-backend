from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.category import Category
from app.models.enums import RecordStatus, UserRole
from app.models.service import Service
from app.models.staff import Staff, StaffAvailability
from app.models.user import User

ROYAL_DUTCH_SERVICES = [
   {
        "id": 1,
        "category": "Dermatology & Aesthetic Medicine",
        "slug": "dermatology-aesthetic-medicine",
        "services": [
            {"id": 1001, "name": "Medical dermatology", "slug": "medical-dermatology", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1002, "name": "Cosmetic injectables", "slug": "cosmetic-injectables", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1003, "name": "Laser and device based treatments", "slug": "laser-device-based-treatments", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1004, "name": "Anti-aging and preventive skin programs", "slug": "anti-aging-preventive-skin-programs", "durationMinutes": 45, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 2,
        "category": "Dentistry Department",
        "slug": "dentistry-department",
        "services": [
            {"id": 1101, "name": "Preventive and general dentistry", "slug": "preventive-general-dentistry", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1102, "name": "Cosmetic smile design and rehabilitation", "slug": "cosmetic-smile-design-rehabilitation", "durationMinutes": 60, "price": None, "currency": "AED"},
            {"id": 1103, "name": "Restorative dentistry", "slug": "restorative-dentistry", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1104, "name": "Pediatric dentistry", "slug": "pediatric-dentistry", "durationMinutes": 30, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 3,
        "category": "General Medicine (GP Services)",
        "slug": "general-medicine",
        "services": [
            {"id": 1201, "name": "Diagnosis and treatment of acute conditions", "slug": "diagnosis-treatment-acute-conditions", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1202, "name": "Chronic disease management", "slug": "chronic-disease-management", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1203, "name": "Preventive health screenings and check-ups", "slug": "preventive-health-screenings-checkups", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1204, "name": "Family medicine and wellness care", "slug": "family-medicine-wellness-care", "durationMinutes": 30, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 4,
        "category": "Physiotherapy & Rehabilitation",
        "slug": "physiotherapy-rehabilitation",
        "services": [
            {"id": 1301, "name": "Musculoskeletal and pain management therapy", "slug": "musculoskeletal-pain-management", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1302, "name": "Post-injury and post-operative rehabilitation", "slug": "post-injury-post-operative-rehabilitation", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1303, "name": "Neurological physiotherapy", "slug": "neurological-physiotherapy", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1304, "name": "Home-based physiotherapy programs", "slug": "home-based-physiotherapy-programs", "durationMinutes": 45, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 5,
        "category": "Home Healthcare Division",
        "slug": "home-healthcare-division",
        "services": [
            {"id": 1401, "name": "Doctor home consultations", "slug": "doctor-home-consultations", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1402, "name": "Skilled nursing care", "slug": "skilled-nursing-care", "durationMinutes": 60, "price": None, "currency": "AED"},
            {"id": 1403, "name": "Elderly and assisted care services", "slug": "elderly-assisted-care-services", "durationMinutes": 60, "price": None, "currency": "AED"},
            {"id": 1404, "name": "Chronic condition monitoring", "slug": "chronic-condition-monitoring", "durationMinutes": 45, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 6,
        "category": "Post-Surgical Care Programs",
        "slug": "post-surgical-care-programs",
        "services": [
            {"id": 1501, "name": "Wound care and infection prevention", "slug": "wound-care-infection-prevention", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1502, "name": "Pain management protocols", "slug": "pain-management-protocols", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1503, "name": "Rehabilitation and mobility restoration", "slug": "rehabilitation-mobility-restoration", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1504, "name": "Long-term recovery and follow-up care", "slug": "long-term-recovery-follow-up-care", "durationMinutes": 45, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 7,
        "category": "Integrated Care Model",
        "slug": "integrated-care-model",
        "services": [
            {"id": 1601, "name": "Seamless coordination between departments", "slug": "seamless-coordination-between-departments", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1602, "name": "Continuity of care from consultation to recovery", "slug": "continuity-of-care", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1603, "name": "Personalized treatment pathways", "slug": "personalized-treatment-pathways", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1604, "name": "Improved clinical outcomes and patient satisfaction", "slug": "improved-clinical-outcomes", "durationMinutes": 30, "price": None, "currency": "AED"},
        ],
    },
]



_SEED_USERS = [
    # (name, email, password, role)
    ("Royal Dutch Admin",   "admin@royaldutch.ae",        "Admin@12345",        UserRole.super_admin),
    ("Royal Dutch Manager", "manager@royaldutch.ae",      "Manager@12345",      UserRole.admin),
    ("Royal Dutch Reception", "reception@royaldutch.ae",  "Reception@12345",    UserRole.receptionist),
]


def seed_admin(db: Session) -> None:
    for name, email, password, role in _SEED_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            if user.role != role:
                user.role = role
        else:
            db.add(User(
                name=name,
                email=email,
                hashed_password=hash_password(password),
                role=role,
            ))


def seed_categories_and_services(db: Session) -> list[Service]:
    """Insert-only seed: never updates existing rows to avoid TiDB unique constraint issues."""
    services: list[Service] = []

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
            services.append(service)
    return services


STAFF_PROFILES: list[dict] = []


def seed_staff(db: Session, services: list[Service]) -> None:
    services_by_slug = {service.slug: service for service in services}

    for profile in STAFF_PROFILES:
        staff = db.scalar(select(Staff).where(Staff.email == profile["email"]))
        if not staff:
            staff = db.scalar(select(Staff).where(Staff.name == profile["name"]))
        if not staff:
            staff = Staff(
                name=profile["name"],
                email=profile["email"],
                phone=profile["phone"],
                role=profile["role"],
                specialization=profile["specialization"],
                status=RecordStatus.active,
            )
            db.add(staff)
            db.flush()
        else:
            staff.name = profile["name"]
            staff.phone = profile["phone"]
            staff.role = profile["role"]
            staff.specialization = profile["specialization"]
            staff.status = RecordStatus.active

        staff.services = [services_by_slug[slug] for slug in profile["service_slugs"] if slug in services_by_slug]

        if not staff.availability:
            staff.availability = [
                StaffAvailability(
                    day_of_week=day,
                    start_time=time(9, 0),
                    end_time=time(18, 0),
                    break_start_time=time(13, 0),
                    break_end_time=time(14, 0),
                    status=RecordStatus.active,
                )
                for day in range(6)
            ]
def seed_database(db: Session) -> None:
    try:
        seed_admin(db)
        services = seed_categories_and_services(db)
        seed_staff(db, services)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Seed warning (non-fatal): {exc}")
