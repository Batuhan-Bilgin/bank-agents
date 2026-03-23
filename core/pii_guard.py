import re

_PATTERNS = [
    ("TC_KIMLIK", re.compile(r"\b[1-9]\d{10}\b")),
    ("IBAN", re.compile(r"\bTR\d{2}[0-9A-Z]{22}\b", re.IGNORECASE)),
    ("KART_NO", re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b")),
    ("TELEFON", re.compile(r"\b(?:\+90|0)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b")),
    ("EMAIL", re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")),
    ("HESAP_NO", re.compile(r"\b\d{16}\b")),
    ("IP_ADRESI", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("PASAPORT", re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")),
]

_MASK_CHAR = "*"


def mask(text: str, types: list[str] | None = None) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    result = text
    for label, pattern in _PATTERNS:
        if types and label not in types:
            continue
        matches = pattern.findall(result)
        if matches:
            counts[label] = len(matches)
            result = pattern.sub(lambda m: _mask_value(m.group(), label), result)
    return result, counts


def _mask_value(value: str, label: str) -> str:
    n = len(value)
    if label == "TC_KIMLIK":
        return value[:3] + _MASK_CHAR * 6 + value[-2:]
    if label == "KART_NO":
        clean = re.sub(r"[\s\-]", "", value)
        return clean[:4] + _MASK_CHAR * 8 + clean[-4:]
    if label == "EMAIL":
        parts = value.split("@")
        local = parts[0]
        masked_local = local[:2] + _MASK_CHAR * (len(local) - 2) if len(local) > 2 else _MASK_CHAR * len(local)
        return f"{masked_local}@{parts[1]}"
    if label == "IBAN":
        return value[:6] + _MASK_CHAR * (n - 10) + value[-4:]
    return _MASK_CHAR * n


def scan(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for label, pattern in _PATTERNS:
        matches = pattern.findall(text)
        if matches:
            found[label] = matches
    return found


def has_pii(text: str) -> bool:
    return any(pattern.search(text) for _, pattern in _PATTERNS)


def guard_tool_result(tool_name: str, result: dict) -> dict:
    import json
    raw = json.dumps(result, ensure_ascii=False)
    masked, counts = mask(raw)
    if counts:
        try:
            import json as _json
            result = _json.loads(masked)
            result["_pii_masked"] = counts
        except Exception:
            result = {"_raw_masked": masked, "_pii_masked": counts}
    return result
