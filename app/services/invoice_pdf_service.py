from decimal import Decimal

from app.models.billing import Invoice


def pdf_escape(value: object) -> str:
    text = str(value or "")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def money(value: Decimal | int | float | None, currency: str) -> str:
    amount = Decimal(value or 0)
    return f"{currency} {amount:.2f}"


def invoice_pdf_filename(invoice: Invoice) -> str:
    safe_number = "".join(ch for ch in invoice.invoice_number if ch.isalnum() or ch in {"-", "_"})
    return f"{safe_number or 'invoice'}.pdf"


def color_command(rgb: tuple[float, float, float]) -> str:
    r, g, b = rgb
    return f"{r} {g} {b} rg"


def add_text(
    commands: list[str],
    x: int,
    y: int,
    text: object,
    size: int = 10,
    font: str = "F1",
    rgb: tuple[float, float, float] = (0.05, 0.09, 0.16),
) -> None:
    commands.append(f"{color_command(rgb)} BT /{font} {size} Tf {x} {y} Td ({pdf_escape(text)}) Tj ET")


def add_line(commands: list[str], x1: int, y1: int, x2: int, y2: int) -> None:
    commands.append(f"{x1} {y1} m {x2} {y2} l S")


def add_rect(commands: list[str], x: int, y: int, width: int, height: int, rgb: tuple[float, float, float]) -> None:
    r, g, b = rgb
    commands.append(f"{r} {g} {b} rg {x} {y} {width} {height} re f")


def wrap_text(value: object, limit: int) -> list[str]:
    words = str(value or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > limit and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def add_wrapped_text(
    commands: list[str],
    x: int,
    y: int,
    text: object,
    limit: int,
    size: int = 9,
    font: str = "F1",
    line_gap: int = 13,
    rgb: tuple[float, float, float] = (0.05, 0.09, 0.16),
) -> int:
    for line in wrap_text(text, limit):
        add_text(commands, x, y, line, size, font, rgb)
        y -= line_gap
    return y


def build_pdf(objects: list[str]) -> bytes:
    content = ["%PDF-1.4\n"]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part.encode("latin-1")) for part in content))
        content.append(f"{index} 0 obj\n{obj}\nendobj\n")
    xref_at = sum(len(part.encode("latin-1")) for part in content)
    content.append(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.append(f"{offset:010d} 00000 n \n")
    content.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF"
    )
    return "".join(content).encode("latin-1", errors="replace")


