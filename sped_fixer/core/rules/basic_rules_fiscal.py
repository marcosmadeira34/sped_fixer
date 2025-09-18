# apps/core/rules/basic_rules.py
from .base import Rule, Issue, Context, SPEDTypeIdentifier
from typing import List
import re
from datetime import datetime
from core.parsers import SpedParser
from difflib import SequenceMatcher

DIGITS = re.compile(r"\D+")

# Helpers

def only_digits(s: str) -> str:
    return DIGITS.sub("", s or "")

def parse_date(s: str, fmt: str = "%d%m%Y") -> datetime | None:
    try:
        return datetime.strptime(s, fmt)
    except Exception:
        return None
    

class Record:
    def __init__(self, line_no, reg, fields):
        self.line_no = line_no
        self.reg = reg
        self.fields = fields

    def __str__(self):
        return f"Registro {self.reg} (linha {self.line_no}): {self.fields}"
    
    def __repr__(self):
        return self.__str__()
    

class R001_HeaderObrigatorio(Rule):
    id = "R001"
    description = "Registro 0000 deve existir como primeira linha"
    def validate(self, record, context):
        issues = []
        if record.line_no == 1 and record.reg != "0000":
            issues.append(Issue(record.line_no, record.reg, self.id, "error", "Primeira linha não é 0000"))
        return issues

class R002_VersaoLayout(Rule):
    id = "R002"
    description = "Campo versão do layout no 0000 deve estar presente"
    def validate(self, record, context):
        if record.reg != "0000":
            return []
        issues = []
        if len(record.fields) < 1 or not record.fields[0].strip():
            issues.append(Issue(record.line_no, record.reg, self.id, "error", "Versão do layout ausente no 0000"))
        return issues


class R003_CNPJValido(Rule):
    id = "R003"
    description = "CNPJ no 0000 deve ter 14 dígitos"
    auto_fix = True
    
    def validate(self, record, context):
        if record.reg != "0000":
            return []
        
        issues = []
        if len(record.fields) < 7:  # Precisamos do campo CNPJ (índice 6)
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Registro 0000 incompleto (menos de 7 campos)",
                suggestion="Verificar estrutura do registro"
            ))
            return issues
        
        cnpj = record.fields[6]  # Campo CNPJ no registro 0000 (índice 6)
        digits = only_digits(cnpj)
        if len(digits) != 14:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CNPJ inválido: {cnpj}",
                suggestion="Normalizar p/14 dígitos"
            ))
        return issues

    def fix(self, record, context):
        if len(record.fields) < 7:  # Precisamos do campo CNPJ (índice 6)
            return
            
        digits = only_digits(record.fields[6])[:14]
        record.fields[6] = digits.zfill(14)


class R004_IEFormato(Rule):
    id = "R004"
    description = "IE deve conter somente dígitos (quando informado)"
    auto_fix = True
    
    def validate(self, record, context):
        if record.reg not in ("0000", "0100", "C100", "0150"):
            return []
        
        issues = []
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 1:
            return issues
            
        ie_index = 2  # Posição padrão da IE
        if record.reg == "0150":
            ie_index = 2  # Posição da IE no 0150
        elif record.reg == "0000":
            ie_index = 6  # Posição da IE no 0000
            
        if ie_index >= len(record.fields):
            return issues
            
        ie = record.fields[ie_index]
        if ie and not only_digits(ie).isdigit():
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="warn",
                message=f"IE {ie} com caracteres inválidos",
                suggestion="Remover não-dígitos"
            ))
        return issues
    
    def fix(self, record, context):
        if record.reg not in ("0000", "0100", "C100", "0150"):
            return
            
        ie_index = 2
        if record.reg == "0150":
            ie_index = 2
        elif record.reg == "0000":
            ie_index = 6
            
        if ie_index < len(record.fields) and record.fields[ie_index]:
            record.fields[ie_index] = only_digits(record.fields[ie_index])


class R005_DataAberturaFechamento(Rule):
    id = "R005"
    description = "Data de início <= data fim (0000)"
    
    def validate(self, record, context):
        if record.reg != "0000":
            return []
        
        issues = []
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 5:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Registro 0000 incompleto (menos de 5 campos)",
                suggestion="Verificar estrutura do registro"
            ))
            return issues
        
        di = parse_date(record.fields[3])
        df = parse_date(record.fields[4])
        if not di or not df:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Datas inválidas no 0000"
            ))
        elif di > df:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Data inicial maior que final"
            ))
        return issues


class R006_LinhasSemEspacos(Rule):
    id = "R006"
    description = "Campos não devem ter espaços em excesso"
    auto_fix = True
    def validate(self, record, context):
        issues = []
        for f in record.fields:
            if f != f.strip():
                issues.append(Issue(record.line_no, record.reg, self.id, "warn", "Espaços extras nos campos", suggestion="Aplicar strip"))
                break
        return issues
    def fix(self, record, context):
        record.fields = [f.strip() for f in record.fields]


class R007_DuplicateCNPJ(Rule):
    id = "R007"
    description = "Remove registros 0150 com CNPJ duplicado"
    auto_fix = True

    def validate(self, record, context):
        if record.reg != "0150":
            return []
        
        cnpj = only_digits(record.fields[1])  # Campo CNPJ
        duplicates = [r for r in context.records if 
                     r.reg == "0150" and 
                     only_digits(r.fields[1]) == cnpj and 
                     r != record]
        
        issues = []
        if duplicates:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CNPJ {cnpj} duplicado",
                suggestion="Manter apenas ultima ocorrencia"
            ))
        return issues

    def fix(self, record, context):
        cnpj = only_digits(record.fields[1])
        duplicates = [r for r in context.records if 
                     r.reg == "0150" and 
                     only_digits(r.fields[1]) == cnpj and 
                     r != record]
        
        # Remove todas as ocorrências menos a última
        for dup in duplicates:
            context.remove_record(dup)

#  Regras de Cadastro (0150, 0190, 0200)
class R008_OrphanedCadastro(Rule):
    id = "R008"
    description = "Remove cadastros 0150 sem referência em documentos"
    auto_fix = True

    def validate(self, record, context):
        if record.reg != "0150":
            return []
        
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 2:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Registro 0150 incompleto (menos de 2 campos)",
                suggestion="Verificar estrutura do registro"
            )]
        
        cnpj = only_digits(record.fields[1])
        referenced = False
        
        # Verifica referências em documentos
        for doc in context.records:
            if doc.reg in ["C100", "C500", "D100"]:
                # Verifica se o documento tem campos suficientes
                if len(doc.fields) < 10:
                    continue
                    
                if only_digits(doc.fields[9]) == cnpj:  # Campo CNPJ do documento
                    referenced = True
                    break
        
        issues = []
        if not referenced:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Cadastro 0150 CNPJ {cnpj} nao referenciado",
                suggestion="Remover cadastro orfao"
            ))
        return issues

    def fix(self, record, context):
        if record.reg != "0150" or len(record.fields) < 2:
            return
        
        cnpj = only_digits(record.fields[1])
        referenced = False
        
        for doc in context.records:
            if doc.reg in ["C100", "C500", "D100"]:
                if len(doc.fields) < 10:
                    continue
                    
                if only_digits(doc.fields[9]) == cnpj:
                    referenced = True
                    break
        
        if not referenced:
            context.remove_record(record)


class R009_InvalidIE(Rule):
    id = "R009"
    description = "IE deve conter somente dígitos (quando informado)"
    auto_fix = True

    def validate(self, record, context):
        if record.reg not in ["0150", "0190"]:
            return []
        
        # No registro 0150, o campo IE é o índice 6
        # No registro 0190, o campo IE é o índice 2
        ie_index = 6 if record.reg == "0150" else 2
        
        # Verifica se o registro tem campos suficientes
        if ie_index >= len(record.fields):
            return []
        
        ie = record.fields[ie_index]
        if ie and not only_digits(ie).isdigit():
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="warn",
                message=f"IE {ie} com caracteres invalidos",
                suggestion="Remover não dígitos"
            )]
        return []

    def fix(self, record, context):
        if record.reg not in ["0150", "0190"]:
            return
        
        # No registro 0150, o campo IE é o índice 6
        # No registro 0190, o campo IE é o índice 2
        ie_index = 6 if record.reg == "0150" else 2
        
        # Verifica se o registro tem campos suficientes
        if ie_index >= len(record.fields):
            return
        
        if record.fields[ie_index]:
            record.fields[ie_index] = only_digits(record.fields[ie_index])


# 2. Regras de Inventário (Bloco H)
class R013_InventoryItemWithoutProduct(Rule):
    id = "R013"
    description = "Remove itens de inventário sem cadastro no 0200"
    auto_fix = True

    def validate(self, record, context):
        if record.reg != "H020":
            return []
        
        cod_item = record.fields[1]  # Código do item
        product_exists = any(
            r.reg == "0200" and r.fields[1] == cod_item
            for r in context.records
        )
        
        if not product_exists:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Item {cod_item} sem cadastro no 0200",
                suggestion="Remover item ou criar cadastro"
            )]
        return []

    def fix(self, record, context):
        if record.reg != "H020":
            return
        
        cod_item = record.fields[1]
        product_exists = any(
            r.reg == "0200" and r.fields[1] == cod_item
            for r in context.records
        )
        
        if not product_exists:
            context.remove_record(record)


class R014_InventoryValueMismatch(Rule):
    id = "R014"
    description = "Ajusta valor total do inventário (H005)"
    auto_fix = True

    def validate(self, record, context):
        if record.reg != "H005":
            return []
        
        total = float(record.fields[1] or 0)
        items_sum = sum(
            float(r.fields[4] or 0)  # Valor total do item
            for r in context.records
            if r.reg == "H020"
        )
        
        if abs(total - items_sum) > 0.01:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Valor inventário ({total}) ≠ soma itens ({items_sum})",
                suggestion="Ajustar valor total"
            )]
        return []

    def fix(self, record, context):
        if record.reg != "H005":
            return
        
        items_sum = sum(
            float(r.fields[4] or 0)
            for r in context.records
            if r.reg == "H020"
        )
        record.fields[1] = f"{items_sum:.2f}"

