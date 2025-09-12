# apps/core/rules/basic_rules.py
from .base import Rule, Issue, Context, SPEDTypeIdentifier
from typing import List
import re
from datetime import datetime
from core.parsers import SpedParser

DIGITS = re.compile(r"\D+")

# Helpers

def only_digits(s: str) -> str:
    return DIGITS.sub("", s or "")

def parse_date(s: str, fmt: str = "%d%m%Y") -> datetime | None:
    try:
        return datetime.strptime(s, fmt)
    except Exception:
        return None

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
                suggestion="Manter apenas última ocorrência"
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
                message=f"Cadastro 0150 CNPJ {cnpj} não referenciado",
                suggestion="Remover cadastro órfão"
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
                message=f"IE {ie} com caracteres inválidos",
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
        if record.reg not in ["C100", "C500", "D100"]:
            return []
        
        key = record.fields[8]  # Chave do documento
        duplicates = [
            r for r in context.records
            if r.reg == record.reg and r.fields[8] == key and r != record
        ]
        
        if duplicates:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"Documento {key} duplicado",
                suggestion="Manter apenas última ocorrência"
            )]
        return []

    def fix(self, record, context):
        if record.reg not in ["C100", "C500", "D100"]:
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
        tp_op = record.fields[2]  # Tipo de operação
        
        # Regras simples de validação
        if tp_op == "0" and not cfop.startswith(("1", "2", "3")):  # Entrada
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CFOP {cfop} inválido para entrada",
                suggestion="Ajustar CFOP para entrada"
            )]
        elif tp_op == "1" and not cfop.startswith(("5", "6", "7")):  # Saída
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CFOP {cfop} inválido para saída",
                suggestion="Ajustar CFOP para saída"
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
    description = "Zera crédito de ICMS para Simples Nacional"
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
                message=f"Total débitos ({total}) ≠ soma documentos ({docs_sum})",
                suggestion="Ajustar total de débitos"
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



# 5. Regras Gerais
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
    description = "Corrige formatação de campos numéricos"
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
                        message=f"Campo {field_idx} com formato inválido: {value}",
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
                message=f"IE {ie_field} com caracteres inválidos",
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
                    message=f"CST PIS {cst_pis} inválido para SPED Fiscal",
                    suggestion="Ajustar para CST válido (50-75)"
                ))
            
            # Verifica CST de COFINS (campo 31)
            cst_cofins = record.fields[31] if len(record.fields) > 31 else ""
            if cst_cofins and cst_cofins not in ["", "50", "51", "52", "53", "54", "55", "56", "60", "61", "62", "63", "64", "65", "66", "67", "70", "71", "72", "73", "74", "75"]:
                issues.append(Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"CST COFINS {cst_cofins} inválido para SPED Fiscal",
                    suggestion="Ajustar para CST válido (50-75)"
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