import os
import uuid
import tempfile
from django.conf import settings
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .rules.main_rules import SPEDAutoFixer
from .rules.basic_rules_fiscal import SPEDComparator
import chardet
import traceback
from .parsers import SpedParser
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .rules.comparison import compare_records_by_key


@method_decorator(csrf_exempt, name='dispatch')
class FixSped(View):
    def post(self, request):
        try:
            files = request.FILES.getlist("files")
            sped_type = request.POST.get('sped_type', 'fiscal')  # Padrão: fiscal

            # Valida o tipo de SPED
            if sped_type not in ['fiscal', 'contrib']:
                return JsonResponse({
                    'error': 'Tipo de SPED inválido',
                    'message': 'Os tipos válidos são: fiscal, contrib'
                }, status=400)

            if not files:
                return JsonResponse({
                    'error': 'Nenhum arquivo enviado',
                    'message': 'Por favor, envie pelo menos um arquivo SPED (.txt)'
                }, status=400)

            results = []

            # Se houver apenas 1 arquivo: correção normal
            if len(files) == 1:
                uploaded_file = files[0]
                temp_file_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                        temp_file.write(uploaded_file.read())
                        temp_file_path = temp_file.name

                    fixer = SPEDAutoFixer(temp_file_path, sped_type=sped_type)
                    issues = fixer.fix_all()

                    # Salvar arquivo corrigido
                    original_name = uploaded_file.name
                    base_name, ext = os.path.splitext(original_name)
                    corrected_filename = f"{base_name}_corrigido_{uuid.uuid4().hex[:8]}{ext}"
                    corrected_path = os.path.join('corrigidos', corrected_filename)

                    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'corrigidos'), exist_ok=True)

                    with default_storage.open(corrected_path, 'w') as f:
                        f.write(fixer.get_corrected_content())

                    corrected_url = default_storage.url(corrected_path)

                    results.append({
                        'original_name': original_name,
                        'corrected_url': corrected_url,
                        'sped_type': sped_type,
                        'issues': [issue.to_dict() for issue in issues],
                        'status': 'success'
                    })

                finally:
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)

            # Se houver 2 arquivos: comparação de similaridade
            elif len(files) == 2:
                temp_paths = []
                try:
                    # Salvar arquivos temporários
                    for uploaded_file in files:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                            file_content = uploaded_file.read()
                            # temp_file.write(file_content)
                            # temp_paths.append(temp_file.name)

                            # Detectar codificação
                            detected = chardet.detect(file_content)
                            encoding = detected['encoding'] or 'utf-8'
                            
                            # Tentar decodificar
                            decoded_content = None
                            try:
                                decoded_content = file_content.decode(encoding)
                            except UnicodeDecodeError:
                                # Tenta encodings alternativos
                                for enc in ['utf-8', 'iso-8859-1', 'windows-1252', 'ascii']:
                                    try:
                                        decoded_content = file_content.decode(enc)
                                        encoding = enc
                                        break
                                    except UnicodeDecodeError:
                                        continue
                            if decoded_content is None:
                                raise ValueError(
                                    f"Nao foi possivel decodificar o arquivo {uploaded_file.name} "
                                    f"com encodings: utf-8, iso-8859-1, windows-1252, ascii"
                                )

                            # Grava o conteúdo decodificado no arquivo temporário
                            temp_file.write(decoded_content.encode('utf-8'))
                            temp_paths.append(temp_file.name)

                    # Carregar SPEDs
                    sped_a = SPEDAutoFixer(temp_paths[0], sped_type=sped_type)
                    sped_b = SPEDAutoFixer(temp_paths[1], sped_type=sped_type)

                    # Comparar
                    comparator = SPEDComparator(sped_a.sped.records, sped_b.sped.records)
                    similarity, divergences = comparator.compare()
                    

                    results.append({
                        'status': 'success',
                        'similarity': f'{similarity*100:.2f}%',
                        'files_compared': [
                            {'original_name': files[0].name},
                            {'original_name': files[1].name},
                        ],
                        'divergences': [
                            {
                                'line_no': d[0] if len(d) > 0 else None,
                                'reg': d[1] if len(d) > 1 else None,
                                'value_a': d[2] if len(d) > 2 else None,
                                'value_b': d[3] if len(d) > 3 else None,
                            } for d in divergences
                        ]
                    })
                finally:
                    # Remover arquivos temporários
                    for path in temp_paths:
                        if os.path.exists(path):
                            os.unlink(path)

            else:
                return JsonResponse({
                    'error': 'Número de arquivos inválido',
                    'message': 'Envie 1 arquivo para correção ou 2 arquivos para comparação',
                    'status': 'error'
                }, status=400)

            return JsonResponse({
                'status': 'success',
                'files': results
            })

        except Exception as e:
            tb = traceback.format_exc()
            return JsonResponse({
                'status': 'error',
                'message': f'Erro inesperado: {str(e)}',
                'traceback': tb
            }, status=500)

        
    
    
    def get(self, request):
        """Documentação da API"""
        return JsonResponse({
            "api_name": "SPED Fixer API",
            "version": "1.0",
            "description": "API para correção automática de arquivos SPED",
            "endpoints": {
                "POST /fix-sped/": {
                    "description": "Processa e corrige arquivos SPED",
                    "parameters": {
                        "files": "Arquivos SPED (.txt) a serem processados",
                        "sped_type": "Tipo de SPED (fiscal, contrib, both). Padrão: fiscal"
                    },
                    "response": {
                        "status": "success",
                        "files": [
                            {
                                "original_name": "Nome do arquivo original",
                                "corrected_url": "URL para download do arquivo corrigido",
                                "sped_type": "Tipo de SPED processado",
                                "issues": [
                                    {
                                        "line_no": "Número da linha",
                                        "reg": "Tipo do registro",
                                        "rule_id": "ID da regra",
                                        "severity": "Severidade do erro",
                                        "message": "Mensagem do erro",
                                        "suggestion": "Sugestão de correção"
                                    }
                                ],
                                "status": "success"
                            }
                        ]
                    }
                },
                "GET /download/<filename>/": {
                    "description": "Download de arquivos corrigidos",
                    "parameters": {
                        "filename": "Nome do arquivo corrigido"
                    }
                }
            },
            "sped_types": {
                "fiscal": "SPED Fiscal (EFD ICMS/IPI)",
                "contrib": "SPED Contribuições (EFD PIS/COFINS)",
                "both": "Arquivo contendo ambos os tipos de SPED"
            }
        })
    



