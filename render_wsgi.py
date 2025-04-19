import os
import sys
import json

# Adicionar diretório da aplicação ao path
sys.path.insert(0, os.path.dirname(__file__))

# Importar aplicação Flask
from app_production import app as application

# Configurações específicas para ambiente de hospedagem
application.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sistema-apostas-esportivas-production-key')
application.config['DEBUG'] = False
application.config['TESTING'] = False

# Configurar SERVER_NAME ou definir como None para aceitar qualquer domínio
application.config['SERVER_NAME'] = os.environ.get('SERVER_NAME', None)

# Inicializar aplicação
if __name__ == '__main__':
    application.run(host='0.0.0.0')
