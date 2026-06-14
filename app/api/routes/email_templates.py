from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.email_template import EmailTemplate
from app.models.user import User
from app.schemas.email_template import EmailTemplateCreate, EmailTemplateRead, EmailTemplateUpdate
from app.services.email_template_service import seed_default_email_templates
from app.services.audit_service import model_snapshot, write_audit_log

router = APIRouter(prefix="/email-templates", tags=["email templates"], dependencies=[Depends(require_permission("email_templates.manage"))])


@router.get("", response_model=list[EmailTemplateRead])
def list_email_templates(db: DbSession) -> list[EmailTemplate]:
    return list(db.scalars(select(EmailTemplate).order_by(EmailTemplate.name)).all())


@router.post("/seed-defaults", response_model=list[EmailTemplateRead])
def seed_email_templates(db: DbSession, request: Request, user: User = Depends(get_current_user)) -> list[EmailTemplate]:
    seed_default_email_templates(db)
    templates = list(db.scalars(select(EmailTemplate).order_by(EmailTemplate.name)).all())
    write_audit_log(db, action="email_template.seed_defaults", entity_type="EmailTemplate", user=user, request=request, new_value={"count": len(templates)})
    db.commit()
    return templates


@router.post("", response_model=EmailTemplateRead)
def create_email_template(data: EmailTemplateCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> EmailTemplate:
    exists = db.scalar(select(EmailTemplate).where(EmailTemplate.slug == data.slug))
    if exists:
        raise HTTPException(status_code=400, detail="Template slug already exists")
    template = EmailTemplate(**data.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    write_audit_log(db, action="email_template.create", entity_type="EmailTemplate", entity_id=template.id, user=user, request=request, new_value=model_snapshot(template))
    db.commit()
    return template


@router.patch("/{template_id}", response_model=EmailTemplateRead)
def update_email_template(template_id: int, data: EmailTemplateUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> EmailTemplate:
    template = db.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    old_value = model_snapshot(template)
    values = data.model_dump(exclude_unset=True)
    if "slug" in values and values["slug"] != template.slug:
        exists = db.scalar(select(EmailTemplate).where(EmailTemplate.slug == values["slug"]))
        if exists:
            raise HTTPException(status_code=400, detail="Template slug already exists")
    for field, value in values.items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    write_audit_log(db, action="email_template.update", entity_type="EmailTemplate", entity_id=template.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(template))
    db.commit()
    return template


@router.delete("/{template_id}")
def delete_email_template(template_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> dict:
    template = db.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    old_value = model_snapshot(template)
    db.delete(template)
    write_audit_log(db, action="email_template.delete", entity_type="EmailTemplate", entity_id=template_id, user=user, request=request, old_value=old_value)
    db.commit()
    return {"message": "Email template deleted"}
