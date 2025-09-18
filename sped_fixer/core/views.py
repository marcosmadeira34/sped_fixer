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
from .rules.main_rules import SPEDAutoFixer, SPEDComparator
# from .sped_comparator import SPEDComparator
import chardet
import traceback
from .parsers import SpedParser


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
                                    f"Não foi possível decodificar o arquivo {uploaded_file.name} "
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
    



@csrf_exempt
def compare_sped_files(request):
    """
    Endpoint para comparar dois arquivos SPED
    """
    if request.method == 'POST':
        try:
            # Verificar se os dois arquivos foram enviados
            if 'reference_file' not in request.FILES or 'audit_file' not in request.FILES:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Both reference and audit files are required'
                }, status=400)
            
            reference_file = request.FILES['reference_file']
            audit_file = request.FILES['audit_file']
            
            # Salvar os arquivos temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as ref_temp:
                for chunk in reference_file.chunks():
                    ref_temp.write(chunk)
                ref_path = ref_temp.name
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as aud_temp:
                for chunk in audit_file.chunks():
                    aud_temp.write(chunk)
                aud_path = aud_temp.name
            
            # Processar os arquivos com o parser
            parser = SpedParser()
            ref_records = parser.parse(open(ref_path, 'r', encoding='latin-1').read())
            aud_records = parser.parse(open(aud_path, 'r', encoding='latin-1').read())
            
            # Organizar os dados por tipo de registro
            ref_data = {}
            for record in ref_records:
                reg_type = record.reg
                if reg_type not in ref_data:
                    ref_data[reg_type] = []
                ref_data[reg_type].append(record)
            
            aud_data = {}
            for record in aud_records:
                reg_type = record.reg
                if reg_type not in aud_data:
                    aud_data[reg_type] = []
                aud_data[reg_type].append(record)
            
            # Comparar os arquivos
            comparator = SPEDComparator()
            comparison_result = comparator.compare(ref_data, aud_data)
            
            # Remover arquivos temporários
            os.unlink(ref_path)
            os.unlink(aud_path)
            
            return JsonResponse({
                'status': 'success',
                'comparison': comparison_result
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)