import re
from datetime import datetime

# Compilação da expressão regular para remover não dígitos
DIGITS = re.compile(r"\D+")

def only_digits(s: str) -> str:
    """Remove todos os caracteres não numéricos de uma string"""
    return DIGITS.sub("", s or "")

def parse_date(s: str, fmt: str = "%d%m%Y") -> datetime | None:
    """Tenta converter uma string para data usando o formato especificado"""
    try:
        return datetime.strptime(s, fmt)
    except Exception:
        return None