# apps/core/parsers.py
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Record:
    line_no: int
    reg: str
    fields: List[str]
    raw: str

class SpedParser:
    def parse(self, text: str) -> List[Record]:
        records: List[Record] = []
        for i, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            parts = line.strip().split("|")
            # Formato esperado: ""|REG|campo1|...|"" -> primeiro e último podem ser vazios
            # Encontrar primeiro token REG válido
            tokens = [p for p in parts if p != ""]
            reg = tokens[0] if tokens else ""
            # Campos após o primeiro token válido (exclui REG)
            try:
                reg_index = parts.index(reg)
            except ValueError:
                reg_index = 1
            fields = parts[reg_index+1:-1] if line.endswith("|") else parts[reg_index+1:]
            records.append(Record(i, reg, fields, line))
        return records

    def reassemble(self, records: List[Record]) -> str:
        out = []
        for r in records:
            out.append("|" + r.reg + "|" + "|".join(r.fields) + "|")
        return "\n".join(out) + "\n"