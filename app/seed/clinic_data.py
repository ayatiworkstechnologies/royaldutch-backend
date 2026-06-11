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
    {
        "id": 10,
        "category": "Dermatology & Aesthetic Medicine",
        "slug": "dermatology-aesthetic-medicine",
        "services": [
            {"id": 1001, "name": "Medical Dermatology", "slug": "medical-dermatology", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1002, "name": "Cosmetic Injectables", "slug": "cosmetic-injectables", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1003, "name": "Laser and Device Based Treatments", "slug": "laser-device-based-treatments", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1004, "name": "Anti-Aging and Preventive Skin Programs", "slug": "anti-aging-preventive-skin-programs", "durationMinutes": 45, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 11,
        "category": "Dentistry Department",
        "slug": "dentistry-department",
        "services": [
            {"id": 1101, "name": "Preventive and General Dentistry", "slug": "preventive-general-dentistry", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1102, "name": "Cosmetic Smile Design and Rehabilitation", "slug": "cosmetic-smile-design-rehabilitation", "durationMinutes": 60, "price": None, "currency": "AED"},
            {"id": 1103, "name": "Restorative Dentistry", "slug": "restorative-dentistry", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1104, "name": "Pediatric Dentistry", "slug": "pediatric-dentistry", "durationMinutes": 30, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 12,
        "category": "General Medicine (GP Services)",
        "slug": "general-medicine",
        "services": [
            {"id": 1201, "name": "Diagnosis and Treatment of Acute Conditions", "slug": "diagnosis-treatment-acute-conditions", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1202, "name": "Chronic Disease Management", "slug": "chronic-disease-management", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1203, "name": "Preventive Health Screenings and Check-Ups", "slug": "preventive-health-screenings-checkups", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1204, "name": "Family Medicine and Wellness Care", "slug": "family-medicine-wellness-care", "durationMinutes": 30, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 13,
        "category": "Physiotherapy & Rehabilitation",
        "slug": "physiotherapy-rehabilitation",
        "services": [
            {"id": 1301, "name": "Musculoskeletal and Pain Management Therapy", "slug": "musculoskeletal-pain-management", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1302, "name": "Post-Injury and Post-Operative Rehabilitation", "slug": "post-injury-post-operative-rehabilitation", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1303, "name": "Neurological Physiotherapy", "slug": "neurological-physiotherapy", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1304, "name": "Home-Based Physiotherapy Programs", "slug": "home-based-physiotherapy-programs", "durationMinutes": 45, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 14,
        "category": "Home Healthcare Division",
        "slug": "home-healthcare-division",
        "services": [
            {"id": 1401, "name": "Doctor Home Consultations", "slug": "doctor-home-consultations", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1402, "name": "Skilled Nursing Care", "slug": "skilled-nursing-care", "durationMinutes": 60, "price": None, "currency": "AED"},
            {"id": 1403, "name": "Elderly and Assisted Care Services", "slug": "elderly-assisted-care-services", "durationMinutes": 60, "price": None, "currency": "AED"},
            {"id": 1404, "name": "Chronic Condition Monitoring", "slug": "chronic-condition-monitoring", "durationMinutes": 45, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 15,
        "category": "Post-Surgical Care Programs",
        "slug": "post-surgical-care-programs",
        "services": [
            {"id": 1501, "name": "Wound Care and Infection Prevention", "slug": "wound-care-infection-prevention", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1502, "name": "Pain Management Protocols", "slug": "pain-management-protocols", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1503, "name": "Rehabilitation and Mobility Restoration", "slug": "rehabilitation-mobility-restoration", "durationMinutes": 45, "price": None, "currency": "AED"},
            {"id": 1504, "name": "Long-Term Recovery and Follow-Up Care", "slug": "long-term-recovery-follow-up-care", "durationMinutes": 45, "price": None, "currency": "AED"},
        ],
    },
    {
        "id": 16,
        "category": "Integrated Care Model",
        "slug": "integrated-care-model",
        "services": [
            {"id": 1601, "name": "Care Coordination Between Departments", "slug": "care-coordination-between-departments", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1602, "name": "Continuity of Care From Consultation to Recovery", "slug": "continuity-of-care", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1603, "name": "Personalized Treatment Pathways", "slug": "personalized-treatment-pathways", "durationMinutes": 30, "price": None, "currency": "AED"},
            {"id": 1604, "name": "Clinical Outcomes and Patient Satisfaction Review", "slug": "clinical-outcomes-patient-satisfaction", "durationMinutes": 30, "price": None, "currency": "AED"},
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
    admin = db.scalar(select(AdminUser).where(AdminUser.email == email))
    if admin:
        admin.name = "Royal Dutch Admin"
        admin.email = email
        admin.hashed_password = hash_password("Admin@12345")
        admin.is_active = True
        return
    db.add(
        AdminUser(
            name="Royal Dutch Admin",
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
            "medical-dermatology",
            "laser-device-based-treatments",
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
            "cosmetic-injectables",
            "anti-aging-preventive-skin-programs",
        ],
        "Dr. Omar": [
            "diagnosis-treatment-acute-conditions",
            "chronic-disease-management",
            "preventive-health-screenings-checkups",
            "family-medicine-wellness-care",
            "doctor-home-consultations",
            "continuity-of-care",
            "personalized-treatment-pathways",
            "clinical-outcomes-patient-satisfaction",
        ],
        "Dr. Leena": [
            "preventive-general-dentistry",
            "cosmetic-smile-design-rehabilitation",
            "restorative-dentistry",
            "pediatric-dentistry",
        ],
        "Dr. Kareem": [
            "musculoskeletal-pain-management",
            "post-injury-post-operative-rehabilitation",
            "neurological-physiotherapy",
            "home-based-physiotherapy-programs",
            "rehabilitation-mobility-restoration",
        ],
        "Nurse Maryam": [
            "skilled-nursing-care",
            "elderly-assisted-care-services",
            "chronic-condition-monitoring",
            "wound-care-infection-prevention",
            "pain-management-protocols",
            "long-term-recovery-follow-up-care",
            "care-coordination-between-departments",
        ],
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
