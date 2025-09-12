from .base import Rule, Issue
from core.services.validator import only_digits


class R101_CSTPISInvalido(Rule):
    id = "R101"
    description = "CST de PIS inválido para a operação"
    auto_fix = True
    
    def validate(self, record, context):
        if record.reg not in ["C170", "C190", "D190"]:
            return []
        
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 30:
            return []
        
        cst_pis = record.fields[29]  # Campo CST_PIS
        tp_op = record.fields[2]    # Tipo de operação
        
        # Regras específicas para CST de PIS
        valid_cst_entrada = ["50", "51", "52", "53", "54", "55", "56", "60", "61", "62", "63", "64", "65", "66", "67", "70", "71", "72", "73", "74", "75"]
        valid_cst_saida = ["01", "02", "03", "04", "05", "06", "07", "08", "09"]
        
        if tp_op == "0" and cst_pis not in valid_cst_entrada:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CST PIS {cst_pis} inválido para entrada",
                suggestion="Ajustar CST PIS para entrada"
            )]
        elif tp_op == "1" and cst_pis not in valid_cst_saida:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CST PIS {cst_pis} inválido para saída",
                suggestion="Ajustar CST PIS para saída"
            )]
        return []

class R102_CSTCOFINSInvalido(Rule):
    id = "R102"
    description = "CST de COFINS inválido para a operação"
    auto_fix = True
    
    def validate(self, record, context):
        if record.reg not in ["C170", "C190", "D190"]:
            return []
        
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 33:
            return []
        
        cst_cofins = record.fields[32]  # Campo CST_COFINS
        tp_op = record.fields[2]        # Tipo de operação
        
        # Regras específicas para CST de COFINS
        valid_cst_entrada = ["50", "51", "52", "53", "54", "55", "56", "60", "61", "62", "63", "64", "65", "66", "67", "70", "71", "72", "73", "74", "75"]
        valid_cst_saida = ["01", "02", "03", "04", "05", "06", "07", "08", "09"]
        
        if tp_op == "0" and cst_cofins not in valid_cst_entrada:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CST COFINS {cst_cofins} inválido para entrada",
                suggestion="Ajustar CST COFINS para entrada"
            )]
        elif tp_op == "1" and cst_cofins not in valid_cst_saida:
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CST COFINS {cst_cofins} inválido para saída",
                suggestion="Ajustar CST COFINS para saída"
            )]
        return []

class R103_CreditoPISDivergente(Rule):
    id = "R103"
    description = "Valor do crédito de PIS divergente da base × alíquota"
    auto_fix = True
    
    def validate(self, record, context):
        if record.reg != "M100":
            return []
        
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 8:
            return []
        
        try:
            vl_bc_pis = float(record.fields[5] or 0)
            aliq_pis = float(record.fields[6] or 0)
            vl_cred_pis = float(record.fields[7] or 0)
            
            calculated_cred = vl_bc_pis * (aliq_pis / 100)
            
            if abs(calculated_cred - vl_cred_pis) > 0.01:
                return [Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"Valor crédito PIS ({vl_cred_pis}) ≠ base × alíquota ({calculated_cred:.2f})",
                    suggestion="Ajustar valor do crédito"
                )]
        except (ValueError, IndexError):
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Valores inválidos no registro M100",
                suggestion="Verificar valores numéricos"
            )]
        
        return []

    def fix(self, record, context):
        if record.reg != "M100" or len(record.fields) < 8:
            return
        
        try:
            vl_bc_pis = float(record.fields[5] or 0)
            aliq_pis = float(record.fields[6] or 0)
            
            calculated_cred = vl_bc_pis * (aliq_pis / 100)
            record.fields[7] = f"{calculated_cred:.2f}"
        except (ValueError, IndexError):
            pass