# 3. Regras de Documentos Fiscais (Blocos C e D)
class R015_DuplicateDocument(Rule):
    id = "R015"
    description = "Remove documentos fiscais duplicados"
    auto_fix = True

    def validate(self, record, context):
        if record.reg not in ["C100", "C500"]:
            return []
        
        key = record.fields[8]  # Chave da Nota Fiscal Eletrônica
        duplicates = [
            r for r in context.records
            if r.reg == record.reg and r.fields[8] == key and r != record
        ]
        print(f"O campo chave do documento e {record.fields[8]}")
        
        if duplicates:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Documento {key} duplicado",
                suggestion="Manter apenas ultima ocorrencia"
            )]
        return []

    def fix(self, record, context):
        if record.reg not in ["C100", "C500"]:
            return
        
        key = record.fields[8]
        duplicates = [
            r for r in context.records
            if r.reg == record.reg and r.fields[8] == key and r != record
        ]
        
        for dup in duplicates:
            context.remove_record(dup)

class R017_InvalidCFOP(Rule):
    id = "R017"
    description = "Corrige CFOP incompatível com operação"
    auto_fix = True

    def validate(self, record, context):
        if record.reg not in ["C100", "C170", "D100"]:
            return []
        
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 3:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Registro {record.reg} incompleto (menos de 3 campos)",
                suggestion="Verificar estrutura do registro"
            )]
        
        cfop_field = 11 if record.reg == "C100" else 9
        if cfop_field >= len(record.fields):
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Registro {record.reg} incompleto (campo CFOP ausente)",
                suggestion="Verificar estrutura do registro"
            )]
        
        cfop = record.fields[cfop_field]
        tp_op = record.fields[2]  # Tipo de operação (campo 3 do sped)
        
        # Regras simples de validação
        if tp_op == "0" and not cfop.startswith(("1", "2", "3")):  # Entrada
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CFOP {cfop} invalido para entrada",
                suggestion="Ajustar CFOP para entrada"
            )]
        elif tp_op == "1" and not cfop.startswith(("5", "6", "7")):  # Saída
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CFOP {cfop} invalido para saida",
                suggestion="Ajustar CFOP para saida"
            )]
        return []

    def fix(self, record, context):
        if record.reg not in ["C100", "C170", "D100"]:
            return
        
        cfop_field = 11 if record.reg == "C100" else 9
        if cfop_field >= len(record.fields):
            return
            
        tp_op = record.fields[2]
        cfop = record.fields[cfop_field]
        
        if tp_op == "0" and not cfop.startswith(("1", "2", "3")):  # Entrada
            # Se o CFOP começa com 5, 6 ou 7 (de saída), substitui pelo correspondente de entrada
            if cfop.startswith("5"):
                record.fields[cfop_field] = "1" + cfop[1:]
            elif cfop.startswith("6"):
                record.fields[cfop_field] = "2" + cfop[1:]
            elif cfop.startswith("7"):
                record.fields[cfop_field] = "3" + cfop[1:]
        elif tp_op == "1" and not cfop.startswith(("5", "6", "7")):  # Saída
            # Se o CFOP começa com 1, 2 ou 3 (de entrada), substitui pelo correspondente de saída
            if cfop.startswith("1"):
                record.fields[cfop_field] = "5" + cfop[1:]
            elif cfop.startswith("2"):
                record.fields[cfop_field] = "6" + cfop[1:]
            elif cfop.startswith("3"):
                record.fields[cfop_field] = "7" + cfop[1:]


    def fix(self, record, context):
        if record.reg not in ["C100", "C170", "D100"]:
            return
        
        cfop_field = 11 if record.reg == "C100" else 9
        if cfop_field >= len(record.fields):
            return
            
        tp_op = record.fields[2]
        
        if tp_op == "0" and not record.fields[cfop_field].startswith("1"):
            record.fields[cfop_field] = "1" + record.fields[cfop_field][1:]
        elif tp_op == "1" and not record.fields[cfop_field].startswith("5"):
            record.fields[cfop_field] = "5" + record.fields[cfop_field][1:]

# 4. Regras de Apuração (Bloco E)
class R021_SimplesNacionalCredit(Rule):
    id = "R021"
    description = "Zera credito de ICMS para Simples Nacional"
    auto_fix = True

    def validate(self, record, context):
        if record.reg != "E110":
            return []
        
        # Verifica se o registro E110 tem campos suficientes
        if len(record.fields) < 6:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Registro E110 incompleto (menos de 6 campos)",
                suggestion="Verificar estrutura do registro"
            )]
        
        # Verifica se é empresa do Simples Nacional
        simples_nacional = False
        for r in context.records:
            if r.reg == "0000":
                # Verifica se o registro 0000 tem campos suficientes
                if len(r.fields) < 19:  # Verifica se tem pelo menos 19 campos (índice 18)
                    continue  # Pula registros 0000 incompletos
                
                if r.fields[18] == "1":  # Campo IND_ATIV
                    simples_nacional = True
                    break
        
        if simples_nacional and float(record.fields[5] or 0) > 0:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Crédito de ICMS para empresa do Simples Nacional",
                suggestion="Zerar valor do crédito"
            )]
        return []

    def fix(self, record, context):
        if record.reg != "E110":
            return
        
        # Verifica se o registro E110 tem campos suficientes
        if len(record.fields) < 6:
            return
        
        # Verifica se é empresa do Simples Nacional
        simples_nacional = False
        for r in context.records:
            if r.reg == "0000":
                # Verifica se o registro 0000 tem campos suficientes
                if len(r.fields) < 19:
                    continue
                
                if r.fields[18] == "1":  # Campo IND_ATIV
                    simples_nacional = True
                    break
        
        if simples_nacional:
            record.fields[5] = "0.00"  # Zera crédito

class R025_DebitTotalMismatch(Rule):
    id = "R025"
    description = "Ajusta total de débitos (E200) para coincidir com documentos"
    auto_fix = True

    def validate(self, record, context):
        if record.reg != "E200":
            return []
        
        # Verifica se o registro E200 tem campos suficientes
        if len(record.fields) < 3:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Registro E200 incompleto (menos de 3 campos)",
                suggestion="Verificar estrutura do registro"
            )]
        
        total = float(record.fields[2] or 0)
        docs_sum = 0
        
        for r in context.records:
            if r.reg in ["C100", "C500"]:
                # Verifica se o documento tem campos suficientes
                if len(r.fields) < 15:  # Precisamos do campo 14 (ICMS) e 2 (tipo de operação)
                    continue
                
                if r.fields[2] == "1":  # Saída
                    docs_sum += float(r.fields[14] or 0)  # Valor ICMS
        
        if abs(total - docs_sum) > 0.01:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Total debitos ({total}) diferente da soma dos documentos ({docs_sum})",
                suggestion="Ajustar total de debitos"
            )]
        return []

    def fix(self, record, context):
        if record.reg != "E200":
            return
        
        # Verifica se o registro E200 tem campos suficientes
        if len(record.fields) < 3:
            return
        
        docs_sum = 0
        for r in context.records:
            if r.reg in ["C100", "C500"]:
                # Verifica se o documento tem campos suficientes
                if len(r.fields) < 15:
                    continue
                
                if r.fields[2] == "1":  # Saída
                    docs_sum += float(r.fields[14] or 0)  # Valor ICMS
        
        record.fields[2] = f"{docs_sum:.2f}"


class R027_ExcessSpaces(Rule):
    id = "R027"
    description = "Remove espaços em excesso dos campos"
    auto_fix = True

    def validate(self, record, context):
        issues = []
        for i, field in enumerate(record.fields):
            if field != field.strip():
                issues.append(Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="warn",
                    message=f"Campo {i} com espaços extras",
                    suggestion="Aplicar strip"
                ))
        return issues

    def fix(self, record, context):
        record.fields = [f.strip() for f in record.fields]


class R028_NumericFormat(Rule):
    id = "R028"
    description = "Corrige formatacao de campos numericos"
    auto_fix = True

    def validate(self, record, context):
        issues = []
        numeric_fields = {
            "C100": [10, 11, 12, 13, 14],  # Campos numéricos
            "C170": [6, 7, 8, 9, 10],
            "H020": [2, 3, 4]
        }
        
        if record.reg in numeric_fields:
            for field_idx in numeric_fields[record.reg]:
                value = record.fields[field_idx]
                if value and not value.replace(".", "").replace(",", "").isdigit():
                    issues.append(Issue(
                        line_no=record.line_no,
                        reg=record.reg,
                        rule_id=self.id,
                        severity="error",
                        message=f"Campo {field_idx} com formato invalido: {value}",
                        suggestion="Converter para formato numérico"
                    ))
        return issues

    def fix(self, record, context):
        numeric_fields = {
            "C100": [10, 11, 12, 13, 14],
            "C170": [6, 7, 8, 9, 10],
            "H020": [2, 3, 4]
        }
        
        if record.reg in numeric_fields:
            for field_idx in numeric_fields[record.reg]:
                value = record.fields[field_idx]
                if value:
                    # Remove formatação e converte para número
                    clean_value = value.replace(".", "").replace(",", "")
                    if clean_value.isdigit():
                        record.fields[field_idx] = f"{int(clean_value)}.00"


