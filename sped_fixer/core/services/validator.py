import re
from datetime import datetime
from typing import Dict, List, Any, TypedDict
from enum import Enum

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
    


class IssueSeverity(Enum):
    """Níveis de severidade para os problemas encontrados"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ValidationContext(TypedDict):
    """Contexto de validação contendo dados dos registros"""
    # Dicionário com os dados dos registros, onde a chave é o tipo de registro
    # e o valor é uma lista de registros (cada registro é uma lista de strings)
    # Exemplo: {"0000": [["0000", "013", "0", ...], ...]}
    Any: List[List[str]]