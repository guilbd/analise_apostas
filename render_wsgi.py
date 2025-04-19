import os
import sys
import json

# Adicionar diretório da aplicação ao path
sys.path.insert(0, os.path.dirname(__file__))

# Importar aplicação Flask
from app_production import app as application

# Carregar configurações de produção
config_file = os.path.join(os.path.dirname(__file__), 'config.json')
if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
        for key, value in config.items():
            application.config[key] = value

# Configurações específicas para ambiente de hospedagem
application.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sistema-apostas-esportivas-production-key')
application.config['DEBUG'] = False
application.config['TESTING'] = False

# Inicializar aplicação
if __name__ == '__main__':
    application.run(host='0.0.0.0')