class R104_CreditoCOFINSDivergente(Rule):
    id = "R104"
    description = "Valor do crédito de COFINS divergente da base × alíquota"
    auto_fix = True
    
    def validate(self, record, context):
        if record.reg != "M500":
            return []
        
        # Verifica se o registro tem campos suficientes
        if len(record.fields) < 8:
            return []
        
        try:
            vl_bc_cofins = float(record.fields[5] or 0)
            aliq_cofins = float(record.fields[6] or 0)
            vl_cred_cofins = float(record.fields[7] or 0)
            
            calculated_cred = vl_bc_cofins * (aliq_cofins / 100)
            
            if abs(calculated_cred - vl_cred_cofins) > 0.01:
                return [Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"Valor crédito COFINS ({vl_cred_cofins}) ≠ base × alíquota ({calculated_cred:.2f})",
                    suggestion="Ajustar valor do crédito"
                )]
        except (ValueError, IndexError):
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Valores inválidos no registro M500",
                suggestion="Verificar valores numéricos"
            )]
        
        return []

    def fix(self, record, context):
        if record.reg != "M500" or len(record.fields) < 8:
            return
        
        try:
            vl_bc_cofins = float(record.fields[5] or 0)
            aliq_cofins = float(record.fields[6] or 0)
            
            calculated_cred = vl_bc_cofins * (aliq_cofins / 100)
            record.fields[7] = f"{calculated_cred:.2f}"
        except (ValueError, IndexError):
            pass


class R105_AliquotaPISInvalida(Rule):
    id = "R105"
    description = "Alíquota de PIS fora do range permitido"
    auto_fix = True
    
    def validate(self, record, context):
        # Só aplica esta regra se o SPED for de contribuições
        if not hasattr(context, 'sped_type') or context.sped_type not in ["contrib", "both"]:
            return []
            
        if record.reg not in ["M100", "C170", "C190", "D190"]:
            return []
        
        # Determina o índice da alíquota conforme o registro
        if record.reg == "M100":
            aliq_index = 6
        elif record.reg == "C170":
            aliq_index = 30  # Posição 31 no layout (ALIQ_PIS)
        elif record.reg == "C190":
            aliq_index = 11
        elif record.reg == "D190":
            aliq_index = 11
        else:
            return []
        
        # Verifica se o registro tem campos suficientes
        if aliq_index >= len(record.fields):
            return []
        
        try:
            aliq_pis_str = record.fields[aliq_index] or "0"
            # Substitui vírgula por ponto para conversão
            aliq_pis_str = aliq_pis_str.replace(",", ".")
            aliq_pis = float(aliq_pis_str)
            
            # Alíquotas válidas para PIS: 0%, 0.65%, 1.65%
            valid_aliqs = [0, 0.65, 1.65]
            
            # Verifica se é um valor claramente errado
            if aliq_pis > 10:  # Qualquer valor acima de 10% é certamente errado para PIS
                return [Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"Alíquota PIS {aliq_pis}% claramente inválida",
                    suggestion="Verificar se valor está na posição correta"
                )]
            elif aliq_pis not in valid_aliqs:
                return [Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"Alíquota PIS {aliq_pis}% inválida",
                    suggestion="Ajustar alíquota para valor válido (0, 0.65 ou 1.65)"
                )]
        except (ValueError, IndexError):
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Alíquota PIS inválida",
                suggestion="Verificar valor numérico"
            )]
        
        return []

    
    def fix(self, record, context):
        # Só aplica esta regra se o SPED for de contribuições
        if not hasattr(context, 'sped_type') or context.sped_type not in ["contrib", "both"]:
            return
            
        if record.reg not in ["M100", "C170", "C190", "D190"]:
            return
        
        # Determina o índice da alíquota conforme o registro
        if record.reg == "M100":
            aliq_index = 6
        elif record.reg == "C170":
            aliq_index = 30
        elif record.reg == "C190":
            aliq_index = 11
        elif record.reg == "D190":
            aliq_index = 11
        else:
            return
        
        # Verifica se o registro tem campos suficientes
        if aliq_index >= len(record.fields):
            return
        
        try:
            aliq_pis_str = record.fields[aliq_index] or "0"
            # Substitui vírgula por ponto para conversão
            aliq_pis_str = aliq_pis_str.replace(",", ".")
            aliq_pis = float(aliq_pis_str)
            
            # Se a alíquota for inválida, ajusta para o valor mais próximo
            valid_aliqs = [0, 0.65, 1.65]
            if aliq_pis not in valid_aliqs:
                # Para valores muito altos (como 50%), assume que é um erro de posicionamento
                # e define como 0 (não tributado)
                if aliq_pis > 10:
                    record.fields[aliq_index] = "0"
                else:
                    # Encontra o valor mais próximo
                    closest = min(valid_aliqs, key=lambda x: abs(x - aliq_pis))
                    # Formata com vírgula como separador decimal
                    record.fields[aliq_index] = f"{closest:.2f}".replace(".", ",")
        except (ValueError, IndexError):
            pass


    


