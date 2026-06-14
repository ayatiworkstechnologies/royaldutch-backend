from math import ceil
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def paginate_query(db: Session, query: Select, page: int, limit: int) -> dict[str, Any]:
    page = max(page, 1)
    limit = min(max(limit, 1), 100)
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    items = db.scalars(query.offset((page - 1) * limit).limit(limit)).unique().all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": ceil(total / limit) if total else 0,
    }