def serialize_issue(issue):
    result = {
        "line_no": issue.line_no,
        "reg": issue.reg,
        "rule_id": issue.rule_id,
        "severity": issue.severity,
        "message": issue.message,
        "suggestion": issue.suggestion
    }
    
    if hasattr(issue, 'impacted_records'):
        result["impacted_records"] = [
            {"reg": r.reg, "line_no": r.line_no} 
            for r in issue.impacted_records
        ]
    
    if hasattr(issue, 'impact_details'):
        result["impact_details"] = issue.impact_details
    
    return result

def generate_impact_summary(issues):
    severity_count = {"error": 0, "warning": 0, "info": 0}
    blocos_afetados = set()
    valor_impacto = 0
    
    for issue in issues:
        severity_count[issue.severity] += 1
        if hasattr(issue, 'impact_details'):
            for detail in issue.impact_details:
                blocos_afetados.add(detail["bloco"])
        
        if hasattr(issue, 'record') and issue.record.reg == "C100":
            try:
                vl_icms = float(issue.record.fields[13]) if len(issue.record.fields) > 13 else 0
                valor_impacto += abs(vl_icms)
            except (ValueError, IndexError):
                pass
    
    return {
        "total_problemas": len(issues),
        "por_severidade": severity_count,
        "blocos_afetados": list(blocos_afetados),
        "valor_impacto_estimado": valor_impacto
    }

def compare_contexts(context_cliente, context_escritorio):
    divergencias = []
    
    # Exemplo: Comparar totais do Bloco C
    def get_total_bloco_c(context):
        total = 0
        for record in context.records:
            if record.reg == "C190":
                try:
                    total += float(record.fields[5])  # VL_ICMS
                except (IndexError, ValueError):
                    pass
        return total
    
    total_cliente = get_total_bloco_c(context_cliente)
    total_escritorio = get_total_bloco_c(context_escritorio)
    
    if abs(total_cliente - total_escritorio) > 0.01:
        divergencias.append({
            "tipo": "Divergência de Totais",
            "bloco": "C",
            "valor_cliente": total_cliente,
            "valor_escritorio": total_escritorio,
            "diferenca": total_cliente - total_escritorio,
            "mensagem": f"Total do Bloco C diverge: Cliente R$ {total_cliente} vs Escritório R$ {total_escritorio}"
        })
    
    return divergencias



def try_read_file(file_path, encodings=None):
    """
    Tenta ler o arquivo com várias codificações diferentes.
    Retorna o conteúdo e a codificação utilizada.
    """
    if encodings is None:
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'cp850']
    
    # Primeiro tenta detectar a codificação
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # Lê os primeiros 10KB
        detected = chardet.detect(raw_data)
        if detected['confidence'] > 0.7:
            # Se a confiança for alta, tenta primeiro com a codificação detectada
            try:
                with open(file_path, 'r', encoding=detected['encoding']) as f:
                    content = f.read()
                return content, detected['encoding']
            except UnicodeDecodeError:
                pass
    except:
        pass
    
    # Se a detecção falhar, tenta cada codificação da lista
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            return content, encoding
        except UnicodeDecodeError:
            continue
    
    # Se nenhuma codificação funcionar, tenta ler com tratamento de erros
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        return content, 'utf-8 (with errors replaced)'
    except Exception as e:
        raise Exception(f"Não foi possível ler o arquivo com nenhuma codificação. Último erro: {str(e)}")



