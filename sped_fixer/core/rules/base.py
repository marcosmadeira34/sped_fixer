# apps/cores/rules/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

# Em seu arquivo de regras (base.py ou rules.py)

class Issue:
    def __init__(self, line_no, reg, rule_id, severity, message, suggestion=None):
        self.line_no = line_no
        self.reg = reg
        self.rule_id = rule_id
        self.severity = severity
        self.message = message
        self.suggestion = suggestion
        self.impacted_records = []  # NOVO: Armazena registros afetados
        self.impact_details = []    # NOVO: Detalhes do impacto (bloco, valor, etc.)

class Rule:
    id: str = ""
    description: str = ""
    severity: str = "error"
    auto_fix: bool = False

    def validate(self, record, context) -> List[Issue]:
        return []

    def fix(self, record, context) -> None:
        """Opcional: altera record.fields inplace quando auto_fix=True."""
        return
    
    
# sped_analyzer/core/rules/base.py

class Context:
    def __init__(self, records):
        self.records = records
        self.sped_type = None  # Será definido posteriormente

    def remove_record(self, record):
        """Remove um registro da lista"""
        if record in self.records:
            self.records.remove(record)



class Record:
    def __init__(self, line_no, reg, fields):
        self.line_no = line_no
        self.reg = reg
        self.fields = fields
        # Referência para o registro pai (usada em registros como C170)
        self.parent = None

    def __str__(self):
        return f"Registro {self.reg} (linha {self.line_no}): {self.fields}"
    
    def __repr__(self):
        return self.__str__()


class SpedFile:
    def __init__(self, records):
        self.records = records



class SPEDTypeIdentifier:
    def __init__(self, records):
        self.records = records
    
    def identify_type(self):
        # Verifica a presença de blocos específicos
        has_fiscal_blocks = any(
            record.reg.startswith(("E", "H")) 
            for record in self.records
        )
        
        has_contrib_blocks = any(
            record.reg.startswith(("M", "1")) 
            for record in self.records
        )
        
        # Verifica se há registros de apuração de PIS/COFINS
        has_pis_cofins_blocks = any(
            record.reg in ["M100", "M200", "M500", "M600", "M110", "M210", "M510", "M610"]
            for record in self.records
        )
        
        # Verifica se há registros de abertura/fechamento de blocos de contribuições
        has_contrib_opening = any(
            record.reg in ["1001", "1010", "9001"] 
            for record in self.records
        )
        
        # No SPED Fiscal, os campos de PIS/COFINS nos registros C170 geralmente estão vazios ou com CST 50-75
        # Vamos verificar se há valores de CST fora desse range
        has_valid_contrib_cst = False
        for record in self.records:
            if record.reg == "C170" and len(record.fields) > 32:
                cst_pis = record.fields[29] if len(record.fields) > 29 else ""
                cst_cofins = record.fields[32] if len(record.fields) > 32 else ""
                
                # Se tem CST de PIS/COFINS fora do range do SPED Fiscal, é SPED Contribuições
                if cst_pis and cst_pis not in ["", "50", "51", "52", "53", "54", "55", "56", "60", "61", "62", "63", "64", "65", "66", "67", "70", "71", "72", "73", "74", "75"]:
                    has_valid_contrib_cst = True
                    print(f"Encontrado CST PIS inválido: {cst_pis}")
                    break
                if cst_cofins and cst_cofins not in ["", "50", "51", "52", "53", "54", "55", "56", "60", "61", "62", "63", "64", "65", "66", "67", "70", "71", "72", "73", "74", "75"]:
                    has_valid_contrib_cst = True
                    print(f"Encontrado CST COFINS inválido: {cst_cofins}")
                    break
        
        # Imprime informações de depuração
        print(f"has_fiscal_blocks: {has_fiscal_blocks}")
        print(f"has_contrib_blocks: {has_contrib_blocks}")
        print(f"has_pis_cofins_blocks: {has_pis_cofins_blocks}")
        print(f"has_contrib_opening: {has_contrib_opening}")
        print(f"has_valid_contrib_cst: {has_valid_contrib_cst}")
        
        # Se não há blocos de contribuições ou registros de apuração de PIS/COFINS
        if not has_contrib_blocks and not has_pis_cofins_blocks and not has_contrib_opening and not has_valid_contrib_cst and has_fiscal_blocks:
            return "fiscal"
        elif has_fiscal_blocks and (has_contrib_blocks or has_pis_cofins_blocks or has_contrib_opening or has_valid_contrib_cst):
            return "both"
        elif has_contrib_blocks or has_pis_cofins_blocks or has_contrib_opening or has_valid_contrib_cst:
            return "contrib"
        else:
            return "unknown"