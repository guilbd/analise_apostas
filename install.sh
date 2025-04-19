#!/bin/bash
# Script de instalação para o Sistema Especialista em Apostas Esportivas

echo "Iniciando instalação do Sistema Especialista em Apostas Esportivas..."

# Verificar se pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo "Erro: pip3 não está instalado. Por favor, instale o Python 3 e o pip."
    exit 1
fi

# Instalar dependências
echo "Instalando dependências..."
pip3 install -r requirements.txt

# Verificar se o diretório de relatórios existe
if [ ! -d "relatorios" ]; then
    echo "Criando diretório de relatórios..."
    mkdir -p relatorios
fi

# Configurar permissões
echo "Configurando permissões..."
chmod -R 755 .
chmod -R 777 relatorios

echo "Instalação concluída com sucesso!"
echo "Para iniciar o servidor, execute: ./start.sh"
