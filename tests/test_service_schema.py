from app.schemas.service import ServiceCreate, ServiceUpdate


def service_payload():
    return {
        "category_id": 1,
        "name": "Consultation",
        "slug": "consultation",
    }


def test_service_schema_has_no_price_or_duration_fields():
    service = ServiceCreate(**service_payload())
    assert "price" not in service.model_fields_set
    assert "duration_minutes" not in service.model_fields_set


def test_service_update_has_no_price_or_duration_fields():
    update = ServiceUpdate(name="Updated consultation")
    assert "price" not in update.model_fields_set
    assert "duration_minutes" not in update.model_fields_set
