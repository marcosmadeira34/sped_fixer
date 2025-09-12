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
import chardet
import traceback


@method_decorator(csrf_exempt, name='dispatch')
class FixSped(View):
    def post(self, request):
        try:
            files = request.FILES.getlist("files")
            sped_type = request.POST.get('sped_type', 'fiscal')  # Padrão: fiscal
            
            # Valida o tipo de SPED
            if sped_type not in ['fiscal', 'contrib', 'both']:
                return JsonResponse({
                    'error': 'Tipo de SPED inválido',
                    'message': 'Os tipos válidos são: fiscal, contrib, both'
                }, status=400)
            
            if not files:
                return JsonResponse({
                    'error': 'Nenhum arquivo enviado',
                    'message': 'Por favor, envie pelo menos um arquivo SPED (.txt)'
                }, status=400)
            
            results = []
            
            for uploaded_file in files:
                # Verificar extensão do arquivo
                if not uploaded_file.name.lower().endswith('.txt'):
                    results.append({
                        'original_name': uploaded_file.name,
                        'error': 'Formato inválido. Apenas arquivos .txt são aceitos'
                    })
                    continue
                
                temp_file_path = None
                try:
                    # Salvar arquivo temporariamente
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
                        # Ler o conteúdo do arquivo e detectar codificação
                        file_content = uploaded_file.read()
                        
                        # Detectar a codificação do arquivo
                        detected = chardet.detect(file_content)
                        encoding = detected['encoding'] or 'utf-8'
                        
                        # Tentar decodificar com a codificação detectada
                        try:
                            decoded_content = file_content.decode(encoding)
                        except UnicodeDecodeError:
                            # Se falhar, tentar com codificações alternativas
                            encodings_to_try = ['utf-8', 'iso-8859-1', 'windows-1252', 'ascii']
                            decoded_content = None
                            
                            for enc in encodings_to_try:
                                try:
                                    decoded_content = file_content.decode(enc)
                                    encoding = enc
                                    break
                                except UnicodeDecodeError:
                                    continue
                            
                            if decoded_content is None:
                                raise ValueError(f"Não foi possível decodificar o arquivo com as codificações: {', '.join(encodings_to_try)}")
                        
                        # Escrever o conteúdo decodificado no arquivo temporário
                        temp_file.write(decoded_content.encode('utf-8'))
                        temp_file_path = temp_file.name
                    
                    # Processar arquivo SPED com o tipo especificado
                    fixer = SPEDAutoFixer(temp_file_path, sped_type=sped_type)
                    issues = fixer.fix_all()
                    
                    # Gerar nome único para arquivo corrigido
                    original_name = uploaded_file.name
                    base_name, ext = os.path.splitext(original_name)
                    corrected_filename = f"{base_name}_corrigido_{uuid.uuid4().hex[:8]}{ext}"
                    
                    # Salvar arquivo corrigido na mídia
                    corrected_path = os.path.join('corrigidos', corrected_filename)
                    corrected_content = fixer.get_corrected_content()
                    
                    # Garantir que o diretório exista
                    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'corrigidos'), exist_ok=True)
                    
                    # Salvar arquivo corrigido
                    with default_storage.open(corrected_path, 'w') as f:
                        f.write(corrected_content)
                    
                    # Gerar URL de download
                    corrected_url = default_storage.url(corrected_path)
                    
                    # Adicionar resultado
                    results.append({
                        'original_name': original_name,
                        'corrected_url': corrected_url,
                        'sped_type': sped_type,
                        'issues': [issue.to_dict() for issue in issues],
                        'status': 'success'
                    })
                
                except Exception as e:
                    # Capturar o traceback completo
                    tb = traceback.format_exc()
                    print(f"Erro ao processar arquivo: {str(e)}")
                    print(f"Traceback: {tb}")
                    
                    results.append({
                        'original_name': uploaded_file.name,
                        'error': f'Erro ao processar arquivo: {str(e)}',
                        'traceback': tb,
                        'status': 'error'
                    })
                finally:
                    # Remover arquivo temporário
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
            
            return JsonResponse({
                'status': 'success',
                'files': results
            })
        
        except Exception as e:
            tb = traceback.format_exc()
            print(f"Erro inesperado: {str(e)}")
            print(f"Traceback: {tb}")
            
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