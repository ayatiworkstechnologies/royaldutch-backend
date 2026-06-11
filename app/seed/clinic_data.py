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

STAFF = [
    ("Dr. Aisha", "Dermatologist", "PMU, skin treatments and consultation"),
    ("Dr. Sana", "Laser Specialist", "Candela laser and slimming treatments"),
    ("Dr. Farah", "Facial Therapist", "Facials, eyelashes and lightening treatments"),
    ("Dr. Omar", "General Practitioner", "General medicine, wellness care and home consultations"),
    ("Dr. Leena", "Dentist", "General dentistry, smile design and pediatric dentistry"),
    ("Dr. Kareem", "Physiotherapist", "Rehabilitation, mobility recovery and pain management"),
    ("Nurse Maryam", "Home Healthcare Coordinator", "Nursing care, elderly support and post-surgical follow-up"),
]


def seed_admin(db: Session) -> None:
    email = "admin@royaldutch.ae"
    admin = db.scalar(select(User).where(User.email == email))
    if admin:
        admin.name = "Royal Dutch Admin"
        admin.email = email
        admin.hashed_password = hash_password("Admin@12345")
        admin.role = UserRole.admin
        admin.is_active = True
        return
    db.add(
        User(
            name="Royal Dutch Admin",
            email=email,
            hashed_password=hash_password("Admin@12345"),
            role=UserRole.admin,
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
            service = db.scalar(
                select(Service).where(
                    (Service.slug == service_data["slug"]) | (Service.external_id == service_data["id"])
                )
            )
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
                service.slug = service_data["slug"]
                service.duration_minutes = service_data["durationMinutes"]
                service.price = service_data["price"]
                service.currency = service_data["currency"]
                service.status = RecordStatus.active
            services.append(service)
    return services


def seed_staff(db: Session, services: list[Service]) -> None:
    all_services = {service.slug: service for service in services}
    role_category_mapping = {
        "Dermatologist": ["dermatology-aesthetic-medicine"],
        "Laser Specialist": ["dermatology-aesthetic-medicine"],
        "Facial Therapist": ["dermatology-aesthetic-medicine"],
        "General Practitioner": ["general-medicine", "integrated-care-model"],
        "Dentist": ["dentistry-department"],
        "Physiotherapist": ["physiotherapy-rehabilitation"],
        "Home Healthcare Coordinator": ["home-healthcare-division", "post-surgical-care-programs", "integrated-care-model"],
    }

    category_to_service_slugs = {
        cat["slug"]: [svc["slug"] for svc in cat["services"]]
        for cat in ROYAL_DUTCH_SERVICES
    }
    for name, role, specialization in STAFF:
        staff = db.scalar(select(Staff).where(Staff.name == name))
        if not staff:
            staff = Staff(
                name=name,
                email=f"{name.lower().replace('dr. ', '').replace(' ', '.')}@royaldutch.ae",
                phone="+971500000000",
                role=role,
                specialization=specialization,
            )
            db.add(staff)
            db.flush()

        assigned_slugs = []
        for cat_slug in role_category_mapping.get(role, []):
            assigned_slugs.extend(category_to_service_slugs.get(cat_slug, []))
            
        staff.services = [all_services[slug] for slug in assigned_slugs if slug in all_services]
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
