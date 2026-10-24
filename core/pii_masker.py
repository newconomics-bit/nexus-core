import re


def mask_phone(phone: str) -> str:
    """
    Mask Indonesian phone number.
    Format: 081234567890 -> 0812***7890
    Shows first 4 digits and last 4 digits, masks the middle.
    """
    # Match Indonesian phone numbers (08xx-xxxx-xxxx or 08xxxxxxxxxx)
    phone_pattern = re.compile(r"(08\d{2})(\d{4,})(\d{4})")
    match = phone_pattern.search(phone)
    if match:
        prefix = match.group(1)
        middle_len = len(match.group(2))
        suffix = match.group(3)
        masked_middle = "*" * middle_len
        return f"{prefix}{masked_middle}{suffix}"
    return phone


def mask_invoice_amount(amount: int | str) -> str:
    """
    Mask invoice amount for non-finance logs.
    Returns: "Rp ***"
    """
    return "Rp ***"


def mask_pii_in_text(text: str) -> str:
    """
    Scan text and replace phone numbers and invoice amounts with masked versions.
    
    Phone pattern: Indonesian numbers starting with 08
    Amount pattern: Rp followed by digits (with optional dots/commas)
    """
    result = text
    
    # Mask phone numbers (08xxxxxxxxxx format)
    phone_pattern = re.compile(r"(08\d{2})(\d{4,})(\d{4})")
    result = phone_pattern.sub(lambda m: f"{m.group(1)}{'*' * len(m.group(2))}{m.group(3)}", result)
    
    # Mask invoice amounts (Rp 150000, Rp 1.500.000, Rp 1,500,000, etc.)
    amount_pattern = re.compile(r"(Rp\s*[\d.,]+)")
    result = amount_pattern.sub("Rp ***", result)
    
    return result