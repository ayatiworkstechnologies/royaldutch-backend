from __future__ import annotations

from app.core.config import get_settings

BASE_SYSTEM_PROMPT = """You are the AI assistant for Royal Dutch Medical Centre (RDMC), a premium private medical clinic in Dubai, UAE.

Clinic details:
- Name: Royal Dutch Medical Centre
- Location: Dubai, UAE
- Hours: Monday to Saturday, 10:00 AM – 8:00 PM (closed Sundays)
- Toll Free: 800-ROYAL (76925)

Your role:
- Answer questions about our clinic services, pricing, duration, and availability.
- Help patients understand their health concerns and guide them to the right service.
- When a user asks about a specific condition or symptom, suggest the relevant service(s) from our catalog.
- For general medical questions, give clear, professional, and compassionate answers — but always remind patients to consult a licensed physician for personal diagnosis or treatment.
- When a user is ready to book, encourage them to use the in-chat booking flow.
- Do NOT diagnose, prescribe medication, or give definitive medical opinions.
- Keep answers concise (2-4 sentences max unless listing services).
- Language: respond in the same language the user writes in.

Tone: Warm, professional, knowledgeable — like a trusted clinic receptionist who also has medical knowledge."""


def _build_service_context(services: list[dict], categories: list[dict]) -> str:
    if not services and not categories:
        return ""

    lines = ["\n\n--- CLINIC SERVICES CATALOG ---"]

    cat_map = {c["id"]: c["name"] for c in categories if "id" in c and "name" in c}

    # Group by category
    by_cat: dict[str, list[dict]] = {}
    for s in services:
        cat_name = cat_map.get(s.get("category_id"), "General")
        by_cat.setdefault(cat_name, []).append(s)

    for cat_name, svcs in by_cat.items():
        lines.append(f"\n{cat_name}:")
        for s in svcs[:10]:
            price_str = f"{s.get('currency','AED')} {s.get('price','—')}" if s.get("price") else ""
            dur_str = f"{s.get('duration_minutes')} mins" if s.get("duration_minutes") else ""
            desc = (s.get("description") or "")[:120]
            detail = " | ".join(filter(None, [price_str, dur_str, desc]))
            lines.append(f"  • {s.get('name','')} — {detail}")

    lines.append("\n--- END OF CATALOG ---")
    return "\n".join(lines)


def get_chat_response(
    messages: list[dict],
    services: list[dict] | None = None,
    categories: list[dict] | None = None,
) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return (
            "The AI assistant is not configured yet. "
            "Please contact the clinic at 800-ROYAL (76925) or use the booking flow."
        )

    system = BASE_SYSTEM_PROMPT + _build_service_context(
        services or [], categories or []
    )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            system=system,
            messages=messages,
        )
        return response.content[0].text
    except Exception:
        return (
            "I'm temporarily unable to respond. "
            "Please call us at 800-ROYAL (76925) for immediate assistance."
        )
