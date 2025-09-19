# sped_analyzer/core/rules/comparison.py

def generate_record_key(record, context):
    """Gera uma chave única para cada registro baseada em seu conteúdo"""
    if record.reg == "C100":
        return f"C100|{record.fields[8]}"  # Chave da NFe
    
    elif record.reg == "C170":
        # Encontra o documento pai
        parent = getattr(record, 'parent', None)
        if not parent:
            # Busca o C100 anterior
            idx = context.records.index(record)
            for r in reversed(context.records[:idx]):
                if r.reg == "C100":
                    parent = r
                    break
        
        if parent:
            # Chave composta: Chave do documento + Código do item + Valor
            item_code = record.fields[2] if len(record.fields) > 2 else ""
            item_value = record.fields[14] if len(record.fields) > 14 else ""
            return f"C170|{parent.fields[8]}|{item_code}|{item_value}"
    
    elif record.reg == "C190":
        # Chave: CST + CFOP + Alíquota
        cst = record.fields[3] if len(record.fields) > 3 else ""
        cfop = record.fields[4] if len(record.fields) > 4 else ""
        aliq = record.fields[5] if len(record.fields) > 5 else ""
        return f"C190|{cst}|{cfop}|{aliq}"
    
    return f"{record.reg}|{'|'.join(record.fields)}"

def compare_records_by_key(context_cliente, context_escritorio):
    """Compara registros usando chaves únicas"""
    # Gera dicionários de registros por chave
    cliente_keys = {}
    escritorio_keys = {}
    
    for record in context_cliente.records:
        key = generate_record_key(record, context_cliente)
        cliente_keys[key] = record
    
    for record in context_escritorio.records:
        key = generate_record_key(record, context_escritorio)
        escritorio_keys[key] = record
    
    # Identifica diferenças
    result = {
        "only_cliente": [],
        "only_escritorio": [],
        "diferent_values": [],
        "resumo_quantitativo": {}
    }
    
    # Registros apenas no cliente
    for key, record in cliente_keys.items():
        if key not in escritorio_keys:
            result["only_cliente"].append({
                "key": key,
                "record": serialize_record(record),
                "impacto": calcular_impacto_registro(record, context_cliente)
            })
    
    # Registros apenas no escritório
    for key, record in escritorio_keys.items():
        if key not in cliente_keys:
            result["only_escritorio"].append({
                "key": key,
                "record": serialize_record(record),
                "impacto": calcular_impacto_registro(record, context_escritorio)
            })
    
    # Registros com valores diferentes
    for key in set(cliente_keys.keys()) & set(escritorio_keys.keys()):
        record_c = cliente_keys[key]
        record_e = escritorio_keys[key]
        
        if record_c.fields != record_e.fields:
            # Compara campo a campo
            diff_fields = []
            for i, (val_c, val_e) in enumerate(zip(record_c.fields, record_e.fields)):
                if val_c != val_e:
                    diff_fields.append({
                        "campo": i,
                        "valor_cliente": val_c,
                        "valor_escritorio": val_e,
                        "impacto": calcular_impacto_campo(i, val_c, val_e, record_c.reg)
                    })
            
            result["diferent_values"].append({
                "key": key,
                "record_cliente": serialize_record(record_c),
                "record_escritorio": serialize_record(record_e),
                "diferencas": diff_fields
            })
    
    # Resumo quantitativo
    result["resumo_quantitativo"] = {
        "total_cliente": len(cliente_keys),
        "total_escritorio": len(escritorio_keys),
        "diferenca": len(cliente_keys) - len(escritorio_keys),
        "por_registro": {}
    }
    
    # Contagem por tipo de registro
    for reg_type in ["C100", "C170", "C190"]:
        count_c = sum(1 for r in cliente_keys.values() if r.reg == reg_type)
        count_e = sum(1 for r in escritorio_keys.values() if r.reg == reg_type)
        result["resumo_quantitativo"]["por_registro"][reg_type] = {
            "cliente": count_c,
            "escritorio": count_e,
            "diferenca": count_c - count_e
        }
    
    return result

def calcular_impacto_registro(record, context):
    """Calcula o impacto financeiro de um registro"""
    if record.reg == "C170":
        try:
            return float(record.fields[14])  # VL_ITEM
        except (ValueError, IndexError):
            return 0.0
    return 0.0

def calcular_impacto_campo(campo_idx, val_c, val_e, reg_type):
    """Calcula o impacto de uma diferença em um campo específico"""
    if reg_type == "C170" and campo_idx == 14:  # VL_ITEM
        try:
            return abs(float(val_c) - float(val_e))
        except ValueError:
            return 0.0
    return 0.0

def serialize_record(record):
    """Serializa um registro para JSON"""
    return {
        "reg": record.reg,
        "line_no": record.line_no,
        "fields": record.fields
    }