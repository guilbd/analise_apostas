"""
Exemplo de como integrar as rotas de debug na aplicação principal
"""
from flask import Flask
from debug_route import register_debug_routes

# Código para integrar as rotas de debug na sua aplicação Flask existente
def add_debug_routes_to_app(app):
    """
    Adiciona as rotas de debug à aplicação Flask existente
    
    Args:
        app: A instância da aplicação Flask
    """
    # Registrar as rotas de debug
    register_debug_routes(app)
    
    # Imprimir mensagem de confirmação
    print("Rotas de debug adicionadas com sucesso!")
    print("Acesse /debug/ para ver a lista de arquivos disponíveis")
    print("Acesse /debug/view/<nome_do_arquivo> para visualizar um arquivo")
    print("Acesse /debug/download/<nome_do_arquivo> para baixar um arquivo")
    
    return app

# Exemplo de como usar em sua aplicação principal
"""
# No seu arquivo app.py ou similar:

from flask import Flask
from debug_integration import add_debug_routes_to_app

app = Flask(__name__)

# Configurações e rotas da sua aplicação...

# Adicionar rotas de debug (apenas em ambiente de desenvolvimento)
if app.config.get('DEBUG', False):
    app = add_debug_routes_to_app(app)

if __name__ == '__main__':
    app.run(debug=True)
"""
