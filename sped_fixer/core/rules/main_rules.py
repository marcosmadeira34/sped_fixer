# sped_fixer/core/rules/main_rules.py
from .basic_rules_fiscal import (
    R015_DuplicateDocument, RC170_DuplicateDocument_C170, 
    RC850_DupicateDocument_C850, TotalizadorBlocoC_vs_BlocoE,
    ConsistenciaC170_vs_C100, 
)

from .impact_analyzer import ImpactAnalyzer
from .base import Issue, Record, SpedFile, Context

# Classe Principal de Correção com todas as regras, tanto sped fiscal quanto contribuições
class SPEDAutoFixer:
    def __init__(self, file_path, sped_type='fiscal'):
        self.file_path = file_path
        self.sped_type = sped_type
        self.sped = self._load_spd(file_path)
        self.rules = self._get_rules_for_type()
        self.context = Context(records=self.sped.records)
        # Adiciona o tipo de SPED ao contexto
        self.context.sped_type = self.sped_type
        # Inicializa o analisador de impacto
        self.impact_analyzer = ImpactAnalyzer(self.context)
        # self.encoding = 'utf-8'  # Codificação padrão

    def _load_spd(self, file_path):
        """Carrega o arquivo SPED e retorna um objeto com os registros"""
        
        records = []
        
        with open(file_path, 'r', encoding="utf-8") as f:
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
        common_rules = []
        
        # Regras específicas para SPED Fiscal
        fiscal_rules = [
            R015_DuplicateDocument(),
            RC170_DuplicateDocument_C170(),
            RC850_DupicateDocument_C850(),
            TotalizadorBlocoC_vs_BlocoE(),
            ConsistenciaC170_vs_C100(),
        ]
        
        if self.sped_type == "fiscal":
            return fiscal_rules
        else:
            return []  # Fallback 
    
    def fix_all(self):
        issues = []
        
        # Primeira passada: validar todos os registros e coletar issues
        for rule in self.rules:
            for record in self.sped.records:
                try:
                    rule_issues = rule.validate(record, self.context)
                    if rule_issues:
                        # Para cada issue, analisar o impacto em cascata
                        for issue in rule_issues:
                            # Adiciona referência ao registro que causou a issue
                            issue.record = record
                            # Analisa o impacto em cascata
                            impacted_records = self.impact_analyzer.trace_impact(record)
                            issue.impacted_records = impacted_records
                            # Gera detalhes do impacto
                            issue.impact_details = self._generate_impact_details(issue, impacted_records)
                        
                        issues.extend(rule_issues)
                        
                        # Se a regra permite correção automática
                        if hasattr(rule, 'fix') and rule.auto_fix:
                            rule.fix(record, self.context)
                except Exception as e:
                    print(f"Erro ao aplicar regra {rule.id} no registro {record.reg} linha {record.line_no}: {str(e)}")
                    print(f"Campos do registro: {record.fields}")
                    raise
        
        # Segunda passada: analisar impactos cruzados entre blocos
        # cross_block_issues = self._analyze_cross_block_impacts()
        # issues.extend(cross_block_issues)
        
        return issues
    
    def _generate_impact_details(self, issue, impacted_records):
        """Gera detalhes legíveis do impacto para o contador"""
        details = []
        for record in impacted_records:
            if record.reg == "E110":
                details.append({
                    "bloco": "E",
                    "registro": "E110",
                    "impacto": "Apuração de ICMS/IPI",
                    "gravidade": "Crítico",
                    "mensagem": "Erro afeta o valor total de impostos a recolher"
                })
            elif record.reg == "C190":
                details.append({
                    "bloco": "C",
                    "registro": "C190",
                    "impacto": "Totalização por CST",
                    "gravidade": "Alto",
                    "mensagem": "Inconsistência nos totais por situação tributária"
                })
            elif record.reg == "H010":
                details.append({
                    "bloco": "H",
                    "registro": "H010",
                    "impacto": "Inventário",
                    "gravidade": "Médio",
                    "mensagem": "Erro afeta o controle de estoque"
                })
            elif record.reg == "C800":
                details.append({
                    "bloco": "C",
                    "registro": "C800",
                    "impacto": "Documentos Fiscais de Serviços",
                    "gravidade": "Alto",
                    "mensagem": "Duplicidade de documentos fiscais de serviços"
                })

            elif record.reg == "C850":
                details.append({
                    "bloco": "C",
                    "registro": "C850",
                    "impacto": "Documentos Fiscais",
                    "gravidade": "Alto",
                    "mensagem": "Duplicidade de documentos fiscais"
                })
            elif record.reg == "C170":
                details.append({
                    "bloco": "C",
                    "registro": "C170",
                    "impacto": "Itens do Documento Fiscal",
                    "gravidade": "Médio",
                    "mensagem": "Inconsistência nos itens do documento fiscal"
                })
            # Adicione outros registros e seus impactos conforme necessário
            

        return details
    
    def _analyze_cross_block_impacts(self):
        """Analisa impactos entre blocos diferentes"""
        issues = []
        
        # Verifica consistência entre totais dos blocos C e E
        total_c190 = sum(
            float(r.fields[5]) if len(r.fields) > 5 and r.fields[5] else 0
            for r in self.context.records if r.reg == "C190"
        )
        
        # Encontra o registro E110
        e110_records = [r for r in self.context.records if r.reg == "E110"]
        if e110_records:
            e110 = e110_records[0]
            total_e110 = float(e110.fields[7]) if len(e110.fields) > 7 and e110.fields[7] else 0
            
            if abs(total_c190 - total_e110) > 0.01:  # Tolerância de centavos
                issues.append(Issue(
                    line_no=e110.line_no,
                    reg="E110",
                    rule_id="CROSS_BLOCK_001",
                    severity="error",
                    message=f"Divergência entre totais do Bloco C (R$ {total_c190}) e Bloco E (R$ {total_e110})",
                    suggestion="Verificar registros C100/C170 com valores de ICMS divergentes",
                    impact_details=[{
                        "bloco": "E",
                        "registro": "E110",
                        "impacto": "Apuração de ICMS/IPI",
                        "gravidade": "Crítico",
                        "mensagem": "Divergência nos totais de ICMS entre blocos"
                    }]
                ))
        
        # Adicione outras análises de impacto cruzado conforme necessário
        
        return issues
    
    def get_impact_summary(self):
        """Retorna um resumo do impacto de todos os problemas encontrados"""
        issues = self.fix_all()
        
        # Conta problemas por severidade
        severity_count = {"error": 0, "warning": 0, "info": 0}
        blocos_afetados = set()
        
        for issue in issues:
            severity_count[issue.severity] = severity_count.get(issue.severity, 0) + 1
            if hasattr(issue, 'impact_details'):
                for detail in issue.impact_details:
                    blocos_afetados.add(detail["bloco"])
        
        # Estima valor do impacto (simplificado)
        valor_impacto = 0
        for issue in issues:
            if hasattr(issue, 'record') and issue.record.reg == "C100":
                try:
                    # Tenta obter o valor do ICMS do registro C100
                    vl_icms = float(issue.record.fields[13]) if len(issue.record.fields) > 13 else 0
                    valor_impacto += abs(vl_icms)
                except (ValueError, IndexError):
                    pass
        
        return {
            "total_problemas": len(issues),
            "por_severidade": severity_count,
            "blocos_afetados": list(blocos_afetados),
            "valor_impacto_estimado": valor_impacto,
            "recomendacao": "Priorizar correção de problemas no Bloco C para evitar erros na apuração"
        }
    
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

