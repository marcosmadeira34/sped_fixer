from .basic_rules_fiscal import (
    R001_HeaderObrigatorio,    R002_VersaoLayout,
    R003_CNPJValido,    R004_IEFormato,
    R005_DataAberturaFechamento,    R006_LinhasSemEspacos,
    R007_DuplicateCNPJ,    R008_OrphanedCadastro,
    R009_InvalidIE,    R013_InventoryItemWithoutProduct,
    R014_InventoryValueMismatch,    R015_DuplicateDocument,
    R017_InvalidCFOP,    R021_SimplesNacionalCredit,
    R025_DebitTotalMismatch,    R027_ExcessSpaces,
    R028_NumericFormat,    R031_EmptyBlocks,
    R032_CNPJNameMismatch,    R033_IENameMismatch,
    R034_CNPJVazio, R110_ValoresPISCOFINSFiscal,
    R035_Registro0000Estrutura, R036_Registro0000CamposObrigatorios,
    
)

from .basic_rules_contribuicoes import (
    R101_CSTPISInvalido, R102_CSTCOFINSInvalido,
    R103_CreditoPISDivergente, R104_CreditoCOFINSDivergente,
    R105_AliquotaPISInvalida, R106_AliquotaCOFINSInvalida,
    R107_CFOPFormatoInvalido
    
)

from .base import Issue, SPEDTypeIdentifier

# Classe Principal de Correção com todas as regras, tanto sped fiscal quanto contribuições
class SPEDAutoFixer:
    def __init__(self, file_path, sped_type='fiscal'):
        self.file_path = file_path
        self.sped_type = sped_type  # Agora recebido como parâmetro
        self.sped = self._load_spd(file_path)
        self.rules = self._get_rules_for_type()
        self.context = Context(records=self.sped.records)
        # Adiciona o tipo de SPED ao contexto
        self.context.sped_type = self.sped_type

    def _load_spd(self, file_path):
        """Carrega o arquivo SPED e retorna um objeto com os registros"""
        records = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Divide a linha pelos pipes
                fields = line.split('|')[1:-1]  # Remove primeiro e último elementos vazios
                
                # Verifica se o registro tem pelo menos o campo de tipo (reg)
                if len(fields) < 1:
                    continue  # Pula registros vazios ou inválidos
                
                # Cria objeto de registro
                record = Record(
                    line_no=line_num,
                    reg=fields[0],
                    fields=fields
                )
                records.append(record)
        
        return SpedFile(records=records)
    
    def _get_rules_for_type(self):
        # Regras comuns a ambos os tipos
        common_rules = [
            R007_DuplicateCNPJ(),
            R008_OrphanedCadastro(),
            R009_InvalidIE(),
            R027_ExcessSpaces(),
            R028_NumericFormat(),
            R031_EmptyBlocks(),
            R032_CNPJNameMismatch(),
            R033_IENameMismatch(),
            R034_CNPJVazio(),
            R035_Registro0000Estrutura(),
            R036_Registro0000CamposObrigatorios(),
            R107_CFOPFormatoInvalido()
        ]
        
        # Regras específicas para SPED Fiscal
        fiscal_rules = [
            R003_CNPJValido(),
            R005_DataAberturaFechamento(),
            R013_InventoryItemWithoutProduct(),
            R014_InventoryValueMismatch(),
            R015_DuplicateDocument(),
            R017_InvalidCFOP(),
            R021_SimplesNacionalCredit(),
            R025_DebitTotalMismatch(),
            R110_ValoresPISCOFINSFiscal()
        ]
        
        # Regras específicas para SPED Contribuições
        contrib_rules = [
            R101_CSTPISInvalido(),
            R102_CSTCOFINSInvalido(),
            R103_CreditoPISDivergente(),
            R104_CreditoCOFINSDivergente(),
            R105_AliquotaPISInvalida(),
            R106_AliquotaCOFINSInvalida()
        ]
        
        if self.sped_type == "fiscal":
            return common_rules + fiscal_rules
        elif self.sped_type == "contrib":
            return common_rules + contrib_rules
        elif self.sped_type == "both":
            return common_rules + fiscal_rules + contrib_rules
        else:
            return common_rules  # Fallback para regras básicas
    
    def fix_all(self):
        issues = []
        
        for rule in self.rules:
            for record in self.sped.records:
                try:
                    rule_issues = rule.validate(record, self.context)
                    issues.extend(rule_issues)
                    
                    if rule_issues and hasattr(rule, 'fix') and rule.auto_fix:
                        rule.fix(record, self.context)
                except Exception as e:
                    print(f"Erro ao aplicar regra {rule.id} no registro {record.reg} linha {record.line_no}: {str(e)}")
                    print(f"Campos do registro: {record.fields}")
                    raise
        
        return issues
    
    def get_corrected_content(self):
        """Retorna o conteúdo do arquivo corrigido como string"""
        lines = []
        for record in self.sped.records:
            # Formata cada registro como linha do SPED
            line = "|".join(record.fields) + "|"
            lines.append(line)
        
        return "\n".join(lines)
    
    def get_sped_type(self):
        """Retorna o tipo de SPED"""
        return self.sped_type


class Record:
    def __init__(self, line_no, reg, fields):
        self.line_no = line_no
        self.reg = reg
        self.fields = fields

class SpedFile:
    def __init__(self, records):
        self.records = records

class Context:
    def __init__(self, records):
        self.records = records

    def remove_record(self, record):
        """Remove um registro da lista"""
        if record in self.records:
            self.records.remove(record)
