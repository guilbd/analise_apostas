# Sistema Especialista em Apostas Esportivas

## Sobre o Sistema
Este é um sistema web para análise de jogos e recomendações de apostas baseadas em dados.
O sistema coleta jogos automaticamente, analisa partidas com base em histórico e estatísticas,
e fornece recomendações de apostas em diferentes níveis de risco.

## Requisitos
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Servidor web (recomendado: Nginx)

## Instruções de Implantação

### 1. Instalação de Dependências
Execute o script de instalação para instalar todas as dependências necessárias:

```bash
./install.sh
```

### 2. Configuração do Servidor Web (Nginx)
Exemplo de configuração para Nginx:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /caminho/para/static;
        expires 1y;
        add_header Cache-Control "public, max-age=31536000";
    }
}
```

Substitua `seu-dominio.com` pelo seu domínio real e `/caminho/para/static` pelo caminho completo para o diretório `static`.

### 3. Iniciar o Servidor
Execute o script de inicialização para iniciar o servidor Gunicorn:

```bash
./start.sh
```

Para manter o servidor rodando em segundo plano, você pode usar:

```bash
nohup ./start.sh > server.log 2>&1 &
```

### 4. Acesso ao Sistema
- URL: http://seu-dominio.com (ou https:// se configurado com SSL)
- Usuário administrador padrão: admin / admin123
- Usuário comum padrão: usuario / usuario123

**Importante:** Altere as senhas padrão após o primeiro acesso!

## Funcionalidades
- Coleta automática de jogos
- Análise de partidas com base em histórico e estatísticas
- Recomendações de apostas em diferentes níveis de risco
- Análise de mercados adicionais (escanteios e cartões)
- Estratégia de cashout
- Dashboard interativo com atualizações em tempo real

## Suporte
Para suporte ou dúvidas, entre em contato através do email: suporte@exemplo.com
