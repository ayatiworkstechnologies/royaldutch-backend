import time

from app.db.session import SessionLocal
from app.services.mail_queue_service import claim_queued_mail, process_claimed_mail, recover_stale_processing_mail


def run_worker(poll_seconds: int = 10) -> None:
    print("Mail worker started")
    while True:
        try:
            with SessionLocal() as db:
                recover_stale_processing_mail(db)
                messages = claim_queued_mail(db, limit=10, include_failed=True)
                for mail in messages:
                    process_claimed_mail(db, mail)
                if messages:
                    db.commit()
        except Exception as exc:
            print(f"Mail worker error: {exc}")
        time.sleep(poll_seconds)


if __name__ == "__main__":
    run_worker()
