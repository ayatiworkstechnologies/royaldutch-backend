from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.seed.clinic_data import seed_database
from app.services.email_template_service import seed_default_email_templates


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
        seed_default_email_templates(db)
    print("Seed complete. Admin login: admin@clinicflow.local / Admin@12345")


if __name__ == "__main__":
    main()
