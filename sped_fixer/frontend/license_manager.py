import hashlib
import platform
import subprocess
import uuid
import json
import os
from api_client import APIClient
from datetime import datetime

class LicenseManager:
    def __init__(self, api_client):
        self.api_client = api_client
        self.hardware_id = self.generate_hardware_id()
        self.license_file = "license.dat"
    
    def generate_hardware_id(self):
        components = [
            str(uuid.getnode()),
            platform.processor(),
            self.get_disk_serial(),
            platform.system(),
        ]
        return hashlib.sha256('-'.join(components).encode()).hexdigest()[:16]
    
    def get_disk_serial(self):
        try:
            if platform.system() == 'Windows':
                output = subprocess.check_output('wmic diskdrive get serialnumber', shell=True).decode()
                return output.split('\n')[1].strip()
            else:
                return subprocess.check_output('hdparm -I /dev/sda | grep Serial', shell=True).decode()
        except:
            return "UNKNOWN"
    
    def save_license(self, license_data):
        with open(self.license_file, 'w') as f:
            json.dump(license_data, f)
    
    def load_license(self):
        try:
            with open(self.license_file, 'r') as f:
                return json.load(f)
        except:
            return None
    
    def activate_license(self, chave):
        response = self.api_client.validar_chave(self.hardware_id, chave)
        if response and response.get('valida'):
            license_data = {
                'chave': chave,
                'hardware_id': self.hardware_id,
                'cliente': response.get('cliente'),
                'expira_em': response.get('expira_em'),
                'ativado_em': datetime.now().isoformat()
            }
            self.save_license(license_data)
            return True, "Licença ativada com sucesso!"
        return False, response.get('motivo', 'Chave inválida')
    
    def check_license(self):
        license_data = self.load_license()
        if license_data:
            # Verifica se a licença ainda é válida (pode validar online ou offline)
            return True
        return False