class R106_AliquotaCOFINSInvalida(Rule):
    id = "R106"
    description = "Alíquota de COFINS fora do range permitido"
    auto_fix = True
    
    def validate(self, record, context):
        if record.reg not in ["M500", "C170", "C190", "D190"]:
            return []
        
        # Determina o índice da alíquota conforme o registro
        if record.reg == "M500":
            aliq_index = 6
        elif record.reg == "C170":
            aliq_index = 33
        elif record.reg == "C190":
            aliq_index = 14
        elif record.reg == "D190":
            aliq_index = 14
        else:
            return []
        
        # Verifica se o registro tem campos suficientes
        if aliq_index >= len(record.fields):
            return []
        
        try:
            aliq_cofins = float(record.fields[aliq_index] or 0)
            
            # Alíquotas válidas para COFINS: 0%, 3%, 7.6%
            valid_aliqs = [0, 3, 7.6]
            
            if aliq_cofins not in valid_aliqs:
                return [Issue(
                    line_no=record.line_no,
                    reg=record.reg,
                    rule_id=self.id,
                    severity="error",
                    message=f"Alíquota COFINS {aliq_cofins}% inválida",
                    suggestion="Ajustar alíquota para valor válido"
                )]
        except (ValueError, IndexError):
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message="Alíquota COFINS inválida",
                suggestion="Verificar valor numérico"
            )]
        
        return []

    def fix(self, record, context):
        if record.reg not in ["M500", "C170", "C190", "D190"]:
            return
        
        # Determina o índice da alíquota conforme o registro
        if record.reg == "M500":
            aliq_index = 6
        elif record.reg == "C170":
            aliq_index = 33
        elif record.reg == "C190":
            aliq_index = 14
        elif record.reg == "D190":
            aliq_index = 14
        else:
            return
        
        # Verifica se o registro tem campos suficientes
        if aliq_index >= len(record.fields):
            return
        
        try:
            aliq_cofins = float(record.fields[aliq_index] or 0)
            
            # Se a alíquota for inválida, ajusta para o valor mais próximo
            valid_aliqs = [0, 3, 7.6]
            if aliq_cofins not in valid_aliqs:
                # Encontra o valor mais próximo
                closest = min(valid_aliqs, key=lambda x: abs(x - aliq_cofins))
                record.fields[aliq_index] = f"{closest}"
        except (ValueError, IndexError):
            pass

class R107_CFOPFormatoInvalido(Rule):
    id = "R107"
    description = "CFOP com formatação inválida"
    auto_fix = True
    
    def validate(self, record, context):
        if record.reg not in ["C100", "C170", "D100"]:
            return []
        
        # Determina o índice do CFOP conforme o registro
        if record.reg == "C100":
            cfop_index = 11
        elif record.reg == "C170":
            cfop_index = 9
        elif record.reg == "D100":
            cfop_index = 9
        else:
            return []
        
        # Verifica se o registro tem campos suficientes
        if cfop_index >= len(record.fields):
            return []
        
        cfop = record.fields[cfop_index]
        
        # Verifica se o CFOP contém caracteres não numéricos (exceto o primeiro dígito)
        if cfop and not cfop.isdigit():
            return [Issue(
                line_no=record.line_no,
                reg=record.reg,
                rule_id=self.id,
                severity="error",
                message=f"CFOP {cfop} com formatação inválida",
                suggestion="Remover caracteres não numéricos"
            )]
        return []
    



    def fix(self, record, context):
        if record.reg not in ["C100", "C170", "D100"]:
            return
        
        # Determina o índice do CFOP conforme o registro
        if record.reg == "C100":
            cfop_index = 11
        elif record.reg == "C170":
            cfop_index = 9
        elif record.reg == "D100":
            cfop_index = 9
        else:
            return
        
        # Verifica se o registro tem campos suficientes
        if cfop_index >= len(record.fields):
            return
        
        cfop = record.fields[cfop_index]
        if cfop:
            # Remove caracteres não numéricos
            clean_cfop = only_digits(cfop)
            if clean_cfop:
                record.fields[cfop_index] = clean_cfop