class R031_EmptyBlocks(Rule):
    id = "R031"
    description = "Remove blocos sem movimento"
    auto_fix = True

    def validate(self, record, context):
        if record.reg not in ["C001", "D001", "H001"]:
            return []
        
        block = record.reg[0]  # C, D ou H
        has_movement = any(
            r.reg.startswith(block) and r.reg != record.reg
            for r in context.records
        )
        
        if not has_movement and record.fields[1] == "1":  # Indicador de movimento
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="warn",
                message=f"Bloco {block} sem movimento",
                suggestion="Remover bloco"
            )]
        return []

    def fix(self, record, context):
        if record.reg not in ["C001", "D001", "H001"]:
            return
        
        block = record.reg[0]
        has_movement = any(
            r.reg.startswith(block) and r.reg != record.reg
            for r in context.records
        )
        
        if not has_movement and record.fields[1] == "1":
            context.remove_record(record)


class R032_CNPJNameMismatch(Rule):
    id = "R032"
    description = "Corrige CNPJ quando campo contém nome em vez de número"
    auto_fix = True

    def validate(self, record, context):
        if record.reg != "0000":
            return []
        
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 7:  # Precisamos do campo CNPJ (índice 6)
            return []
        
        cnpj_field = record.fields[6]  # Campo CNPJ no registro 0000 (índice 6)
        
        # Verifica se o campo parece ser um nome (contém letras e espaços)
        if any(c.isalpha() for c in cnpj_field) and ' ' in cnpj_field:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CNPJ parece ser um nome: {cnpj_field}",
                suggestion="Remover nome ou verificar CNPJ correto"
            )]
        return []

    def fix(self, record, context):
        if record.reg != "0000" or len(record.fields) < 7:
            return
        
        cnpj_field = record.fields[6]  # Campo CNPJ no registro 0000 (índice 6)
        
        # Se o campo parece ser um nome, tenta extrair apenas dígitos
        if any(c.isalpha() for c in cnpj_field) and ' ' in cnpj_field:
            # Tenta extrair apenas dígitos
            digits = only_digits(cnpj_field)
            if len(digits) == 14:  # CNPJ completo
                record.fields[6] = digits
            elif len(digits) == 11:  # CPF completo
                record.fields[6] = digits
            elif not digits:  # Se não encontrou dígitos, deixa em branco
                record.fields[6] = ""
            else:  # Se encontrou alguns dígitos mas não suficientes
                # Completa com zeros à esquerda
                record.fields[6] = digits.zfill(14)

    
class R033_IENameMismatch(Rule):
    id = "R033"
    description = "Corrige IE quando campo contém nome em vez de número"
    auto_fix = True

    def validate(self, record, context):
        if record.reg not in ["0150", "0190"]:
            return []
        
        # No registro 0150, o campo IE é o índice 6
        # No registro 0190, o campo IE é o índice 2
        ie_index = 6 if record.reg == "0150" else 2
        
        # Verifica se o registro tem campos suficientes
        if ie_index >= len(record.fields):
            return []
        
        ie_field = record.fields[ie_index]
        
        # Verifica se o campo parece ser um nome (contém letras e espaços)
        if any(c.isalpha() for c in ie_field) and ' ' in ie_field:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="warn",
                message=f"IE {ie_field} com caracteres invalidos",
                suggestion="Remover nao degitos"
            )]
        return []

    def fix(self, record, context):
        if record.reg not in ["0150", "0190"]:
            return
        
        # No registro 0150, o campo IE é o índice 6
        # No registro 0190, o campo IE é o índice 2
        ie_index = 6 if record.reg == "0150" else 2
        
        # Verifica se o registro tem campos suficientes
        if ie_index >= len(record.fields):
            return []
        
        ie_field = record.fields[ie_index]
        
        # Se o campo parece ser um nome, limpa-o
        if any(c.isalpha() for c in ie_field) and ' ' in ie_field:
            # Tenta extrair apenas dígitos
            digits = only_digits(ie_field)
            if digits:  # Se encontrou dígitos
                record.fields[ie_index] = digits
            else:
                # Se não encontrou dígitos, deixa em branco
                record.fields[ie_index] = ""


class R034_CNPJVazio(Rule):
    id = "R034"
    description = "CNPJ vazio no registro 0000"
    auto_fix = False  # Não corrige automaticamente, requer intervenção manual
    
    def validate(self, record, context):
        if record.reg != "0000":
            return []
        
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 6:
            return []
        
        cnpj = record.fields[5]
        
        if not cnpj or cnpj.strip() == "":
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="CNPJ vazio no registro 0000",
                suggestion="Preencher CNPJ corretamente"
            )]
        return []
    

class R035_Registro0000Estrutura(Rule):
    id = "R035"
    description = "Corrige estrutura do registro 0000"
    auto_fix = True
    
    def validate(self, record, context):
        if record.reg != "0000":
            return []
        
        issues = []
        
        # Verifica se o registro tem mais campos que o esperado (15 campos)
        if len(record.fields) > 15:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Registro 0000 com {len(record.fields)} campos (deveria ter 15)",
                suggestion="Remover campos extras"
            ))
        
        return issues
    
    def fix(self, record, context):
        if record.reg != "0000":
            return
        
        # Se o registro tem mais campos que o esperado, remove os extras
        if len(record.fields) > 15:
            # Mantém apenas os 15 primeiros campos
            record.fields = record.fields[:15]


class R036_Registro0000CamposObrigatorios(Rule):
    id = "R036"
    description = "Verifica campos obrigatórios do registro 0000"
    auto_fix = False
    
    def validate(self, record, context):
        if record.reg != "0000":
            return []
        
        issues = []
        
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 15:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Registro 0000 incompleto ({len(record.fields)} campos, deveria ter 15)",
                suggestion="Completar campos obrigatórios"
            ))
            return issues
        
        # Verifica campos obrigatórios
        campos_obrigatorios = {
            1: "COD_VER",    # Campo 02 (índice 1)
            2: "COD_FIN",    # Campo 03 (índice 2)
            3: "DT_INI",     # Campo 04 (índice 3)
            4: "DT_FIN",     # Campo 05 (índice 4)
            5: "NOME",       # Campo 06 (índice 5)
            8: "UF",         # Campo 09 (índice 8)
            9: "IE",         # Campo 10 (índice 9)
            10: "COD_MUN",   # Campo 11 (índice 10)
            13: "IND_PERFIL", # Campo 14 (índice 13)
            14: "IND_ATIV"   # Campo 15 (índice 14)
        }
        
        for idx, nome_campo in campos_obrigatorios.items():
            if not record.fields[idx] or record.fields[idx].strip() == "":
                issues.append(Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"Campo obrigatório {nome_campo} vazio",
                    suggestion=f"Preencher campo {nome_campo}"
                ))
        
        # Verifica se CNPJ ou CPF foi informado (campos mutuamente excludentes)
        cnpj = record.fields[6]  # Campo 07 (índice 6)
        cpf = record.fields[7]   # Campo 08 (índice 7)
        
        if not cnpj and not cpf:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="CNPJ e CPF vazios",
                suggestion="Informar CNPJ ou CPF"
            ))
        
        if cnpj and cpf:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="CNPJ e CPF preenchidos (deve ser apenas um)",
                suggestion="Informar apenas CNPJ ou CPF"
            ))
        
        # Verifica se IND_ATIV está correto conforme o CNPJ/CPF
        ind_ativ = record.fields[14]  # Campo 15 (índice 14)
        
        if cpf and ind_ativ != "1":
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"IND_ATIV deve ser '1' quando CPF é informado (valor: {ind_ativ})",
                suggestion="Alterar IND_ATIV para '1'"
            ))
        
        # Verifica se IND_PERFIL é um valor válido
        ind_perfil = record.fields[13]  # Campo 14 (índice 13)
        if ind_perfil not in ["A", "B", "C"]:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"IND_PERFIL inválido: {ind_perfil} (deve ser A, B ou C)",
                suggestion="Corrigir IND_PERFIL para valor válido"
            ))
        
        # Verifica se COD_FIN é um valor válido
        cod_fin = record.fields[2]  # Campo 03 (índice 2)
        if cod_fin not in ["0", "1"]:
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"COD_FIN inválido: {cod_fin} (deve ser 0 ou 1)",
                suggestion="Corrigir COD_FIN para valor válido"
            ))
        
        return issues
    

