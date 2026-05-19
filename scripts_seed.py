from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.seed.clinic_data import seed_database


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    print("Seed complete. Admin login: admin@clinicflow.local / Admin@12345")


if __name__ == "__main__":
    main()
