import argparse

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.seed.clinic_data import seed_admin, seed_categories_and_services, seed_database
from app.services.email_template_service import seed_default_email_templates


def seed_login(db) -> None:
    seed_admin(db)
    db.commit()


def seed_services(db) -> None:
    seed_categories_and_services(db)
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Royal Dutch backend data.")
    parser.add_argument("--login", action="store_true", help="Seed or reset the default admin login only.")
    parser.add_argument("--services", action="store_true", help="Seed service categories, services and staff only.")
    parser.add_argument("--templates", action="store_true", help="Seed email templates only.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if args.login:
            seed_login(db)
            print("Admin seed complete. Login: admin@royaldutch.ae / Admin@12345")
        if args.services:
            seed_services(db)
            print("Services seed complete. Categories, services and staff are ready.")
        if args.templates:
            seed_default_email_templates(db)
            db.commit()
            print("Email template seed complete.")
        if not (args.login or args.services or args.templates):
            seed_database(db)
            seed_default_email_templates(db)
            print("Full seed complete. Admin login: admin@royaldutch.ae / Admin@12345")


if __name__ == "__main__":
    main()
