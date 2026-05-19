from datetime import time

from app.models.enums import RecordStatus
from app.schemas.common import ORMModel, Timestamped


class StaffAvailabilityBase(ORMModel):
    day_of_week: int
    start_time: time
    end_time: time
    break_start_time: time | None = None
    break_end_time: time | None = None
    status: RecordStatus = RecordStatus.active


class StaffAvailabilityCreate(StaffAvailabilityBase):
    pass


class StaffAvailabilityRead(StaffAvailabilityBase, Timestamped):
    id: int
    staff_id: int


class StaffBase(ORMModel):
    name: str
    email: str | None = None
    phone: str | None = None
    role: str
    specialization: str | None = None
    profile_image: str | None = None
    status: RecordStatus = RecordStatus.active


class StaffCreate(StaffBase):
    service_ids: list[int] = []
    availability: list[StaffAvailabilityCreate] = []


class StaffUpdate(ORMModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    specialization: str | None = None
    profile_image: str | None = None
    status: RecordStatus | None = None
    service_ids: list[int] | None = None
    availability: list[StaffAvailabilityCreate] | None = None


class StaffRead(StaffBase, Timestamped):
    id: int
    service_ids: list[int] = []
    availability: list[StaffAvailabilityRead] = []
