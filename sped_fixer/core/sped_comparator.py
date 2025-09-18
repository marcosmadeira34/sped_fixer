# sped_fixer/core/sped_comparator.py
from typing import Dict, List, Any, TypedDict
import re

class ComparisonResult(TypedDict):
    """Resultado da comparação entre dois arquivos SPED"""
    summary: Dict[str, Any]
    differences: List[Dict[str, Any]]

class DifferenceType:
    """Tipos de Diferencas encontradas"""
    MISSING_RECORD = "missing_record"  # Registro faltante no auditado
    EXTRA_RECORD = "extra_record"      # Registro excedente no auditado
    VALUE_DIFFERENCE = "value_difference"  # Diferenca de valores
    QUANTITY_DIFFERENCE = "quantity_difference"  # Diferenca de quantidades
    FIELD_DIFFERENCE = "field_difference"  # Diferenca em campos específicos

class SPEDComparator:
    """
    Classe para comparar dois arquivos SPED e identificar Diferencas objetivas
    """
    
    def __init__(self):
        self.differences = []
        self.summary = {
            'total_records_ref': 0,
            'total_records_aud': 0,
            'missing_records': 0,
            'extra_records': 0,
            'value_differences': 0,
            'quantity_differences': 0,
            'field_differences': 0
        }
    
    def compare(self, ref_data: Dict[str, Any], aud_data: Dict[str, Any]) -> ComparisonResult:
        """
        Compara dois arquivos SPED e retorna as Diferencas encontradas
        
        Args:
            ref_data: Dados do arquivo de referência
            aud_data: Dados do arquivo auditado
            
        Returns:
            ComparisonResult com o resumo e as Diferencas encontradas
        """
        self.differences = []
        self._reset_summary()
        
        # Contar totais
        self._count_totals(ref_data, aud_data)
        
        # Comparar registros C100 (Notas Fiscais)
        self._compare_c100_records(ref_data.get('C100', []), aud_data.get('C100', []))
        
        # Comparar registros C170 (Itens das Notas Fiscais)
        self._compare_c170_records(ref_data.get('C170', []), aud_data.get('C170', []))
        
        # Comparar registros H010 (Inventário)
        self._compare_h010_records(ref_data.get('H010', []), aud_data.get('H010', []))
        
        # Comparar registros E200 (Apuração de ICMS)
        self._compare_e200_records(ref_data.get('E200', []), aud_data.get('E200', []))
        
        # Comparar totais dos blocos
        self._compare_block_totals(ref_data, aud_data)
        
        return {
            'summary': self.summary,
            'differences': self.differences
        }
    
    def _reset_summary(self):
        """Reseta o resumo das Diferencas"""
        self.summary = {
            'total_records_ref': 0,
            'total_records_aud': 0,
            'missing_records': 0,
            'extra_records': 0,
            'value_differences': 0,
            'quantity_differences': 0,
            'field_differences': 0
        }
    
    def _count_totals(self, ref_data: Dict[str, Any], aud_data: Dict[str, Any]):
        """Conta o total de registros em cada arquivo"""
        # Os dados já vêm organizados por tipo de registro
        for reg_type in ref_data:
            if reg_type in ['C100', 'C170', 'H010', 'E200']:
                self.summary['total_records_ref'] += len(ref_data[reg_type])
        
        for reg_type in aud_data:
            if reg_type in ['C100', 'C170', 'H010', 'E200']:
                self.summary['total_records_aud'] += len(aud_data[reg_type])
    
    def _compare_c100_records(self, ref_records: List[Any], aud_records: List[Any]):
        """Compara registros C100 (Notas Fiscais)"""
        # Criar dicionários com chaves únicas
        ref_dict = self._create_c100_dict(ref_records)
        aud_dict = self._create_c100_dict(aud_records)
        
        # Verificar registros faltantes no auditado
        for key, ref_record in ref_dict.items():
            if key not in aud_dict:
                self.differences.append({
                    'type': DifferenceType.MISSING_RECORD,
                    'record_type': 'C100',
                    'key': key,
                    'reference_data': {
                        'line_no': ref_record.line_no,
                        'cnpj': ref_record.fields[3] if len(ref_record.fields) > 3 else "",
                        'modelo': ref_record.fields[5] if len(ref_record.fields) > 5 else "",
                        'serie': ref_record.fields[6] if len(ref_record.fields) > 6 else "",
                        'numero': ref_record.fields[7] if len(ref_record.fields) > 7 else "",
                        'data': ref_record.fields[8] if len(ref_record.fields) > 8 else "",
                        'vl_doc': ref_record.fields[10] if len(ref_record.fields) > 10 else ""
                    },
                    'audit_data': None,
                    'severity': 'error',
                    'message': f'Nota fiscal não encontrada no arquivo auditado: {key}'
                })
                self.summary['missing_records'] += 1
        
        # Verificar registros excedentes no auditado
        for key, aud_record in aud_dict.items():
            if key not in ref_dict:
                self.differences.append({
                    'type': DifferenceType.EXTRA_RECORD,
                    'record_type': 'C100',
                    'key': key,
                    'reference_data': None,
                    'audit_data': {
                        'line_no': aud_record.line_no,
                        'cnpj': aud_record.fields[3] if len(aud_record.fields) > 3 else "",
                        'modelo': aud_record.fields[5] if len(aud_record.fields) > 5 else "",
                        'serie': aud_record.fields[6] if len(aud_record.fields) > 6 else "",
                        'numero': aud_record.fields[7] if len(aud_record.fields) > 7 else "",
                        'data': aud_record.fields[8] if len(aud_record.fields) > 8 else "",
                        'vl_doc': aud_record.fields[10] if len(aud_record.fields) > 10 else ""
                    },
                    'severity': 'warning',
                    'message': f'Nota fiscal excedente no arquivo auditado: {key}'
                })
                self.summary['extra_records'] += 1
        
        # Comparar valores em registros presentes em ambos os arquivos
        for key in set(ref_dict.keys()) & set(aud_dict.keys()):
            ref_record = ref_dict[key]
            aud_record = aud_dict[key]
            
            # Comparar valores monetários importantes
            value_fields = {
                10: 'VL_DOC',   # Valor do documento
                11: 'VL_ICMS',  # Valor do ICMS
                14: 'VL_IPI',   # Valor do IPI
                15: 'VL_PIS',   # Valor do PIS
                16: 'VL_COFINS' # Valor do COFINS
            }
            
            for field_idx, field_name in value_fields.items():
                if field_idx < len(ref_record.fields) and field_idx < len(aud_record.fields):
                    ref_value = self._parse_float(ref_record.fields[field_idx])
                    aud_value = self._parse_float(aud_record.fields[field_idx])
                    
                    if abs(ref_value - aud_value) > 0.01:  # Tolerância de 1 centavo
                        self.differences.append({
                            'type': DifferenceType.VALUE_DIFFERENCE,
                            'record_type': 'C100',
                            'key': key,
                            'field': field_name,
                            'reference_value': ref_value,
                            'audit_value': aud_value,
                            'difference': ref_value - aud_value,
                            'severity': 'error',
                            'message': f'Diferenca no valor do campo {field_name}: R$ {ref_value:.2f} vs R$ {aud_value:.2f}'
                        })
                        self.summary['value_differences'] += 1
    
    def _compare_c170_records(self, ref_records: List[Any], aud_records: List[Any]):
        """Compara registros C170 (Itens das Notas Fiscais)"""
        # Criar dicionários com chaves únicas
        ref_dict = self._create_c170_dict(ref_records)
        aud_dict = self._create_c170_dict(aud_records)
        
        # Detectar registros duplicados no auditado
        aud_duplicates = self._find_duplicates(aud_records)
        for duplicate in aud_duplicates:
            self.differences.append({
                'type': 'duplicate_record',
                'record_type': 'C170',
                'key': duplicate['key'],
                'reference_data': None,
                'audit_data': {
                    'line_no': duplicate['record'].line_no,
                    'cnpj': duplicate['record'].fields[3] if len(duplicate['record'].fields) > 3 else "",
                    'modelo': duplicate['record'].fields[5] if len(duplicate['record'].fields) > 5 else "",
                    'serie': duplicate['record'].fields[6] if len(duplicate['record'].fields) > 6 else "",
                    'numero': duplicate['record'].fields[7] if len(duplicate['record'].fields) > 7 else "",
                    'data': duplicate['record'].fields[8] if len(duplicate['record'].fields) > 8 else "",
                    'item': duplicate['record'].fields[2] if len(duplicate['record'].fields) > 2 else "",
                    'vl_item': duplicate['record'].fields[12] if len(duplicate['record'].fields) > 12 else ""
                },
                'severity': 'warning',
                'message': f'Registro C170 duplicado no arquivo auditado: {duplicate["key"]}',
                'duplicate_count': duplicate['count']
            })
            self.summary['extra_records'] += 1
        
        # Verificar itens faltantes no auditado
        for key, ref_record in ref_dict.items():
            if key not in aud_dict:
                self.differences.append({
                    'type': DifferenceType.MISSING_RECORD,
                    'record_type': 'C170',
                    'key': key,
                    'reference_data': {
                        'line_no': ref_record.line_no,
                        'cnpj': ref_record.fields[3] if len(ref_record.fields) > 3 else "",
                        'modelo': ref_record.fields[5] if len(ref_record.fields) > 5 else "",
                        'serie': ref_record.fields[6] if len(ref_record.fields) > 6 else "",
                        'numero': ref_record.fields[7] if len(ref_record.fields) > 7 else "",
                        'data': ref_record.fields[8] if len(ref_record.fields) > 8 else "",
                        'item': ref_record.fields[2] if len(ref_record.fields) > 2 else "",
                        'vl_item': ref_record.fields[12] if len(ref_record.fields) > 12 else ""
                    },
                    'audit_data': None,
                    'severity': 'error',
                    'message': f'Item de nota fiscal não encontrado no arquivo auditado: {key}'
                })
                self.summary['missing_records'] += 1
        
        # Verificar itens excedentes no auditado (que não são duplicados)
        for key, aud_record in aud_dict.items():
            if key not in ref_dict and not any(d['key'] == key for d in aud_duplicates):
                self.differences.append({
                    'type': DifferenceType.EXTRA_RECORD,
                    'record_type': 'C170',
                    'key': key,
                    'reference_data': None,
                    'audit_data': {
                        'line_no': aud_record.line_no,
                        'cnpj': aud_record.fields[3] if len(aud_record.fields) > 3 else "",
                        'modelo': aud_record.fields[5] if len(aud_record.fields) > 5 else "",
                        'serie': aud_record.fields[6] if len(aud_record.fields) > 6 else "",
                        'numero': aud_record.fields[7] if len(aud_record.fields) > 7 else "",
                        'data': aud_record.fields[8] if len(aud_record.fields) > 8 else "",
                        'item': aud_record.fields[2] if len(aud_record.fields) > 2 else "",
                        'vl_item': aud_record.fields[12] if len(aud_record.fields) > 12 else ""
                    },
                    'severity': 'warning',
                    'message': f'Item de nota fiscal excedente no arquivo auditado: {key}'
                })
                self.summary['extra_records'] += 1
        
        # Comparar valores em itens presentes em ambos os arquivos
        for key in set(ref_dict.keys()) & set(aud_dict.keys()):
            ref_record = ref_dict[key]
            aud_record = aud_dict[key]
            
            # Comparar quantidade
            if 4 < len(ref_record.fields) and 4 < len(aud_record.fields):
                ref_qtd = self._parse_float(ref_record.fields[4])
                aud_qtd = self._parse_float(aud_record.fields[4])
                
                if abs(ref_qtd - aud_qtd) > 0.001:  # Tolerância para quantidade
                    self.differences.append({
                        'type': DifferenceType.QUANTITY_DIFFERENCE,
                        'record_type': 'C170',
                        'key': key,
                        'field': 'QTD',
                        'reference_value': ref_qtd,
                        'audit_value': aud_qtd,
                        'difference': ref_qtd - aud_qtd,
                        'severity': 'error',
                        'message': f'Diferenca na quantidade do item: {ref_qtd} vs {aud_qtd}'
                    })
                    self.summary['quantity_differences'] += 1
            
            # Comparar valor unitário
            if 5 < len(ref_record.fields) and 5 < len(aud_record.fields):
                ref_vl_unit = self._parse_float(ref_record.fields[5])
                aud_vl_unit = self._parse_float(aud_record.fields[5])
                
                if abs(ref_vl_unit - aud_vl_unit) > 0.01:  # Tolerância de 1 centavo
                    self.differences.append({
                        'type': DifferenceType.VALUE_DIFFERENCE,
                        'record_type': 'C170',
                        'key': key,
                        'field': 'VL_UNIT',
                        'reference_value': ref_vl_unit,
                        'audit_value': aud_vl_unit,
                        'difference': ref_vl_unit - aud_vl_unit,
                        'severity': 'error',
                        'message': f'Diferenca no valor unitário do item: R$ {ref_vl_unit:.6f} vs R$ {aud_vl_unit:.6f}'
                    })
                    self.summary['value_differences'] += 1
            
            # Comparar valor total
            if 12 < len(ref_record.fields) and 12 < len(aud_record.fields):
                ref_vl_item = self._parse_float(ref_record.fields[12])
                aud_vl_item = self._parse_float(aud_record.fields[12])
                
                if abs(ref_vl_item - aud_vl_item) > 0.01:  # Tolerância de 1 centavo
                    self.differences.append({
                        'type': DifferenceType.VALUE_DIFFERENCE,
                        'record_type': 'C170',
                        'key': key,
                        'field': 'VL_ITEM',
                        'reference_value': ref_vl_item,
                        'audit_value': aud_vl_item,
                        'difference': ref_vl_item - aud_vl_item,
                        'severity': 'error',
                        'message': f'Diferenca no valor total do item: R$ {ref_vl_item:.2f} vs R$ {aud_vl_item:.2f}'
                    })
                    self.summary['value_differences'] += 1
    
    def _find_duplicates(self, records: List[Any]) -> List[Dict[str, Any]]:
        """Encontra registros duplicados com base em uma chave única"""
        key_counts = {}
        duplicates = []
        
        # Contar ocorrências de cada chave
        for record in records:
            if len(record.fields) >= 9:
                key = f"{record.fields[3]}|{record.fields[5]}|{record.fields[6]}|{record.fields[7]}|{record.fields[8]}|{record.fields[2]}"
                if key not in key_counts:
                    key_counts[key] = []
                key_counts[key].append(record)
        
        # Identificar duplicados
        for key, record_list in key_counts.items():
            if len(record_list) > 1:
                # Para cada duplicado exceto o primeiro
                for i in range(1, len(record_list)):
                    duplicates.append({
                        'key': key,
                        'record': record_list[i],
                        'count': len(record_list)
                    })
        
        return duplicates

    def _compare_h010_records(self, ref_records: List[Any], aud_records: List[Any]):
        """Compara registros H010 (Inventário)"""
        # Criar dicionários com chaves únicas
        ref_dict = self._create_h010_dict(ref_records)
        aud_dict = self._create_h010_dict(aud_records)
        
        # Verificar itens faltantes no auditado
        for key, ref_record in ref_dict.items():
            if key not in aud_dict:
                self.differences.append({
                    'type': DifferenceType.MISSING_RECORD,
                    'record_type': 'H010',
                    'key': key,
                    'reference_data': {
                        'line_no': ref_record.line_no,
                        'cod_item': ref_record.fields[1] if len(ref_record.fields) > 1 else "",
                        'unid': ref_record.fields[2] if len(ref_record.fields) > 2 else "",
                        'vl_item': ref_record.fields[5] if len(ref_record.fields) > 5 else ""
                    },
                    'audit_data': None,
                    'severity': 'error',
                    'message': f'Item de estoque não encontrado no arquivo auditado: {key}'
                })
                self.summary['missing_records'] += 1
        
        # Verificar itens excedentes no auditado
        for key, aud_record in aud_dict.items():
            if key not in ref_dict:
                self.differences.append({
                    'type': DifferenceType.EXTRA_RECORD,
                    'record_type': 'H010',
                    'key': key,
                    'reference_data': None,
                    'audit_data': {
                        'line_no': aud_record.line_no,
                        'cod_item': aud_record.fields[1] if len(aud_record.fields) > 1 else "",
                        'unid': aud_record.fields[2] if len(aud_record.fields) > 2 else "",
                        'vl_item': aud_record.fields[5] if len(aud_record.fields) > 5 else ""
                    },
                    'severity': 'warning',
                    'message': f'Item de estoque excedente no arquivo auditado: {key}'
                })
                self.summary['extra_records'] += 1
        
        # Comparar valores em itens presentes em ambos os arquivos
        for key in set(ref_dict.keys()) & set(aud_dict.keys()):
            ref_record = ref_dict[key]
            aud_record = aud_dict[key]
            
            # Comparar quantidade
            if 3 < len(ref_record.fields) and 3 < len(aud_record.fields):
                ref_qtd = self._parse_float(ref_record.fields[3])
                aud_qtd = self._parse_float(aud_record.fields[3])
                
                if abs(ref_qtd - aud_qtd) > 0.001:  # Tolerância para quantidade
                    self.differences.append({
                        'type': DifferenceType.QUANTITY_DIFFERENCE,
                        'record_type': 'H010',
                        'key': key,
                        'field': 'QTD',
                        'reference_value': ref_qtd,
                        'audit_value': aud_qtd,
                        'difference': ref_qtd - aud_qtd,
                        'severity': 'error',
                        'message': f'Diferenca na quantidade do item de estoque: {ref_qtd} vs {aud_qtd}'
                    })
                    self.summary['quantity_differences'] += 1
            
            # Comparar valor unitário
            if 4 < len(ref_record.fields) and 4 < len(aud_record.fields):
                ref_vl_unit = self._parse_float(ref_record.fields[4])
                aud_vl_unit = self._parse_float(aud_record.fields[4])
                
                if abs(ref_vl_unit - aud_vl_unit) > 0.01:  # Tolerância de 1 centavo
                    self.differences.append({
                        'type': DifferenceType.VALUE_DIFFERENCE,
                        'record_type': 'H010',
                        'key': key,
                        'field': 'VL_UNIT',
                        'reference_value': ref_vl_unit,
                        'audit_value': aud_vl_unit,
                        'difference': ref_vl_unit - aud_vl_unit,
                        'severity': 'error',
                        'message': f'Diferenca no valor unitário do item de estoque: R$ {ref_vl_unit:.6f} vs R$ {aud_vl_unit:.6f}'
                    })
                    self.summary['value_differences'] += 1
            
            # Comparar valor total
            if 5 < len(ref_record.fields) and 5 < len(aud_record.fields):
                ref_vl_item = self._parse_float(ref_record.fields[5])
                aud_vl_item = self._parse_float(aud_record.fields[5])
                
                if abs(ref_vl_item - aud_vl_item) > 0.01:  # Tolerância de 1 centavo
                    self.differences.append({
                        'type': DifferenceType.VALUE_DIFFERENCE,
                        'record_type': 'H010',
                        'key': key,
                        'field': 'VL_ITEM',
                        'reference_value': ref_vl_item,
                        'audit_value': aud_vl_item,
                        'difference': ref_vl_item - aud_vl_item,
                        'severity': 'error',
                        'message': f'Diferenca no valor total do item de estoque: R$ {ref_vl_item:.2f} vs R$ {aud_vl_item:.2f}'
                    })
                    self.summary['value_differences'] += 1
    
    def _compare_e200_records(self, ref_records: List[Any], aud_records: List[Any]):
        """Compara registros E200 (Apuração de ICMS)"""
        if not ref_records or not aud_records:
            return
        
        ref_record = ref_records[0]
        aud_record = aud_records[0]
        
        # Comparar valor total de débitos
        if 2 < len(ref_record.fields) and 2 < len(aud_record.fields):
            ref_debitos = self._parse_float(ref_record.fields[2])
            aud_debitos = self._parse_float(aud_record.fields[2])
            
            if abs(ref_debitos - aud_debitos) > 0.01:  # Tolerância de 1 centavo
                self.differences.append({
                    'type': DifferenceType.VALUE_DIFFERENCE,
                    'record_type': 'E200',
                    'key': 'TOTAL_DEBITOS',
                    'field': 'VL_DEBITOS',
                    'reference_value': ref_debitos,
                    'audit_value': aud_debitos,
                    'difference': ref_debitos - aud_debitos,
                    'severity': 'error',
                    'message': f'Diferenca no total de debitos: R$ {ref_debitos:.2f} vs R$ {aud_debitos:.2f}'
                })
                self.summary['value_differences'] += 1
        
        # Comparar valor total de créditos
        if 3 < len(ref_record.fields) and 3 < len(aud_record.fields):
            ref_creditos = self._parse_float(ref_record.fields[3])
            aud_creditos = self._parse_float(aud_record.fields[3])
            
            if abs(ref_creditos - aud_creditos) > 0.01:  # Tolerância de 1 centavo
                self.differences.append({
                    'type': DifferenceType.VALUE_DIFFERENCE,
                    'record_type': 'E200',
                    'key': 'TOTAL_CREDITOS',
                    'field': 'VL_CREDITOS',
                    'reference_value': ref_creditos,
                    'audit_value': aud_creditos,
                    'difference': ref_creditos - aud_creditos,
                    'severity': 'error',
                    'message': f'Diferenca no total de creditos: R$ {ref_creditos:.2f} vs R$ {aud_creditos:.2f}'
                })
                self.summary['value_differences'] += 1
    
    def _compare_block_totals(self, ref_data: Dict[str, Any], aud_data: Dict[str, Any]):
        """Compara os totais dos blocos C, H e E"""
        # Comparar totais do Bloco C
        ref_c_details = self._get_block_details(ref_data, 'C')
        aud_c_details = self._get_block_details(aud_data, 'C')
        ref_c_total = ref_c_details['total']
        aud_c_total = aud_c_details['total']
        
        if abs(ref_c_total - aud_c_total) > 0.01:
            self.differences.append({
                'type': DifferenceType.VALUE_DIFFERENCE,
                'record_type': 'BLOCK_C',
                'key': 'TOTAL',
                'field': 'VL_TOTAL',
                'reference_value': ref_c_total,
                'audit_value': aud_c_total,
                'difference': ref_c_total - aud_c_total,
                'severity': 'error',
                'message': f'Diferenca no total do Bloco C: R$ {ref_c_total:.2f} vs R$ {aud_c_total:.2f}',
                'details': {
                    'reference_breakdown': ref_c_details['breakdown'],
                    'audit_breakdown': aud_c_details['breakdown']
                }
            })
            self.summary['value_differences'] += 1
        
        # Comparar totais do Bloco H
        ref_h_details = self._get_block_details(ref_data, 'H')
        aud_h_details = self._get_block_details(aud_data, 'H')
        ref_h_total = ref_h_details['total']
        aud_h_total = aud_h_details['total']
        
        if abs(ref_h_total - aud_h_total) > 0.01:
            self.differences.append({
                'type': DifferenceType.VALUE_DIFFERENCE,
                'record_type': 'BLOCK_H',
                'key': 'TOTAL',
                'field': 'VL_TOTAL',
                'reference_value': ref_h_total,
                'audit_value': aud_h_total,
                'difference': ref_h_total - aud_h_total,
                'severity': 'error',
                'message': f'Diferenca no total do Bloco H: R$ {ref_h_total:.2f} vs R$ {aud_h_total:.2f}',
                'details': {
                    'reference_breakdown': ref_h_details['breakdown'],
                    'audit_breakdown': aud_h_details['breakdown']
                }
            })
            self.summary['value_differences'] += 1
    
    def _create_c100_dict(self, records: List[Any]) -> Dict[str, Any]:
        """Cria um dicionário com chaves únicas para registros C100"""
        result = {}
        for record in records:
            if len(record.fields) >= 9:
                # Chave: CNPJ|Modelo|Série|Número|Data
                key = f"{record.fields[3]}|{record.fields[5]}|{record.fields[6]}|{record.fields[7]}|{record.fields[8]}"
                result[key] = record
        return result
    
    def _create_c170_dict(self, records: List[Any]) -> Dict[str, Any]:
        """Cria um dicionário com chaves únicas para registros C170"""
        result = {}
        for record in records:
            if len(record.fields) >= 9:
                # Chave: CNPJ|Modelo|Série|Número|Data|Item
                key = f"{record.fields[3]}|{record.fields[5]}|{record.fields[6]}|{record.fields[7]}|{record.fields[8]}|{record.fields[2]}"
                result[key] = record
        return result
    
    def _create_h010_dict(self, records: List[Any]) -> Dict[str, Any]:
        """Cria um dicionário com chaves únicas para registros H010"""
        result = {}
        for record in records:
            if len(record.fields) >= 2:
                # Chave: Código do Item
                key = record.fields[1]
                result[key] = record
        return result
    
    def _get_block_details(self, data: Dict[str, Any], block: str) -> Dict[str, Any]:
        """Calcula o total monetário de um bloco e retorna detalhes da composição"""
        total = 0.0
        breakdown = {}
        
        for reg_type, records in data.items():
            if reg_type.startswith(block):
                reg_total = 0.0
                reg_count = 0
                
                for record in records:
                    if reg_type == 'C100' and len(record.fields) > 10:
                        value = self._parse_float(record.fields[10])  # VL_DOC
                        reg_total += value
                        reg_count += 1
                    elif reg_type == 'C170' and len(record.fields) > 7:
                        value = self._parse_float(record.fields[7])  # VL_ITEM
                        reg_total += value
                        reg_count += 1
                    elif reg_type == 'H010' and len(record.fields) > 5:
                        value = self._parse_float(record.fields[5])   # VL_ITEM
                        reg_total += value
                        reg_count += 1
                    elif reg_type == 'E200' and len(record.fields) > 2:
                        value = self._parse_float(record.fields[2])   # VL_DEBITOS
                        reg_total += value
                        reg_count += 1
                
                if reg_total > 0:
                    breakdown[reg_type] = {
                        'total': reg_total,
                        'count': reg_count,
                        'average': reg_total / reg_count if reg_count > 0 else 0
                    }
                
                total += reg_total
        
        return {
            'total': total,
            'breakdown': breakdown
        }

    
    def _parse_float(self, value: str) -> float:
        """Converte uma string para float, tratando formatação brasileira"""
        if not value:
            return 0.0
        
        # Remover caracteres não numéricos, exceto vírgula e ponto
        cleaned = re.sub(r'[^\d,.-]', '', value)
        
        # Substituir vírgula por ponto
        cleaned = cleaned.replace(',', '.')
        
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
        
    def _get_block_total(self, data: Dict[str, Any], block: str) -> float:
        """Calcula o total monetário de um bloco"""
        total = 0.0
        
        for reg_type, records in data.items():
            if reg_type.startswith(block):
                for record in records:
                    if reg_type == 'C100' and len(record.fields) > 10:
                        total += self._parse_float(record.fields[10])  # VL_DOC
                    elif reg_type == 'C170' and len(record.fields) > 12:
                        total += self._parse_float(record.fields[12])  # VL_ITEM
                    elif reg_type == 'H010' and len(record.fields) > 5:
                        total += self._parse_float(record.fields[5])   # VL_ITEM
                    elif reg_type == 'E200' and len(record.fields) > 2:
                        total += self._parse_float(record.fields[2])   # VL_DEBITOS
        
        return total
    
    