class R110_ValoresPISCOFINSFiscal(Rule):
    id = "R110"
    description = "Verifica valores de PIS/COFINS no SPED Fiscal"
    auto_fix = True
    
    def validate(self, record, context):
        # Só aplica esta regra se o SPED for fiscal
        if not hasattr(context, 'sped_type') or context.sped_type not in ["fiscal", "both"]:
            return []
            
        if record.reg != "C170":
            return []
        
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 37:
            return []
        
        issues = []
        
        try:
            # Verifica CST de PIS (campo 25)
            cst_pis = record.fields[25] if len(record.fields) > 25 else ""
            if cst_pis and cst_pis not in ["", "50", "51", "52", "53", "54", "55", "56", "60", "61", "62", "63", "64", "65", "66", "67", "70", "71", "72", "73", "74", "75"]:
                issues.append(Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"CST PIS {cst_pis} invalido para SPED Fiscal",
                    suggestion="Ajustar para CST valido (50-75)"
                ))
            
            # Verifica CST de COFINS (campo 31)
            cst_cofins = record.fields[31] if len(record.fields) > 31 else ""
            if cst_cofins and cst_cofins not in ["", "50", "51", "52", "53", "54", "55", "56", "60", "61", "62", "63", "64", "65", "66", "67", "70", "71", "72", "73", "74", "75"]:
                issues.append(Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"CST COFINS {cst_cofins} invalido para SPED Fiscal",
                    suggestion="Ajustar para CST valido (50-75)"
                ))
            
            # Verifica se os valores de crédito estão preenchidos quando não deveriam
            vl_cred_pis = record.fields[30] if len(record.fields) > 30 else ""  # VL_PIS
            vl_cred_cofins = record.fields[36] if len(record.fields) > 36 else ""  # VL_COFINS
            
            # Se o CST de PIS indica não incidência, o valor do crédito deve ser zero
            if cst_pis in ["50", "51", "52", "53", "54", "55", "56"] and vl_cred_pis and float(vl_cred_pis.replace(",", ".")) != 0:
                issues.append(Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"Valor crédito PIS ({vl_cred_pis}) deve ser zero para CST {cst_pis}",
                    suggestion="Zerar valor do crédito"
                ))
            
            # Se o CST de COFINS indica não incidência, o valor do crédito deve ser zero
            if cst_cofins in ["50", "51", "52", "53", "54", "55", "56"] and vl_cred_cofins and float(vl_cred_cofins.replace(",", ".")) != 0:
                issues.append(Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"Valor crédito COFINS ({vl_cred_cofins}) deve ser zero para CST {cst_cofins}",
                    suggestion="Zerar valor do crédito"
                ))
                
        except (ValueError, IndexError):
            issues.append(Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Valores inválidos no registro C170",
                suggestion="Verificar valores numéricos"
            ))
        
        return issues

    def fix(self, record, context):
        # Só aplica esta regra se o SPED for fiscal
        if not hasattr(context, 'sped_type') or context.sped_type not in ["fiscal", "both"]:
            return
            
        if record.reg != "C170" or len(record.fields) < 37:
            return
        
        try:
            # Verifica CST de PIS (campo 25)
            cst_pis = record.fields[25] if len(record.fields) > 25 else ""
            if cst_pis and cst_pis not in ["", "50", "51", "52", "53", "54", "55", "56", "60", "61", "62", "63", "64", "65", "66", "67", "70", "71", "72", "73", "74", "75"]:
                # Se for um CST inválido, define como 50 (não incidência)
                record.fields[25] = "50"
            
            # Verifica CST de COFINS (campo 31)
            cst_cofins = record.fields[31] if len(record.fields) > 31 else ""
            if cst_cofins and cst_cofins not in ["", "50", "51", "52", "53", "54", "55", "56", "60", "61", "62", "63", "64", "65", "66", "67", "70", "71", "72", "73", "74", "75"]:
                # Se for um CST inválido, define como 50 (não incidência)
                record.fields[31] = "50"
            
            # Zera os valores de crédito quando o CST indica não incidência
            if cst_pis in ["50", "51", "52", "53", "54", "55", "56"] and len(record.fields) > 30:
                # Só zera se o valor for diferente de zero
                if record.fields[30] and float(record.fields[30].replace(",", ".")) != 0:
                    record.fields[30] = "0,00"
            
            if cst_cofins in ["50", "51", "52", "53", "54", "55", "56"] and len(record.fields) > 36:
                # Só zera se o valor for diferente de zero
                if record.fields[36] and float(record.fields[36].replace(",", ".")) != 0:
                    record.fields[36] = "0,00"
                
        except (ValueError, IndexError):
            pass


class RH001_OPENBLOCK(Rule):
    """
    Validação do Registro H001: Abertura do Bloco H
    """
    id = "RH001"
    description = "Validação do Registro H001: Abertura do Bloco H"
    auto_fix = True
    
    def validate(self, record, context):
        # Só aplica esta regra se o SPED for fiscal
        if not hasattr(context, 'sped_type') or context.sped_type not in ['fiscal', 'both']:
            return []
        
        # Verificar se o registro é H001
        if record.reg != "H001":
            return []
        
        # Verificar quantidade mínima de campos
        if len(record.fields) < 2:
            return [Issue(
                record.line_no, 
                record.reg, 
                self.id, 
                "error", 
                "Registro H001 com quantidade de campos inferior ao esperado",
                "O registro H001 deve ter pelo menos 2 campos"
            )]
        
        issues = []
        
        # Validar campo IND_MOV (posição 1)
        ind_mov = record.fields[1] if len(record.fields) > 1 else ""
        if ind_mov not in ["0", "1"]:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Valor invalido para IND_MOV: {ind_mov}",
                "O campo IND_MOV deve ser '0' (Bloco com dados) ou '1' (Bloco sem dados)"
            ))
        
        # Verificar obrigatoriedade de apresentar inventário em fevereiro
        # Obter informações do período do contexto
        dt_ini = ""
        dt_fin = ""
        
        # Procurar pelo registro 0000 no contexto
        for r in context.records:
            if r.reg == "0000" and len(r.fields) >= 5:
                dt_ini = r.fields[3]  # Campo DT_INI (índice 3)
                dt_fin = r.fields[4]  # Campo DT_FIN (índice 4)
                break
        
        if dt_ini and dt_fin:
            # Verificar se o período é fevereiro
            if dt_ini[4:6] == "02" and dt_fin[4:6] == "02":
                # Verificar se existe registro H005 com data de 31/12 do ano anterior
                has_h005_31_12 = False
                for r in context.records:
                    if r.reg == "H005" and len(r.fields) >= 5:
                        dt_inv = r.fields[1]  # Campo DT_INV (índice 1)
                        if dt_inv == f"3112{int(dt_ini[:4])-1:04d}" and r.fields[4] == "01":  # Campo MOT_INV (índice 4)
                            has_h005_31_12 = True
                            break
                
                if not has_h005_31_12:
                    issues.append(Issue(
                        record.line_no,
                        record.reg,
                        self.id,
                        "warning",
                        "Período de fevereiro não contém Registro H005 com data de 31/12 do ano anterior e MOT_INV=01",
                        "Incluir Registro H005 com DT_INV=3112AAAA (AAAA=ano anterior) e MOT_INV=01"
                    ))
        
        return issues
    
    def fix(self, record, context):
        """
        Corrige problemas no Registro H001
        """
        fixed_fields = record.fields.copy()
        
        # Corrigir IND_MOV inválido
        if len(fixed_fields) >= 2:
            # Se houver outros registros H além de H001 e H990, definir como 0
            has_other_h_records = any(
                r.reg.startswith("H") and r.reg not in ["H001", "H990"]
                for r in context.records
            )
            fixed_fields[1] = "0" if has_other_h_records else "1"
        
        return Record(
            line_no=record.line_no,
            reg=record.reg,
            fields=fixed_fields
        )

class RH005_TOTAL_IVENTORY(Rule):
    """
    Validação do Registro H005: Totais do Inventário
    """
    id = "RH005"
    description = "Validação do Registro H005: Totais do Inventário"
    auto_fix = True
    
    def validate(self, record, context):
        # Só aplica esta regra se o SPED for fiscal
        if not hasattr(context, 'sped_type') or context.sped_type not in ['fiscal', 'both']:
            return []
        
        # Verificar se o registro é H005
        if record.reg != "H005":
            return []
        
        # Verificar quantidade mínima de campos
        if len(record.fields) < 5:
            return [Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                "Registro H005 com quantidade de campos inferior ao esperado",
                "O registro H005 deve ter pelo menos 5 campos"
            )]
        
        issues = []
        
        # Validar campo DT_INV (posição 1)
        dt_inv = record.fields[1] if len(record.fields) > 1 else ""
        if not dt_inv.isdigit() or len(dt_inv) != 8:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para DT_INV: {dt_inv}",
                "O campo DT_INV deve ser uma data no formato ddmmaaaa"
            ))
        else:
            # Validar se DT_INV é menor ou igual a DT_FIN do registro 0000
            dt_fin = ""
            for r in context.records:
                if r.reg == "0000" and len(r.fields) >= 5:
                    dt_fin = r.fields[4]  # Campo DT_FIN (índice 4)
                    break
            
            if dt_fin and dt_inv > dt_fin:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Data do inventário ({dt_inv}) é maior que a data final do período ({dt_fin})",
                    "A data do inventário deve ser menor ou igual à data final do período"
                ))
            
            # Validar se inventário (MOT_INV=1) não é apresentado após o 2º mês subsequente
            if len(record.fields) >= 5 and record.fields[4] == "01":
                # Obter data de 2 meses após DT_INV
                inv_year = int(dt_inv[4:8])
                inv_month = int(dt_inv[2:4])
                inv_day = int(dt_inv[0:2])
                
                # Calcular 2 meses após
                if inv_month <= 10:
                    limit_month = inv_month + 2
                    limit_year = inv_year
                else:
                    limit_month = (inv_month + 2) % 12
                    limit_year = inv_year + 1
                
                # Obter data inicial do período
                dt_ini = ""
                for r in context.records:
                    if r.reg == "0000" and len(r.fields) >= 5:
                        dt_ini = r.fields[3]  # Campo DT_INI (índice 3)
                        break
                
                if dt_ini:
                    ini_year = int(dt_ini[4:8])
                    ini_month = int(dt_ini[2:4])
                    
                    # Verificar se o período é após o limite
                    if ini_year > limit_year or (ini_year == limit_year and ini_month > limit_month):
                        issues.append(Issue(
                            record.line_no,
                            record.reg,
                            self.id,
                            "error",
                            f"Inventário com MOT_INV=01 apresentado após o 2º mês subsequente à data do inventário",
                            "O inventário com MOT_INV=01 deve ser apresentado até o 2º mês subsequente à data do inventário"
                        ))
        
        # Validar campo VL_INV (posição 2)
        vl_inv = record.fields[2] if len(record.fields) > 2 else ""
        try:
            vl_inv_float = float(vl_inv.replace(",", "."))
            
            # Validar se VL_INV é igual à soma do campo VL_ITEM do registro H010
            soma_h010 = 0.0
            for r in context.records:
                if r.reg == "H010" and len(r.fields) >= 6:
                    vl_item = r.fields[5]  # Campo VL_ITEM (índice 5)
                    try:
                        soma_h010 += float(vl_item.replace(",", "."))
                    except ValueError:
                        pass
            
            if abs(vl_inv_float - soma_h010) > 0.01:  # Tolerância de 1 centavo
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Valor do inventário ({vl_inv}) é diferente da soma dos itens ({soma_h010:.2f})",
                    "O campo VL_INV deve ser igual à soma do campo VL_ITEM dos registros H010"
                ))
        except ValueError:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para VL_INV: {vl_inv}",
                "O campo VL_INV deve ser um valor numérico com 2 casas decimais"
            ))
        
        # Validar campo MOT_INV (posição 4)
        if len(record.fields) >= 5:
            mot_inv = record.fields[4]
            if mot_inv not in ["01", "02", "03", "04", "05", "06"]:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Valor invalido para MOT_INV: {mot_inv}",
                    "O campo MOT_INV deve ser '01', '02', '03', '04', '05' ou '06'"
                ))
            
            # Validar se MOT_INV=06, então deve ter H030
            if mot_inv == "06":
                # Verificar se existe H030 associado
                has_h030 = any(r.reg == "H030" for r in context.records)
                
                if not has_h030:
                    issues.append(Issue(
                        record.line_no,
                        record.reg,
                        self.id,
                        "error",
                        "Registro H005 com MOT_INV=06 não possui registro H030 associado",
                        "Incluir registro H030 para informações complementares de substituição tributária"
                    ))
        
        return issues
    
    def fix(self, record, context):
        """
        Corrige problemas no Registro H005
        """
        fixed_fields = record.fields.copy()
        
        # Corrigir VL_INV para corresponder à soma dos itens H010
        soma_h010 = 0.0
        for r in context.records:
            if r.reg == "H010" and len(r.fields) >= 6:
                vl_item = r.fields[5]  # Campo VL_ITEM (índice 5)
                try:
                    soma_h010 += float(vl_item.replace(",", "."))
                except ValueError:
                    pass
        
        if len(fixed_fields) >= 3:
            fixed_fields[2] = f"{soma_h010:.2f}".replace(".", ",")
        
        # Corrigir MOT_INV inválido
        if len(fixed_fields) >= 5:
            # Se não for possível determinar, usar "01" (fim do período)
            fixed_fields[4] = "01"
        
        return Record(
            line_no=record.line_no,
            reg=record.reg,
            fields=fixed_fields
        )

