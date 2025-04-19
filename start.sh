#!/bin/bash
# Script de inicialização para o Sistema Especialista em Apostas Esportivas

echo "Iniciando o Sistema Especialista em Apostas Esportivas..."

# Verificar se gunicorn está instalado
if ! command -v gunicorn &> /dev/null; then
    echo "Erro: gunicorn não está instalado. Execute ./install.sh primeiro."
    exit 1
fi

# Iniciar servidor gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 wsgi:application