def generate_invoice_pdf(invoice: Invoice, settings: dict[str, str]) -> bytes:
    patient = invoice.patient or (invoice.booking.patient if invoice.booking else None)
    booking = invoice.booking
    status_text = invoice.status.replace("_", " ").upper()
    dark = (0.16, 0.13, 0.15)
    muted = (0.36, 0.43, 0.53)
    theme_accent = (0.478, 0.169, 0.408)
    white = (1, 1, 1)
    paid_badge = (0.91, 0.98, 0.95)
    due_badge = (1, 0.97, 0.88)
    commands = [
        "0.988 0.984 0.976 rg 0 0 612 792 re f",
        "0.88 0.91 0.95 RG 1 w",
        "0.478 0.169 0.408 rg 0 704 612 88 re f",
        "0.761 0.651 0.380 rg 0 704 612 8 re f",
    ]

    add_text(commands, 44, 754, settings["clinic_name"], 21, "F2", white)
    add_wrapped_text(commands, 44, 734, settings["clinic_address"], 58, 8, "F1", 13, (0.86, 0.91, 0.96))
    add_text(commands, 44, 710, f"{settings['clinic_phone']}  |  {settings['clinic_email']}", 8, "F1", (0.86, 0.91, 0.96))
    add_text(commands, 444, 754, "INVOICE", 27, "F2", white)
    add_text(commands, 444, 731, invoice.invoice_number, 10, "F2", (0.86, 0.91, 0.96))
    add_rect(commands, 444, 710, 114, 17, paid_badge if invoice.balance_due <= 0 else due_badge)
    add_text(commands, 452, 715, status_text, 8, "F2", theme_accent if invoice.balance_due <= 0 else (0.65, 0.33, 0.02))

    add_rect(commands, 44, 592, 248, 82, (1, 1, 1))
    commands.append("0.88 0.91 0.95 RG 44 592 248 82 re S")
    add_text(commands, 60, 650, "BILL TO", 9, "F2", theme_accent)
    add_text(commands, 60, 631, patient.full_name if patient else "Patient", 13, "F2", dark)
    add_text(commands, 60, 613, patient.phone if patient else "", 9, "F1", muted)
    add_text(commands, 60, 599, patient.email if patient and patient.email else "", 9, "F1", muted)

    add_rect(commands, 320, 592, 248, 82, (1, 1, 1))
    commands.append("0.88 0.91 0.95 RG 320 592 248 82 re S")
    add_text(commands, 336, 650, "INVOICE DETAILS", 9, "F2", theme_accent)
    add_text(commands, 336, 631, f"Issue Date: {invoice.issue_date}", 9, "F1", muted)
    add_text(commands, 336, 616, f"Due Date: {invoice.due_date or invoice.issue_date}", 9, "F1", muted)
    add_text(commands, 336, 601, f"Booking: {booking.booking_code if booking else '-'}", 9, "F1", muted)
    if settings.get("tax_registration_number"):
        add_text(commands, 336, 586, f"TRN: {settings['tax_registration_number']}", 9, "F1", muted)

    add_rect(commands, 44, 544, 524, 28, theme_accent)
    add_text(commands, 60, 553, "DESCRIPTION", 9, "F2", white)
    add_text(commands, 326, 553, "QTY", 9, "F2", white)
    add_text(commands, 386, 553, "UNIT PRICE", 9, "F2", white)
    add_text(commands, 504, 553, "TOTAL", 9, "F2", white)

    y = 518
    for item in invoice.items:
        add_wrapped_text(commands, 60, y, item.description, 42, 9, "F2", 13, dark)
        add_text(commands, 335, y, item.quantity, 10, "F1", muted)
        add_text(commands, 390, y, money(item.unit_price, invoice.currency), 10, "F1", muted)
        add_text(commands, 500, y, money(item.line_total, invoice.currency), 10, "F2", dark)
        add_line(commands, 44, y - 15, 568, y - 15)
        y -= 36

    y = min(y - 8, 390)
    add_rect(commands, 336, y - 123, 232, 142, (1, 1, 1))
    commands.append(f"0.88 0.91 0.95 RG 336 {y - 123} 232 142 re S")
    rows = [
        ("Subtotal", invoice.subtotal),
        ("Discount", -invoice.discount_amount),
        ("Tax", invoice.tax_amount),
        ("Total", invoice.total_amount),
        ("Paid", invoice.paid_amount),
        ("Balance Due", invoice.balance_due),
    ]
    total_y = y
    for label, value in rows:
        font = "F2" if label in {"Total", "Balance Due"} else "F1"
        size = 11 if label == "Balance Due" else 9
        row_color = theme_accent if label == "Balance Due" else dark
        add_text(commands, 352, total_y, label, size, font, row_color)
        add_text(commands, 462, total_y, money(value, invoice.currency), size, font, row_color)
        if label == "Total":
            add_line(commands, 352, total_y - 7, 552, total_y - 7)
        total_y -= 20

    add_rect(commands, 44, 188, 248, 92, (1, 1, 1))
    commands.append("0.88 0.91 0.95 RG 44 188 248 92 re S")
    add_text(commands, 60, 258, "PAYMENT SUMMARY", 9, "F2", theme_accent)
    add_text(commands, 60, 238, f"Paid: {money(invoice.paid_amount, invoice.currency)}", 10, "F1", muted)
    add_text(commands, 60, 220, f"Balance Due: {money(invoice.balance_due, invoice.currency)}", 12, "F2", theme_accent)

    add_text(commands, 44, 150, "Terms", 11, "F2", dark)
    add_wrapped_text(commands, 44, 133, settings["invoice_terms"], 95, 8, "F1", 13, muted)
    add_text(commands, 44, 76, settings["invoice_footer"], 10, "F2", dark)
    add_text(commands, 44, 58, "Generated by Royal Dutch Medical Centre billing system", 8, "F1", muted)

    stream = "\n".join(commands)
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream",
    ]
    return build_pdf(objects)
