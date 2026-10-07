"""Create the aesthetic parent service and its priced sub-services.

Safe to run repeatedly: records are matched by parent service and slug.
"""
from decimal import Decimal

from app.db.session import SessionLocal
from app.models.category import Category
from app.models.enums import RecordStatus
from app.models.service import Service
from app.models.sub_service import SubService


AESTHETIC_ITEMS = [
    ("Classic Facial", "classic-facial", "150", None),
    ("HydraFacial", "hydrafacial", "250", None),
    ("Vitamin C Hydrafacial", "vitamin-c-hydrafacial", "250", None),
    ("Acne Control Facial", "acne-control-facial", "350", None),
    ("Glowing Dermapen", "glowing-dermapen", "300", None),
    ("Exosome Dermapen", "exosome-dermapen", "499", None),
    ("Pink Drop", "pink-drop", "499", None),
    ("Peeling Pearl Facial", "peeling-pearl-facial", "649", None),
    ("Chemical Peel Brightening Serum", "chemical-peel-brightening-serum", "649", None),
    ("Royal Dutch Facial", "royal-dutch-facial", "300", None),
    ("Fat Freezing (Cryolipolysis)", "fat-freezing-cryolipolysis", "400", "Package: AED 800 for 2+1 sessions."),
    ("Ear Piercing", "ear-piercing", "150", None),
]

WOMEN_LASER_ITEMS = [
    ("Upper Lip", "upper-lip", "50", None),
    ("Chin + Upper Lip", "chin-upper-lip", "75", None),
    ("Underarms", "underarms", "120", None),
    ("Bikini Lines - Half", "bikini-lines-half", "150", None),
    ("Bikini Lines - Full", "bikini-lines-full", "200", None),
    ("Full Arms + Hands", "full-arms-hands", "200", None),
    ("Full Arms + Hands + Underarms", "full-arms-hands-underarms", "250", None),
    ("Half Arms + Hands", "half-arms-hands", "150", None),
    ("Half Legs + Feet", "half-legs-feet", "200", None),
    ("Full Legs + Feet", "full-legs-feet", "300", None),
    ("Full Body Without Belly and Back", "full-body-without-belly-back", "450", None),
    ("Full Body With Belly and Back", "full-body-with-belly-back", "650", None),
]

MEN_LASER_ITEMS = [
    ("Beard", "beard", "100", None),
    ("Underarms", "underarms", "150", None),
    ("Half Legs", "half-legs", "400", None),
    ("Full Legs", "full-legs", "600", None),
    ("Back", "back", "400", None),
    ("Full Body Without Belly and Back", "full-body-without-belly-back", "750", None),
    ("Full Body With Belly and Back", "full-body-with-belly-back", "950", None),
]


def upsert_items(db, service: Service, items: list[tuple[str, str, str, str | None]]) -> tuple[int, int]:
    created = updated = 0
    existing = {item.slug: item for item in service.sub_services}
    for name, slug, price, description in items:
        item = existing.get(slug)
        if item is None:
            item = SubService(service=service, slug=slug)
            db.add(item)
            created += 1
        else:
            updated += 1
        item.name = name
        item.price = str(price)
        item.currency = "AED"
        item.description = description
        item.status = RecordStatus.active
    return created, updated


def main() -> None:
    with SessionLocal() as db:
        category = db.query(Category).filter(Category.slug == "advanced-skin-treatments").one()
        aesthetic = db.query(Service).filter(Service.slug == "aesthetic-and-skin-care-services").one_or_none()
        if aesthetic is None:
            aesthetic = Service(
                category=category,
                name="Aesthetic And Skin Care Services",
                slug="aesthetic-and-skin-care-services",
                description="Facial, skin care and aesthetic treatments.",
                currency="AED",
                status=RecordStatus.active,
            )
            db.add(aesthetic)
            db.flush()

        men = db.query(Service).filter(Service.display_id == 39).one()
        women = db.query(Service).filter(Service.display_id == 40).one()
        if men.status != RecordStatus.active or women.status != RecordStatus.active or category.status != RecordStatus.active:
            raise RuntimeError("Parent services and category must be active")
        # Repair legacy replacement characters in the imported service names.
        men.name = "Men's Laser Hair Removal"
        women.name = "Women's Laser Hair Removal"

        totals = [
            upsert_items(db, aesthetic, AESTHETIC_ITEMS),
            upsert_items(db, women, WOMEN_LASER_ITEMS),
            upsert_items(db, men, MEN_LASER_ITEMS),
        ]
        db.commit()
        print(
            f"Aesthetic service #{aesthetic.display_id}; "
            f"created {sum(item[0] for item in totals)}, updated {sum(item[1] for item in totals)} sub-services"
        )


if __name__ == "__main__":
    main()