class RH010_IVENTORY(Rule):
    """
    Validação do Registro H010: Inventário
    """
    id = "RH010"
    description = "Validação do Registro H010: Inventário"
    auto_fix = True
    
    def validate(self, record, context):
        # Só aplica esta regra se o SPED for fiscal
        if not hasattr(context, 'sped_type') or context.sped_type not in ['fiscal', 'both']:
            return []
        
        # Verificar se o registro é H010
        if record.reg != "H010":
            return []
        
        # Verificar quantidade mínima de campos
        if len(record.fields) < 7:
            return [Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                "Registro H010 com quantidade de campos inferior ao esperado",
                "O registro H010 deve ter pelo menos 7 campos"
            )]
        
        issues = []
        
        # Validar campo COD_ITEM (posição 1)
        cod_item = record.fields[1] if len(record.fields) > 1 else ""
        if not cod_item:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                "Campo COD_ITEM não informado",
                "O campo COD_ITEM é obrigatório"
            ))
        else:
            # Validar se COD_ITEM existe no registro 0200
            cod_items_0200 = []
            for r in context.records:
                if r.reg == "0200" and len(r.fields) >= 2:
                    cod_items_0200.append(r.fields[1])  # Campo COD_ITEM (índice 1)
            
            if cod_item not in cod_items_0200:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Código do item {cod_item} não encontrado no registro 0200",
                    "Verificar se o código do item está cadastrado no registro 0200"
                ))
        
        # Validar campo UNID (posição 2)
        unid = record.fields[2] if len(record.fields) > 2 else ""
        if not unid:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                "Campo UNID não informado",
                "O campo UNID é obrigatório"
            ))
        else:
            # Validar se UNID existe no registro 0200
            unid_exists = False
            for r in context.records:
                if r.reg == "0200" and len(r.fields) >= 4 and r.fields[1] == cod_item and r.fields[3] == unid:
                    unid_exists = True
                    break
            
            if not unid_exists:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Unidade {unid} não encontrada para o item {cod_item} no registro 0200",
                    "Verificar se a unidade está cadastrada corretamente no registro 0200"
                ))
        
        # Validar campo QTD (posição 3)
        qtd = record.fields[3] if len(record.fields) > 3 else ""
        try:
            qtd_float = float(qtd.replace(",", "."))
            if qtd_float < 0:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Quantidade negativa: {qtd}",
                    "A quantidade deve ser maior ou igual a zero"
                ))
        except ValueError:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para QTD: {qtd}",
                "O campo QTD deve ser um valor numérico com 3 casas decimais"
            ))
        
        # Validar campo VL_UNIT (posição 4)
        vl_unit = record.fields[4] if len(record.fields) > 4 else ""
        try:
            vl_unit_float = float(vl_unit.replace(",", "."))
            if vl_unit_float < 0:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Valor unitário negativo: {vl_unit}",
                    "O valor unitário deve ser maior ou igual a zero"
                ))
        except ValueError:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para VL_UNIT: {vl_unit}",
                "O campo VL_UNIT deve ser um valor numérico com 6 casas decimais"
            ))
        
        # Validar campo VL_ITEM (posição 5)
        vl_item = record.fields[5] if len(record.fields) > 5 else ""
        try:
            vl_item_float = float(vl_item.replace(",", "."))
            if vl_item_float < 0:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Valor do item negativo: {vl_item}",
                    "O valor do item deve ser maior ou igual a zero"
                ))
        except ValueError:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para VL_ITEM: {vl_item}",
                "O campo VL_ITEM deve ser um valor numérico com 2 casas decimais"
            ))
        
        # Validar campo IND_PROP (posição 6)
        if len(record.fields) >= 7:
            ind_prop = record.fields[6]
            if ind_prop not in ["0", "1", "2"]:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Valor invalido para IND_PROP: {ind_prop}",
                    "O campo IND_PROP deve ser '0', '1' ou '2'"
                ))
            
            # Validar se IND_PROP = 1 ou 2, então COD_PART é obrigatório
            if ind_prop in ["1", "2"]:
                if len(record.fields) < 8 or not record.fields[7]:
                    issues.append(Issue(
                        record.line_no,
                        record.reg,
                        self.id,
                        "error",
                        "Campo COD_PART não informado para IND_PROP=1 ou 2",
                        "O campo COD_PART é obrigatório quando IND_PROP é '1' ou '2'"
                    ))
                else:
                    # Validar se COD_PART existe no registro 0150
                    cod_part = record.fields[7]
                    cod_parts_0150 = []
                    for r in context.records:
                        if r.reg == "0150" and len(r.fields) >= 3:
                            cod_parts_0150.append(r.fields[2])  # Campo COD_PART (índice 2)
                    
                    if cod_part not in cod_parts_0150:
                        issues.append(Issue(
                            record.line_no,
                            record.reg,
                            self.id,
                            "error",
                            f"Código do participante {cod_part} não encontrado no registro 0150",
                            "Verificar se o código do participante está cadastrado no registro 0150"
                        ))
        
        return issues
    
    def fix(self, record, context):
        """
        Corrige problemas no Registro H010
        """
        fixed_fields = record.fields.copy()
        
        # Corrigir quantidade negativa
        if len(fixed_fields) >= 4:
            try:
                qtd_float = float(fixed_fields[3].replace(",", "."))
                if qtd_float < 0:
                    fixed_fields[3] = f"{abs(qtd_float):.3f}".replace(".", ",")
            except ValueError:
                fixed_fields[3] = "0,000"
        
        # Corrigir valor unitário negativo
        if len(fixed_fields) >= 5:
            try:
                vl_unit_float = float(fixed_fields[4].replace(",", "."))
                if vl_unit_float < 0:
                    fixed_fields[4] = f"{abs(vl_unit_float):.6f}".replace(".", ",")
            except ValueError:
                fixed_fields[4] = "0,000000"
        
        # Corrigir valor do item negativo
        if len(fixed_fields) >= 6:
            try:
                vl_item_float = float(fixed_fields[5].replace(",", "."))
                if vl_item_float < 0:
                    fixed_fields[5] = f"{abs(vl_item_float):.2f}".replace(".", ",")
            except ValueError:
                fixed_fields[5] = "0,00"
        
        # Corrigir IND_PROP inválido
        if len(fixed_fields) >= 7:
            # Se não for possível determinar, usar "0" (propriedade do informante)
            fixed_fields[6] = "0"
        
        return Record(
            line_no=record.line_no,
            reg=record.reg,
            fields=fixed_fields
        )

class RH020_INFO_COMPLEMENTAR_IVENTORY(Rule):
    """
    Validação do Registro H020: Informação Complementar do Inventário
    """
    id = "RH020"
    description = "Validação do Registro H020: Informação Complementar do Inventário"
    auto_fix = True
    
    def validate(self, record, context):
        # Só aplica esta regra se o SPED for fiscal
        if not hasattr(context, 'sped_type') or context.sped_type not in ['fiscal', 'both']:
            return []
        
        # Verificar se o registro é H020
        if record.reg != "H020":
            return []
        
        # Verificar quantidade mínima de campos
        if len(record.fields) < 5:
            return [Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                "Registro H020 com quantidade de campos inferior ao esperado",
                "O registro H020 deve ter pelo menos 5 campos"
            )]
        
        issues = []
        
        # Validar campo CST_ICMS (posição 1)
        cst_icms = record.fields[1] if len(record.fields) > 1 else ""
        if not cst_icms.isdigit() or len(cst_icms) != 3:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para CST_ICMS: {cst_icms}",
                "O campo CST_ICMS deve ser um código numérico de 3 dígitos"
            ))
        
        # Validar campo BC_ICMS (posição 2)
        bc_icms = record.fields[2] if len(record.fields) > 2 else ""
        try:
            bc_icms_float = float(bc_icms.replace(",", "."))
            if bc_icms_float < 0:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Base de cálculo do ICMS negativa: {bc_icms}",
                    "A base de cálculo do ICMS deve ser maior ou igual a zero"
                ))
        except ValueError:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para BC_ICMS: {bc_icms}",
                "O campo BC_ICMS deve ser um valor numérico com 2 casas decimais"
            ))
        
        # Validar campo VL_ICMS (posição 3)
        vl_icms = record.fields[3] if len(record.fields) > 3 else ""
        try:
            vl_icms_float = float(vl_icms.replace(",", "."))
            if vl_icms_float < 0:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Valor do ICMS negativo: {vl_icms}",
                    "O valor do ICMS deve ser maior ou igual a zero"
                ))
        except ValueError:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para VL_ICMS: {vl_icms}",
                "O campo VL_ICMS deve ser um valor numérico com 2 casas decimais"
            ))
        
        return issues
    
    def fix(self, record, context):
        """
        Corrige problemas no Registro H020
        """
        fixed_fields = record.fields.copy()
        
        # Corrigir base de cálculo do ICMS negativa
        if len(fixed_fields) >= 3:
            try:
                bc_icms_float = float(fixed_fields[2].replace(",", "."))
                if bc_icms_float < 0:
                    fixed_fields[2] = f"{abs(bc_icms_float):.2f}".replace(".", ",")
            except ValueError:
                fixed_fields[2] = "0,00"
        
        # Corrigir valor do ICMS negativo
        if len(fixed_fields) >= 4:
            try:
                vl_icms_float = float(fixed_fields[3].replace(",", "."))
                if vl_icms_float < 0:
                    fixed_fields[3] = f"{abs(vl_icms_float):.2f}".replace(".", ",")
            except ValueError:
                fixed_fields[3] = "0,00"
        
        return Record(
            line_no=record.line_no,
            reg=record.reg,
            fields=fixed_fields
        )

