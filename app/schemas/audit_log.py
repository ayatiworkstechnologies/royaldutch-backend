from app.schemas.common import Timestamped


class AuditLogRead(Timestamped):
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    old_value: dict | None
    new_value: dict | None
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