def load_sped_file(file_path, sped_type='fiscal'):
    """Carrega um arquivo SPED com tratamento robusto de codificação"""
    try:
        # Tenta ler o arquivo com várias codificações
        content, encoding = try_read_file(file_path)
        
        # Cria um arquivo temporário com o conteúdo já decodificado
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Carrega o arquivo com a codificação correta
            fixer = SPEDAutoFixer(temp_path, sped_type=sped_type)
            issues = fixer.fix_all()
            return fixer.context, issues, encoding
        finally:
            # Remove o arquivo temporário
            os.unlink(temp_path)
    except Exception as e:
        raise Exception(f"Não foi possível processar o arquivo. Erro: {str(e)}")

@csrf_exempt
@require_http_methods(["POST"])
def compare_sped_files(request):
    try:
        cliente_file = request.FILES.get('cliente_file')
        escritorio_file = request.FILES.get('escritorio_file')
        
        if not cliente_file or not escritorio_file:
            return JsonResponse({"error": "Ambos os arquivos são obrigatórios"}, status=400)
        
        # Salva os arquivos temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as cliente_temp:
            # Escreve o conteúdo do arquivo como está, sem modificar a codificação
            cliente_temp.write(cliente_file.read())
            cliente_path = cliente_temp.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as escritorio_temp:
            escritorio_temp.write(escritorio_file.read())
            escritorio_path = escritorio_temp.name
        
        try:
            # Processa os arquivos com tratamento robusto de codificação
            context_cliente, issues_cliente, encoding_cliente = load_sped_file(cliente_path, sped_type='fiscal')
            context_escritorio, issues_escritorio, encoding_escritorio = load_sped_file(escritorio_path, sped_type='fiscal')
            
            # Compara os contextos
            divergencias = compare_contexts(context_cliente, context_escritorio)
            comparacao_detalhada = compare_records_by_key(context_cliente, context_escritorio)
            
            result = {
                "issues_cliente": [serialize_issue(issue) for issue in issues_cliente],
                "issues_escritorio": [serialize_issue(issue) for issue in issues_escritorio],
                "divergencias": divergencias,
                "resumo_impacto_cliente": generate_impact_summary(issues_cliente),
                "resumo_impacto_escritorio": generate_impact_summary(issues_escritorio),
                "encoding_cliente": encoding_cliente,
                "encoding_escritorio": encoding_escritorio,
                "comparacao_detalhada": comparacao_detalhada,
                "acao_recomendada": gerar_recomendacao_acao(comparacao_detalhada)
            }
            


            return JsonResponse(result)
        
        finally:
            # Remove os arquivos temporários
            os.unlink(cliente_path)
            os.unlink(escritorio_path)
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

def gerar_recomendacao_acao(comparacao):
    """Gera recomendações de ação baseadas na comparação"""
    recomendacoes = []
    
    # Verifica registros faltantes no cliente
    only_escritorio = comparacao.get("only_escritorio", [])
    if only_escritorio:
        total_impacto = sum(r["impacto"] for r in only_escritorio)
        recomendacoes.append({
            "tipo": "ADICIONAR",
            "destino": "CLIENTE",
            "quantidade": len(only_escritorio),
            "impacto_total": total_impacto,
            "descricao": f"Adicionar {len(only_escritorio)} registros no arquivo do cliente (impacto total: R$ {total_impacto:.2f})",
            "registros": only_escritorio[:5]  # Mostra até 5 exemplos
        })
    
    # Verifica registros faltantes no escritório
    only_cliente = comparacao.get("only_cliente", [])
    if only_cliente:
        total_impacto = sum(r["impacto"] for r in only_cliente)
        recomendacoes.append({
            "tipo": "REMOVER",
            "destino": "ESCRITORIO",
            "quantidade": len(only_cliente),
            "impacto_total": total_impacto,
            "descricao": f"Remover {len(only_cliente)} registros do arquivo do escritório (impacto total: R$ {total_impacto:.2f})",
            "registros": only_cliente[:5]
        })
    
    # Verifica valores diferentes
    different_values = comparacao.get("diferent_values", [])
    if different_values:
        recomendacoes.append({
            "tipo": "CORRIGIR",
            "destino": "AMBOS",
            "quantidade": len(different_values),
            "descricao": f"Corrigir {len(different_values)} registros com valores divergentes",
            "registros": different_values[:3]
        })
    
    return recomendacoes