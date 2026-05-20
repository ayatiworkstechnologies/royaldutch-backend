from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, get_current_admin
from app.models.email_template import EmailTemplate
from app.schemas.email_template import EmailTemplateCreate, EmailTemplateRead, EmailTemplateUpdate
from app.services.email_template_service import seed_default_email_templates

router = APIRouter(prefix="/email-templates", tags=["email templates"], dependencies=[Depends(get_current_admin)])


@router.get("", response_model=list[EmailTemplateRead])
def list_email_templates(db: DbSession) -> list[EmailTemplate]:
    return list(db.scalars(select(EmailTemplate).order_by(EmailTemplate.name)).all())


@router.post("/seed-defaults", response_model=list[EmailTemplateRead])
def seed_email_templates(db: DbSession) -> list[EmailTemplate]:
    seed_default_email_templates(db)
    return list(db.scalars(select(EmailTemplate).order_by(EmailTemplate.name)).all())


@router.post("", response_model=EmailTemplateRead)
def create_email_template(data: EmailTemplateCreate, db: DbSession) -> EmailTemplate:
    exists = db.scalar(select(EmailTemplate).where(EmailTemplate.slug == data.slug))
    if exists:
        raise HTTPException(status_code=400, detail="Template slug already exists")
    template = EmailTemplate(**data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.patch("/{template_id}", response_model=EmailTemplateRead)
def update_email_template(template_id: int, data: EmailTemplateUpdate, db: DbSession) -> EmailTemplate:
    template = db.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    values = data.model_dump(exclude_unset=True)
    if "slug" in values and values["slug"] != template.slug:
        exists = db.scalar(select(EmailTemplate).where(EmailTemplate.slug == values["slug"]))
        if exists:
            raise HTTPException(status_code=400, detail="Template slug already exists")
    for field, value in values.items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}")
def delete_email_template(template_id: int, db: DbSession) -> dict:
    template = db.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    db.delete(template)
    db.commit()
    return {"message": "Email template deleted"}