class RH030_INFO_COMPLEMENTAR_IVENTORY_ST(Rule):
    """
    Validação do Registro H030: Informações Complementares do Inventário das Mercadorias Sujeitas ao Regime de Substituição Tributária
    """
    id = "RH030"
    description = "Validação do Registro H030: Informações Complementares do Inventário das Mercadorias Sujeitas ao Regime de Substituição Tributária"
    auto_fix = True
    
    def validate(self, record, context):
        # Só aplica esta regra se o SPED for fiscal
        if not hasattr(context, 'sped_type') or context.sped_type not in ['fiscal', 'both']:
            return []
        
        # Verificar se o registro é H030
        if record.reg != "H030":
            return []
        
        # Verificar quantidade mínima de campos
        if len(record.fields) < 6:
            return [Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                "Registro H030 com quantidade de campos inferior ao esperado",
                "O registro H030 deve ter pelo menos 6 campos"
            )]
        
        issues = []
        
        # Validar campo VL_ICMS_OP (posição 1)
        vl_icms_op = record.fields[1] if len(record.fields) > 1 else ""
        try:
            vl_icms_op_float = float(vl_icms_op.replace(",", "."))
            if vl_icms_op_float < 0:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Valor do ICMS OP negativo: {vl_icms_op}",
                    "O valor do ICMS OP deve ser maior ou igual a zero"
                ))
        except ValueError:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para VL_ICMS_OP: {vl_icms_op}",
                "O campo VL_ICMS_OP deve ser um valor numérico com 6 casas decimais"
            ))
        
        # Validar campo VL_BC_ICMS_ST (posição 2)
        vl_bc_icms_st = record.fields[2] if len(record.fields) > 2 else ""
        try:
            vl_bc_icms_st_float = float(vl_bc_icms_st.replace(",", "."))
            if vl_bc_icms_st_float < 0:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Valor da base de cálculo do ICMS ST negativo: {vl_bc_icms_st}",
                    "O valor da base de cálculo do ICMS ST deve ser maior ou igual a zero"
                ))
        except ValueError:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para VL_BC_ICMS_ST: {vl_bc_icms_st}",
                "O campo VL_BC_ICMS_ST deve ser um valor numérico com 6 casas decimais"
            ))
        
        # Validar campo VL_ICMS_ST (posição 3)
        vl_icms_st = record.fields[3] if len(record.fields) > 3 else ""
        try:
            vl_icms_st_float = float(vl_icms_st.replace(",", "."))
            if vl_icms_st_float < 0:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Valor do ICMS ST negativo: {vl_icms_st}",
                    "O valor do ICMS ST deve ser maior ou igual a zero"
                ))
        except ValueError:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para VL_ICMS_ST: {vl_icms_st}",
                "O campo VL_ICMS_ST deve ser um valor numérico com 6 casas decimais"
            ))
        
        # Validar campo VL_FCP (posição 4)
        if len(record.fields) >= 5:
            vl_fcp = record.fields[4]
            try:
                vl_fcp_float = float(vl_fcp.replace(",", "."))
                if vl_fcp_float < 0:
                    issues.append(Issue(
                        record.line_no,
                        record.reg,
                        self.id,
                        "error",
                        f"Valor do FCP negativo: {vl_fcp}",
                        "O valor do FCP deve ser maior ou igual a zero"
                    ))
            except ValueError:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Formato invalido para VL_FCP: {vl_fcp}",
                    "O campo VL_FCP deve ser um valor numérico com 6 casas decimais"
                ))
        
        return issues
    
    def fix(self, record, context):
        """
        Corrige problemas no Registro H030
        """
        fixed_fields = record.fields.copy()
        
        # Corrigir valor do ICMS OP negativo
        if len(fixed_fields) >= 2:
            try:
                vl_icms_op_float = float(fixed_fields[1].replace(",", "."))
                if vl_icms_op_float < 0:
                    fixed_fields[1] = f"{abs(vl_icms_op_float):.6f}".replace(".", ",")
            except ValueError:
                fixed_fields[1] = "0,000000"
        
        # Corrigir valor da base de cálculo do ICMS ST negativo
        if len(fixed_fields) >= 3:
            try:
                vl_bc_icms_st_float = float(fixed_fields[2].replace(",", "."))
                if vl_bc_icms_st_float < 0:
                    fixed_fields[2] = f"{abs(vl_bc_icms_st_float):.6f}".replace(".", ",")
            except ValueError:
                fixed_fields[2] = "0,000000"
        
        # Corrigir valor do ICMS ST negativo
        if len(fixed_fields) >= 4:
            try:
                vl_icms_st_float = float(fixed_fields[3].replace(",", "."))
                if vl_icms_st_float < 0:
                    fixed_fields[3] = f"{abs(vl_icms_st_float):.6f}".replace(".", ",")
            except ValueError:
                fixed_fields[3] = "0,000000"
        
        # Corrigir valor do FCP negativo
        if len(fixed_fields) >= 5:
            try:
                vl_fcp_float = float(fixed_fields[4].replace(",", "."))
                if vl_fcp_float < 0:
                    fixed_fields[4] = f"{abs(vl_fcp_float):.6f}".replace(".", ",")
            except ValueError:
                fixed_fields[4] = "0,000000"
        
        return Record(
            line_no=record.line_no,
            reg=record.reg,
            fields=fixed_fields
        )

class RH990_END_BLOCK_H(Rule):
    """
    Validação do Registro H990: Encerramento do Bloco H
    """
    id = "RH990"
    description = "Validação do Registro H990: Encerramento do Bloco H"
    auto_fix = True
    
    def validate(self, record, context):
        # Só aplica esta regra se o SPED for fiscal
        if not hasattr(context, 'sped_type') or context.sped_type not in ['fiscal', 'both']:
            return []
        
        # Verificar se o registro é H990
        if record.reg != "H990":
            return []
        
        # Verificar quantidade mínima de campos
        if len(record.fields) < 2:
            return [Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                "Registro H990 com quantidade de campos inferior ao esperado",
                "O registro H990 deve ter pelo menos 2 campos"
            )]
        
        issues = []
        
        # Validar campo QTD_LIN_H (posição 1)
        qtd_lin_h = record.fields[1] if len(record.fields) > 1 else ""
        try:
            qtd_lin_h_int = int(qtd_lin_h)
            
            # Contar registros do Bloco H no contexto
            count_h = sum(1 for r in context.records if r.reg.startswith("H"))
            
            if qtd_lin_h_int != count_h:
                issues.append(Issue(
                    record.line_no,
                    record.reg,
                    self.id,
                    "error",
                    f"Quantidade de linhas do Bloco H ({qtd_lin_h_int}) não corresponde ao total de registros ({count_h})",
                    "O campo QTD_LIN_H deve refletir a quantidade total de registros do Bloco H"
                ))
        except ValueError:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                f"Formato invalido para QTD_LIN_H: {qtd_lin_h}",
                "O campo QTD_LIN_H deve ser um número inteiro"
            ))
        
        return issues
    
    def fix(self, record, context):
        """
        Corrige problemas no Registro H990
        """
        fixed_fields = record.fields.copy()
        
        # Corrigir QTD_LIN_H para corresponder ao total de registros
        count_h = sum(1 for r in context.records if r.reg.startswith("H"))
        
        if len(fixed_fields) >= 2:
            fixed_fields[1] = str(count_h)
        
        return Record(
            line_no=record.line_no,
            reg=record.reg,
            fields=fixed_fields
        )

