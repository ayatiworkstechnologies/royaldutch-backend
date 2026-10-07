from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.service import ServiceCreate, ServiceUpdate


def service_payload(price):
    return {
        "category_id": 1,
        "name": "Consultation",
        "slug": "consultation",
        "price": price,
    }


@pytest.mark.parametrize("price", ["", "   ", None])
def test_create_service_treats_blank_price_as_none(price):
    assert ServiceCreate(**service_payload(price)).price is None


@pytest.mark.parametrize("price", [250, "250.50", "1,250.50"])
def test_create_service_accepts_numeric_prices(price):
    expected = Decimal(str(price).replace(",", ""))
    assert ServiceCreate(**service_payload(price)).price == expected


def test_update_service_treats_blank_price_as_none():
    assert ServiceUpdate(price="").price is None


def test_service_rejects_price_ranges():
    with pytest.raises(ValidationError):
        ServiceCreate(**service_payload("200-500"))
