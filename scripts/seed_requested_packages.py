"""Create the requested 2+1 and 3+1 packages without changing sub-services.

Safe to rerun: every package is matched by its sub-service and package slug.
"""

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import RecordStatus
from app.models.service import Service
from app.models.service_package import ServicePackage
from app.models.sub_service import SubService


# slug: (2+1 package price, 3+1 package price)
FACIAL_PACKAGES = {
    "classic-facial": (374, 449),
    "vitamin-c-hydrafacial": (624, 749),
    "acne-control-facial": (874, 1049),
}
WOMEN_LASER_PACKAGES = {
    "chin-upper-lip": (184, 224),
    "upper-lip": (124, 149),
    "underarms": (299, 359),
    "bikini-lines-half": (374, 449),
    "bikini-lines-full": (499, 599),
    "full-arms-hands": (499, 599),
    "full-arms-hands-underarms": (624, 749),
    "half-arms-hands": (374, 449),
    "full-body-without-belly-back": (1124, 1349),
    "full-body-with-belly-back": (1624, 1949),
}
MEN_LASER_PACKAGES = {
    "beard": (249, 299),
    "underarms": (374, 449),
    "half-legs": (999, 1199),
    "full-legs": (1499, 1799),
    "back": (999, 1199),
}


def upsert_package(db, sub_service: SubService, label: str, sessions: int, price: int) -> bool:
    slug = f"{sub_service.slug}-{label.lower().replace('+', '-')}-package"
    package = db.scalar(select(ServicePackage).where(
        ServicePackage.sub_service_id == sub_service.id,
        ServicePackage.slug == slug,
    ))
    created = package is None
    if package is None:
        package = ServicePackage(sub_service_id=sub_service.id, slug=slug)
        db.add(package)
    package.name = f"{sub_service.name} {label} Package"
    # Package labels already communicate 2+1 / 3+1; leave the optional
    # session-count field empty so the admin table matches the requested UI.
    package.sessions = None
    package.price = f"{price:.2f}"
    package.currency = "AED"
    package.status = RecordStatus.active
    package.description = f"{label} package: {sessions} sessions."
    return created


def add_for_service(db, service: Service, prices: dict[str, tuple[int, int]]) -> tuple[int, int]:
    sub_services = {item.slug: item for item in service.sub_services}
    missing = sorted(set(prices) - set(sub_services))
    if missing:
        raise RuntimeError(f"Missing sub-services for {service.name}: {', '.join(missing)}")
    created = updated = 0
    for sub_service_slug, (two_plus_one, three_plus_one) in prices.items():
        sub_service = sub_services[sub_service_slug]
        for label, sessions, price in (("2+1", 3, two_plus_one), ("3+1", 4, three_plus_one)):
            if upsert_package(db, sub_service, label, sessions, price):
                created += 1
            else:
                updated += 1
    return created, updated


def main() -> None:
    with SessionLocal() as db:
        facial = db.scalar(select(Service).where(Service.slug == "facial-treatments"))
        women = db.scalar(select(Service).where(Service.display_id == 40))
        men = db.scalar(select(Service).where(Service.display_id == 39))
        if not all((facial, women, men)):
            raise RuntimeError("Required facial, women's laser, or men's laser parent service was not found")
        totals = [
            add_for_service(db, facial, FACIAL_PACKAGES),
            add_for_service(db, women, WOMEN_LASER_PACKAGES),
            add_for_service(db, men, MEN_LASER_PACKAGES),
        ]
        db.commit()
        print(f"Packages created: {sum(item[0] for item in totals)}; updated: {sum(item[1] for item in totals)}")


if __name__ == "__main__":
    main()