class RHBLOCK_ALL_VALIDATION(Rule):
    """
    Validação do Bloco H como um todo
    """
    id = "RHBLOCK"
    description = "Validação do Bloco H como um todo"
    auto_fix = False  # Não há correção automática para problemas no bloco
    
    def validate(self, record, context):
        # Só aplica esta regra se o SPED for fiscal
        if not hasattr(context, 'sped_type') or context.sped_type not in ['fiscal', 'both']:
            return []
        
        # Esta regra é aplicada a todos os registros do Bloco H
        if not record.reg.startswith("H"):
            return []
        
        issues = []
        
        # Verificar se existe o registro H001
        h001_records = [r for r in context.records if r.reg == "H001"]
        if not h001_records:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                "Bloco H não possui registro H001",
                "Incluir registro H001 de abertura do Bloco H"
            ))
            return issues
        
        # Verificar se existe o registro H990
        h990_records = [r for r in context.records if r.reg == "H990"]
        if not h990_records:
            issues.append(Issue(
                record.line_no,
                record.reg,
                self.id,
                "error",
                "Bloco H não possui registro H990",
                "Incluir registro H990 de encerramento do Bloco H"
            ))
            return issues
        
        # Validar IND_MOV do registro H001
        if h001_records and len(h001_records[0].fields) >= 2:
            ind_mov = h001_records[0].fields[1]
            
            if ind_mov == "1":
                # Se IND_MOV = 1, então só pode ter H001 e H990
                total_records = sum(1 for r in context.records if r.reg.startswith("H"))
                
                if total_records > 2:
                    issues.append(Issue(
                        record.line_no,
                        record.reg,
                        self.id,
                        "error",
                        "Bloco H com IND_MOV=1 possui registros além de H001 e H990",
                        "Remover registros do Bloco H ou alterar IND_MOV para 0"
                    ))
            
            elif ind_mov == "0":
                # Se IND_MOV = 0, então deve ter pelo menos um registro além de H001 e H990
                total_records = sum(1 for r in context.records if r.reg.startswith("H"))
                
                if total_records <= 2:
                    issues.append(Issue(
                        record.line_no,
                        record.reg,
                        self.id,
                        "error",
                        "Bloco H com IND_MOV=0 não possui registros além de H001 e H990",
                        "Incluir registros do Bloco H ou alterar IND_MOV para 1"
                    ))
                
                # Verificar se existe pelo menos um registro H005
                h005_records = [r for r in context.records if r.reg == "H005"]
                if not h005_records:
                    issues.append(Issue(
                        record.line_no,
                        record.reg,
                        self.id,
                        "error",
                        "Bloco H com IND_MOV=0 não possui registro H005",
                        "Incluir registro H005 com informações do inventário"
                    ))
        
        # Verificar se existe pelo menos um registro H010 para cada H005 com VL_INV > 0
        h005_records = [r for r in context.records if r.reg == "H005"]
        h010_records = [r for r in context.records if r.reg == "H010"]
        
        for h005 in h005_records:
            if len(h005.fields) >= 3:
                vl_inv = h005.fields[2]
                try:
                    vl_inv_float = float(vl_inv.replace(",", "."))
                    if vl_inv_float > 0 and not h010_records:
                        issues.append(Issue(
                            record.line_no,
                            record.reg,
                            self.id,
                            "error",
                            "Registro H005 com VL_INV > 0 não possui registros H010 associados",
                            "Incluir registros H010 com detalhamento dos itens do inventário"
                        ))
                except ValueError:
                    pass
        
        return issues
    
    def fix(self, record, context):
        # Para problemas no bloco como um todo, não há correção automática simples
        # Retornar o registro original sem modificação
        return record


import re

class RC170_DuplicateDocument_C170(Rule):
    id = "RC170"
    description = "Remove itens duplicados no registro C170 considerando o documento pai (C100)"
    auto_fix = False

    # ---------- Helpers ----------
    def _ensure_parents(self, context):
        """Se parent não foi atribuído pelo parser, atribui o último C100 encontrado a cada C170."""
        last_c100 = None
        for r in context.records:
            if r.reg == "C100":
                last_c100 = r
            elif r.reg == "C170":
                if getattr(r, "parent", None) is None:
                    r.parent = last_c100

    def _normalize_number(self, s: str) -> str:
        """Normaliza formatos numéricos: '1.234,56' -> '1234.56', '26,24' -> '26.24'."""
        if s is None:
            return ""
        s = str(s).strip()
        if not s:
            return ""
        # Se tem ponto e vírgula assume ponto = milhar, vírgula = decimal
        if "." in s and "," in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        # else mantém ponto como decimal
        return s

    def _find_item_code(self, rec):
        """Heurística para achar código do item no registro C170 (tenta índices comuns)."""
        # tenta índices típicos (2,3,4) — ajusta se parser incluir ou não campo vazio inicial
        candidates = []
        # se parser usa fields com 'C170' em index 0:
        for idx in (2, 3, 4, 5):
            try:
                val = rec.fields[idx]
            except Exception:
                continue
            if val and re.match(r'^[A-Za-z0-9\-\./]{3,}$', val):  # código razoável
                candidates.append((idx, val))
        # se encontrou, retorna o primeiro plausível
        if candidates:
            return candidates[0][1]
        # fallback simples: tente qualquer campo que pareça código (>=3 chars)
        for f in rec.fields:
            if f and len(f) >= 3 and not f.upper() in ("UN", "KG", "LT", "0"):
                if re.search(r'[A-Za-z0-9]', f):
                    return f
        return None

    def _find_value_field(self, rec):
        """Heurística para achar o campo valor do item dentro do C170 (procura número decimal)."""
        # procura a partir do índice 6 até 30 (onde tipicamente aparecem valores)
        for i in range(6, min(30, len(rec.fields))):
            f = rec.fields[i]
            if f is None:
                continue
            f = str(f).strip()
            if not f:
                continue
            # padrão numérico com vírgula ou ponto e possivelmente milhares
            if re.match(r'^\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?$', f):
                return f
        # fallback: procura em toda a linha
        for f in rec.fields:
            if f and re.match(r'^\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?$', str(f).strip()):
                return str(f).strip()
        return None

    def _doc_key_of(self, rec, context):
        """Retorna chave do documento C100 pai (campo 8) com segurança."""
        parent = getattr(rec, "parent", None)
        if parent and getattr(parent, "reg", None) == "C100":
            try:
                return parent.fields[8]
            except Exception:
                return None
        # se parent não existe, tenta encontrar C100 anterior no contexto
        try:
            idx = context.records.index(rec)
        except ValueError:
            idx = None
        if idx is not None:
            for r in reversed(context.records[:idx]):
                if r.reg == "C100":
                    try:
                        return r.fields[8]
                    except Exception:
                        return None
        return None

    def _unique_key_for(self, rec, context):
        """Cria chave composta: doc_key|item_code|item_value_normalizado"""
        doc_key = self._doc_key_of(rec, context)
        if not doc_key:
            return None

        item_code = None
        # tenta pegar item_code direto (se parser já garante índices comuns)
        try:
            # tenta índice 2 (comum quando fields[0]='C170')
            possible = rec.fields[2]
            if possible and len(str(possible).strip()) >= 2:
                item_code = possible
        except Exception:
            item_code = None

        if not item_code:
            item_code = self._find_item_code(rec)
        if not item_code:
            return None

        item_value = None
        # tenta índice 6 (algumas implementações)
        try:
            possible_val = rec.fields[6]
            if possible_val and re.match(r'^\d', str(possible_val).strip()):
                item_value = possible_val
        except Exception:
            item_value = None

        if not item_value:
            item_value = self._find_value_field(rec)
        if item_value is None:
            return None

        norm_value = self._normalize_number(item_value)
        return f"{str(doc_key).strip()}|{str(item_code).strip()}|{norm_value}"

    # ---------- Rule methods ----------
    def validate(self, record, context):
        """
        Valida UM registro. Retorna Issue se o registro for uma ocorrência duplicada
        (mantemos apenas a última ocorrência — registros anteriores são considerados duplicados).
        """
        # garante parents
        self._ensure_parents(context)

        if record.reg != "C170":
            return []

        unique = self._unique_key_for(record, context)
        if not unique:
            return []

        # encontra todas as ocorrências com essa chave (na ordem do arquivo)
        occurrences = [r for r in context.records if r.reg == "C170" and self._unique_key_for(r, context) == unique]
        if not occurrences or len(occurrences) == 1:
            return []

        # decide qual é a última ocorrência (por posição no context.records)
        def _pos(r):
            try:
                return context.records.index(r)
            except ValueError:
                return getattr(r, "line_no", -1)

        last = max(occurrences, key=_pos)
        # se o registro atual NÃO for o último => é duplicado (reportar)
        if record is not last:
            doc_key = self._doc_key_of(record, context)
            item_code = self._find_item_code(record) or record.fields[2] if len(record.fields) > 2 else "?"
            item_value = self._find_value_field(record) or (record.fields[6] if len(record.fields) > 6 else "?")
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Item duplicado na nota {doc_key}: codigo={item_code}, valor={item_value}",
                suggestion="Manter apenas ultima ocorrencia"
            )]
        return []

    def fix(self, record, context):
        """
        Remove todas as ocorrências duplicadas desta chave, mantendo apenas a última.
        Se chamado para qualquer registro da chave, irá remover os anteriores.
        """
        # garante parents
        self._ensure_parents(context)

        if record.reg != "C170":
            return

        unique = self._unique_key_for(record, context)
        if not unique:
            return

        occurrences = [r for r in list(context.records) if r.reg == "C170" and self._unique_key_for(r, context) == unique]
        if len(occurrences) <= 1:
            return

        # determina última ocorrência
        def _pos(r):
            try:
                return context.records.index(r)
            except ValueError:
                return getattr(r, "line_no", -1)
        last = max(occurrences, key=_pos)

        # remove todos exceto o último
        for r in occurrences:
            if r is last:
                continue
            try:
                context.remove_record(r)
            except Exception:
                # se remove_record não existir, tenta remover da lista diretamente
                if hasattr(context, "records") and isinstance(context.records, list):
                    try:
                        context.records.remove(r)
                    except ValueError:
                        pass

    # ---------- conveniência: processo "tudo-em-um" ----------
    def process_context(self, context):
        """
        Método único pra rodar: garante parents, detecta issues para todos os C170 e
        remove duplicados mantendo a última ocorrência. Retorna lista de Issue.
        Use assim:
            issues = RC170_DuplicateDocument_C170().process_context(context)
        """
        self._ensure_parents(context)
        issues = []
        # checar todas ocorrências e coletar issues
        for rec in list(context.records):  # cópia para segurança caso haja remoção
            issues.extend(self.validate(rec, context))

        # agora aplica remoção por grupos (manter última)
        groups = {}
        for r in list(context.records):
            if r.reg != "C170":
                continue
            key = self._unique_key_for(r, context)
            if not key:
                continue
            groups.setdefault(key, []).append(r)

        for key, group in groups.items():
            if len(group) <= 1:
                continue
            # achar o último
            def _pos(r):
                try:
                    return context.records.index(r)
                except ValueError:
                    return getattr(r, "line_no", -1)
            last = max(group, key=_pos)
            for r in group:
                if r is last:
                    continue
                try:
                    context.remove_record(r)
                except Exception:
                    if hasattr(context, "records") and isinstance(context.records, list):
                        try:
                            context.records.remove(r)
                        except ValueError:
                            pass

        return issues

