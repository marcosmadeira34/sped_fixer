import requests
import json
from datetime import datetime

class APIClient:
    def __init__(self, base_url, token=None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {'Content-Type': 'application/json'}
        if token:
            self.headers['Authorization'] = f'Token {token}'
    
    def login(self, username, password):
        url = f"{self.base_url}/api-auth/login/"
        response = requests.post(url, json={'username': username, 'password': password})
        if response.status_code == 200:
            self.token = response.json().get('token')
            self.headers['Authorization'] = f'Token {self.token}'
            return True
        return False
    
    def gerar_chave(self, hardware_id, cliente_id):
        url = f"{self.base_url}/api/licencas/gerar_chave/"
        response = requests.post(url, json={
            'hardware_id': hardware_id,
            'cliente_id': cliente_id
        }, headers=self.headers)
        return response.json() if response.status_code == 200 else None
    
    def validar_chave(self, hardware_id, chave):
        url = f"{self.base_url}/api/licencas/validar_chave/"
        response = requests.post(url, json={
            'hardware_id': hardware_id,
            'chave': chave
        }, headers=self.headers)
        return response.json() if response.status_code == 200 else None
    
    def upload_arquivos(self, original_path, comparacao_path):
        url = f"{self.base_url}/api/comparacoes/upload_arquivos/"
        with open(original_path, 'rb') as f1, open(comparacao_path, 'rb') as f2:
            files = {
                'arquivo_original': f1,
                'arquivo_comparacao': f2
            }
            response = requests.post(url, files=files, headers=self.headers)
        return response.json() if response.status_code == 200 else None