class RC850_DupicateDocument_C850(Rule):
    id = "RC850"
    description = "Valida duplicidade e consistência dos registros C850 (filho de C800)"
    auto_fix = False

    # ---------- Helpers ----------
    def _ensure_parents(self, context):
        """Se parent não foi atribuído pelo parser, atribui o último C800 encontrado a cada C850."""
        last_c800 = None
        for r in context.records:
            if r.reg == "C800":
                last_c800 = r
            elif r.reg == "C850":
                if getattr(r, "parent", None) is None:
                    r.parent = last_c800

    def _normalize_number(self, s: str) -> float:
        """Normaliza número e retorna como float."""
        if not s:
            return 0.0
        s = str(s).strip()
        if "." in s and "," in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except Exception:
            return 0.0

    def _doc_key_of(self, rec, context):
        """Retorna a chave do documento pai (combinação NUM_CFE + NUM_SAT + DT_DOC)."""
        parent = getattr(rec, "parent", None)
        if parent and getattr(parent, "reg", None) == "C800":
            try:
                return f"{parent.fields[3]}|{parent.fields[4]}|{parent.fields[5]}"
            except Exception:
                return None
        return None

    def _unique_key_for(self, rec, context):
        """Cria chave única do C850: doc_key|CST|CFOP|ALIQ"""
        doc_key = self._doc_key_of(rec, context)
        if not doc_key:
            return None
        try:
            cst = rec.fields[1] or ""
            cfop = rec.fields[2] or ""
            aliq = rec.fields[3] or ""
        except Exception:
            return None
        return f"{doc_key}|{cst}|{cfop}|{aliq}"

    # ---------- Rule methods ----------
    def validate(self, record, context):
        """Valida um C850 contra duplicidade e regras do C800 pai."""
        self._ensure_parents(context)

        if record.reg != "C850":
            return []

        parent = getattr(record, "parent", None)
        if not parent or parent.reg != "C800":
            return []

        issues = []
        doc_key = self._doc_key_of(record, context)

        # Exceção: COD_SIT 02 ou 03 → não deve existir C850
        try:
            cod_sit = parent.fields[2]
        except Exception:
            cod_sit = None
        if cod_sit in ("02", "03"):
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"C800 cancelado (COD_SIT={cod_sit}) não pode possuir C850",
                suggestion="Remover C850 vinculado"
            )]

        # Detectar duplicidade (mesma chave composta)
        unique = self._unique_key_for(record, context)
        if not unique:
            return []

        occurrences = [r for r in context.records if r.reg == "C850" and self._unique_key_for(r, context) == unique]
        if len(occurrences) > 1:
            # última ocorrência sobrevive
            last = max(occurrences, key=lambda r: context.records.index(r))
            if record is not last:
                issues.append(Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"Duplicidade em {doc_key}: CST={record.fields[1]}, CFOP={record.fields[2]}, ALIQ={record.fields[3]}",
                    suggestion="Manter apenas última ocorrência"
                ))

        return issues

    def fix(self, record, context):
        """Remove duplicados de C850, mantendo apenas a última ocorrência."""
        self._ensure_parents(context)

        if record.reg != "C850":
            return

        unique = self._unique_key_for(record, context)
        if not unique:
            return

        occurrences = [r for r in list(context.records) if r.reg == "C850" and self._unique_key_for(r, context) == unique]
        if len(occurrences) <= 1:
            return

        last = max(occurrences, key=lambda r: context.records.index(r))
        for r in occurrences:
            if r is last:
                continue
            try:
                context.remove_record(r)
            except Exception:
                if hasattr(context, "records") and isinstance(context.records, list):
                    try:
                        context.records.remove(r)
                    except ValueError:
                        pass

    def process_context(self, context):
        """
        Valida todos os C850:
        - Remove duplicados
        - Checa exceções de COD_SIT
        - Valida somatórios com C800
        """
        self._ensure_parents(context)
        issues = []

        # Valida registro a registro
        for rec in list(context.records):
            issues.extend(self.validate(rec, context))

        # Verifica somatórios por C800
        for c800 in [r for r in context.records if r.reg == "C800"]:
            c850s = [r for r in context.records if r.reg == "C850" and getattr(r, "parent", None) is c800]

            if not c850s:
                continue

            soma_vl_opr = sum(self._normalize_number(r.fields[4]) for r in c850s if len(r.fields) > 4)
            soma_vl_bc_icms = sum(self._normalize_number(r.fields[5]) for r in c850s if len(r.fields) > 5)
            soma_vl_icms = sum(self._normalize_number(r.fields[6]) for r in c850s if len(r.fields) > 6)

            try:
                vl_cfe = self._normalize_number(c800.fields[6])
                vl_icms = self._normalize_number(c800.fields[8])
            except Exception:
                vl_cfe, vl_icms = 0.0, 0.0

            if round(soma_vl_opr, 2) != round(vl_cfe, 2):
                issues.append(Issue(
                    line_no=c800.line_no,
                    reg="C800",
                    rule_id=self.id,
                    severity="error",
                    message=f"Soma VL_OPR dos C850 ({soma_vl_opr}) difere do VL_CFE do C800 ({vl_cfe})",
                    suggestion="Ajustar valores"
                ))

            if round(soma_vl_icms, 2) != round(vl_icms, 2):
                issues.append(Issue(
                    line_no=c800.line_no,
                    reg="C800",
                    rule_id=self.id,
                    severity="error",
                    message=f"Soma VL_ICMS dos C850 ({soma_vl_icms}) difere do VL_ICMS do C800 ({vl_icms})",
                    suggestion="Ajustar valores"
                ))

        return issues


class TotalizadorBlocoC_vs_BlocoE(Rule):
    id = "R001"
    description = "Valida consistência entre totais do Bloco C e Bloco E"

    def to_float(self, value):
        if isinstance(value, str):
            return float(value.replace(",", "."))
        return float(value or 0)
    

    def validate(self, record, context):
        if record.reg != "E110":
            return []
        
        # Soma VL_ICMS de todos os C190 do Bloco C
        total_c190 = sum(
            self.to_float(r.fields[6])  # Campo VL_ICMS do C190
            for r in context.records
            if r.reg == "C190"
        )
        
        total_debits = self.to_float(record.fields[1])   # Campo VL_TOT_DEBITOS do E110
        total_credits = self.to_float(record.fields[5])
        # soma total de debitos mais créditos
        total_e110 = total_debits + total_credits  # Campo VL_TOT_C
        
        
        if abs(total_c190 - total_e110) > 0.01:  # Tolerância de centavos
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Divergência de ICMS: Bloco C (R$ {total_c190}) vs Bloco E (R$ {total_e110})",
                suggestion="Verificar registros C100/C170 com valores de ICMS divergentes"
            )]
        return []


class ConsistenciaC170_vs_C100(Rule):
    id = "R002"
    description = "Valida soma de itens (C170) vs total das mercadorias (C100) ou C190 se C170 não existir"

    def to_float(self, value):
        """Converte valores do SPED para float."""
        if isinstance(value, str):
            return float(value.replace(",", "."))
        return float(value or 0)

    def validate(self, record, context):
        if record.reg != "C100":
            return []

        # Procura registros C170 filhos
        c170_children = [
            r for r in context.records
            if r.reg == "C170" and getattr(r, "parent", None) == record
        ]

        if not c170_children:
            # Se não houver C170, não como validar
            return []
        
        vl_total_itens = sum(self.to_float(r.fields[6]) for r in c170_children)

        # Valor total das mercadorias no C100 (campo 16 = VL_MERC)
        vl_merc = self.to_float(record.fields[15])

        if abs(vl_total_itens - vl_merc) > 0.01:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Soma de itens (R$ {vl_total_itens}) diverge do total das mercadorias (R$ {vl_merc})",
                suggestion="Verificar itens C170 com valores incorretos"
            )]

        return []


class SPEDComparator:
    def __init__(self, records_a, records_b):
        self.records_a = records_a
        self.records_b = records_b

    def record_similarity(self, rec_a, rec_b):
        """Calcula similaridade entre dois registros (0 a 1)"""
        if rec_a.reg != rec_b.reg:
            return 0.0  # registros diferentes não são similares

        # Concatena os campos relevantes como string
        str_a = "|".join(rec_a.fields)
        str_b = "|".join(rec_b.fields)

        return SequenceMatcher(None, str_a, str_b).ratio()

    def compare(self):
        divergences = []
        matched_count = 0

        for rec_a in self.records_a:
            # Encontrar o registro mais parecido no arquivo B do mesmo tipo
            candidates = [r for r in self.records_b if r.reg == rec_a.reg]
            if not candidates:
                divergences.append((rec_a.line_no, rec_a.reg, "Não encontrado"))
                continue

            best_match = max(candidates, key=lambda r: self.record_similarity(rec_a, r))
            sim = self.record_similarity(rec_a, best_match)

            if sim < 0.95:  # threshold de 95% para considerar divergente
                divergences.append((rec_a.line_no, rec_a.reg, rec_a.fields, best_match.line_no, best_match.fields, sim))
            else:
                matched_count += 1

        total_records = len(self.records_a)
        similarity_percent = matched_count / total_records * 100

        return similarity_percent, divergences