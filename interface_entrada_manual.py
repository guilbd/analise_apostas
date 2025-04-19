"""
Interface para entrada manual de dados do site Academia das Apostas Brasil
-------------------------------------------------------------------------
Este módulo implementa uma interface web para entrada manual de dados copiados
do site Academia das Apostas Brasil.
"""

import os
import json
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, StringField, SelectField
from wtforms.validators import DataRequired

from coleta_dados_reais import ColetorDadosReais

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('interface_entrada_manual')

# Inicializar o coletor de dados
coletor = ColetorDadosReais()

# Definir formulários
class FormEntradaManual(FlaskForm):
    """Formulário para entrada manual de dados copiados."""
    texto = TextAreaField('Cole aqui o texto copiado do site Academia das Apostas Brasil', 
                         validators=[DataRequired()])
    tipo_conteudo = SelectField('Tipo de conteúdo', choices=[
        ('jogo', 'Página de jogo específico'),
        ('lista', 'Lista de jogos'),
        ('classificacao', 'Tabela de classificação')
    ])
    submit = SubmitField('Processar')

class FormBuscaJogo(FlaskForm):
    """Formulário para busca de jogo específico."""
    time_casa = StringField('Time da casa', validators=[DataRequired()])
    time_visitante = StringField('Time visitante', validators=[DataRequired()])
    submit = SubmitField('Buscar')

# Função para criar a aplicação Flask
def criar_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'sistema-apostas-esportivas-entrada-manual'
    
    # Rota principal - formulário de entrada manual
    @app.route('/', methods=['GET', 'POST'])
    def index():
        form = FormEntradaManual()
        
        if form.validate_on_submit():
            texto = form.texto.data
            tipo_conteudo = form.tipo_conteudo.data
            
            try:
                # Processar o texto copiado
                resultado = coletor.processar_texto_copiado(texto)
                
                # Verificar se foram encontrados jogos ou estatísticas
                if resultado.get('jogos'):
                    flash(f'Foram encontrados {len(resultado["jogos"])} jogos no texto copiado.', 'success')
                else:
                    flash('Nenhum jogo foi encontrado no texto copiado.', 'warning')
                    
                if resultado.get('estatisticas'):
                    flash(f'Foram encontradas estatísticas para {len(resultado["estatisticas"])} jogos.', 'success')
                else:
                    flash('Nenhuma estatística foi encontrada no texto copiado.', 'warning')
                
                # Redirecionar para a página de resultados
                return redirect(url_for('resultados', tipo=tipo_conteudo))
                
            except Exception as e:
                logger.error(f"Erro ao processar texto copiado: {str(e)}")
                flash(f'Erro ao processar o texto: {str(e)}', 'danger')
        
        # Carregar jogos disponíveis
        jogos = coletor.carregar_jogos()
        
        return render_template('entrada_manual.html', form=form, jogos=jogos)
    
    # Rota para exibir resultados do processamento
    @app.route('/resultados/<tipo>')
    def resultados(tipo):
        # Carregar jogos disponíveis
        jogos = coletor.carregar_jogos()
        
        # Carregar estatísticas para o primeiro jogo (se houver)
        estatisticas = None
        if jogos:
            estatisticas = coletor.carregar_estatisticas(jogos[0]['id_jogo'])
        
        return render_template('resultados.html', tipo=tipo, jogos=jogos, estatisticas=estatisticas)
    
    # Rota para buscar jogo específico
    @app.route('/buscar-jogo', methods=['GET', 'POST'])
    def buscar_jogo():
        form = FormBuscaJogo()
        
        if form.validate_on_submit():
            time_casa = form.time_casa.data
            time_visitante = form.time_visitante.data
            
            try:
                # Buscar estatísticas para o jogo
                estatisticas = coletor.parser.obter_estatisticas_jogo(time_casa, time_visitante)
                
                # Gerar ID para o jogo
                id_jogo = f"{time_casa.lower().replace(' ', '_')}_{time_visitante.lower().replace(' ', '_')}_manual"
                
                # Salvar estatísticas
                coletor._salvar_estatisticas(id_jogo, estatisticas)
                
                # Criar jogo
                jogo = {
                    'id_jogo': id_jogo,
                    'time_casa': time_casa,
                    'time_visitante': time_visitante,
                    'data': 'N/A',
                    'hora': 'N/A',
                    'campeonato': 'Brasileirão Série A'
                }
                
                # Salvar jogo
                coletor._salvar_jogos([jogo])
                
                flash(f'Estatísticas para {time_casa} vs {time_visitante} coletadas com sucesso!', 'success')
                return redirect(url_for('visualizar_estatisticas', id_jogo=id_jogo))
                
            except Exception as e:
                logger.error(f"Erro ao buscar estatísticas: {str(e)}")
                flash(f'Erro ao buscar estatísticas: {str(e)}', 'danger')
        
        return render_template('buscar_jogo.html', form=form)
    
    # Rota para visualizar estatísticas de um jogo
    @app.route('/estatisticas/<id_jogo>')
    def visualizar_estatisticas(id_jogo):
        # Carregar estatísticas do jogo
        estatisticas = coletor.carregar_estatisticas(id_jogo)
        
        if not estatisticas:
            flash(f'Estatísticas não encontradas para o jogo {id_jogo}', 'warning')
            return redirect(url_for('index'))
        
        # Carregar jogos para encontrar o jogo específico
        jogos = coletor.carregar_jogos()
        jogo = next((j for j in jogos if j['id_jogo'] == id_jogo), None)
        
        return render_template('visualizar_estatisticas.html', jogo=jogo, estatisticas=estatisticas)
    
    # API para obter jogos disponíveis
    @app.route('/api/jogos')
    def api_jogos():
        jogos = coletor.carregar_jogos()
        return jsonify({"jogos": jogos})
    
    # API para obter estatísticas de um jogo
    @app.route('/api/estatisticas/<id_jogo>')
    def api_estatisticas(id_jogo):
        estatisticas = coletor.carregar_estatisticas(id_jogo)
        
        if not estatisticas:
            return jsonify({"erro": "Estatísticas não encontradas"}), 404
            
        return jsonify(estatisticas)
    
    # API para processar texto copiado
    @app.route('/api/processar-texto', methods=['POST'])
    def api_processar_texto():
        if not request.json or 'texto' not in request.json:
            return jsonify({"erro": "Texto não fornecido"}), 400
            
        texto = request.json['texto']
        
        try:
            resultado = coletor.processar_texto_copiado(texto)
            return jsonify(resultado)
            
        except Exception as e:
            logger.error(f"Erro ao processar texto copiado: {str(e)}")
            return jsonify({"erro": str(e)}), 500
    
    return app

# Criar diretórios para templates e arquivos estáticos
def criar_diretorio_templates():
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

# Criar templates HTML
def criar_templates():
    # Template base
    with open('templates/base.html', 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Sistema de Apostas Esportivas{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <i class="fas fa-futbol me-2"></i>Sistema de Apostas Esportivas
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('index') }}">
                            <i class="fas fa-home me-1"></i>Início
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('buscar_jogo') }}">
                            <i class="fas fa-search me-1"></i>Buscar Jogo
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4 mb-5">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <footer class="footer bg-light py-3 mt-auto">
        <div class="container text-center">
            <span class="text-muted">Sistema de Apostas Esportivas &copy; 2025</span>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>""")
    
    # Template para entrada manual
    with open('templates/entrada_manual.html', 'w', encoding='utf-8') as f:
        f.write("""{% extends 'base.html' %}

{% block title %}Entrada Manual de Dados{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-8">
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0"><i class="fas fa-keyboard me-2"></i>Entrada Manual de Dados</h4>
            </div>
            <div class="card-body">
                <p class="card-text">
                    Cole abaixo o texto copiado do site Academia das Apostas Brasil. O sistema irá processar o texto
                    e extrair informações sobre jogos e estatísticas.
                </p>
                
                <form method="POST" action="{{ url_for('index') }}">
                    {{ form.hidden_tag() }}
                    
                    <div class="mb-3">
                        {{ form.tipo_conteudo.label(class="form-label") }}
                        {{ form.tipo_conteudo(class="form-select") }}
                        <div class="form-text">Selecione o tipo de conteúdo que você está colando.</div>
                    </div>
                    
                    <div class="mb-3">
                        {{ form.texto.label(class="form-label") }}
                        {{ form.texto(class="form-control", rows=15) }}
                        {% if form.texto.errors %}
                            <div class="invalid-feedback d-block">
                                {% for error in form.texto.errors %}
                                    {{ error }}
                                {% endfor %}
                            </div>
                        {% endif %}
                    </div>
                    
                    <div class="d-grid">
                        {{ form.submit(class="btn btn-primary btn-lg") }}
                    </div>
                </form>
            </div>
            <div class="card-footer">
                <div class="text-muted small">
                    <i class="fas fa-info-circle me-1"></i>
                    Dica: Para melhores resultados, copie o conteúdo completo da página, incluindo cabeçalhos e tabelas.
                </div>
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card shadow-sm">
            <div class="card-header bg-success text-white">
                <h4 class="mb-0"><i class="fas fa-futbol me-2"></i>Jogos Disponíveis</h4>
            </div>
            <div class="card-body">
                {% if jogos %}
                    <div class="list-group">
                        {% for jogo in jogos[:5] %}
                            <a href="{{ url_for('visualizar_estatisticas', id_jogo=jogo['id_jogo']) }}" class="list-group-item list-group-item-action">
                                <div class="d-flex w-100 justify-content-between">
                                    <h5 class="mb-1">{{ jogo['time_casa'] }} vs {{ jogo['time_visitante'] }}</h5>
                                    <small>{{ jogo['data'] }}</small>
                                </div>
                                <p class="mb-1">{{ jogo['hora'] }} - {{ jogo['campeonato'] }}</p>
                            </a>
                        {% endfor %}
                    </div>
                    
                    {% if jogos|length > 5 %}
                        <div class="text-center mt-3">
                            <span class="badge bg-secondary">+{{ jogos|length - 5 }} jogos</span>
                        </div>
                    {% endif %}
                {% else %}
                    <div class="alert alert-info mb-0">
                        <i class="fas fa-info-circle me-1"></i>
                        Nenhum jogo disponível. Cole o texto de uma página de jogos para começar.
                    </div>
                {% endif %}
            </div>
        </div>
        
        <div class="card shadow-sm mt-4">
            <div class="card-header bg-info text-white">
                <h4 class="mb-0"><i class="fas fa-question-circle me-2"></i>Ajuda</h4>
            </div>
            <div class="card-body">
                <h5>Como usar:</h5>
                <ol>
                    <li>Acesse o site <a href="https://www.academiadasapostas.com.br" target="_blank">Academia das Apostas Brasil</a></li>
                    <li>Navegue até a página do jogo que deseja analisar</li>
                    <li>Selecione todo o conteúdo da página (Ctrl+A)</li>
                    <li>Copie o conteúdo (Ctrl+C)</li>
                    <li>Cole o conteúdo no campo de texto ao lado (Ctrl+V)</li>
                    <li>Clique em "Processar"</li>
                </ol>
                
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-1"></i>
                    O processamento pode levar alguns segundos, dependendo da quantidade de texto.
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}""")
    
    # Template para resultados
    with open('templates/resultados.html', 'w', encoding='utf-8') as f:
        f.write("""{% extends 'base.html' %}

{% block title %}Resultados do Processamento{% endblock %}

{% block content %}
<div class="card shadow-sm">
    <div class="card-header bg-success text-white">
        <h4 class="mb-0"><i class="fas fa-check-circle me-2"></i>Resultados do Processamento</h4>
    </div>
    <div class="card-body">
        <div class="alert alert-success">
            <i class="fas fa-check-circle me-1"></i>
            O texto foi processado com sucesso!
        </div>
        
        <h5 class="mt-4">Jogos Encontrados:</h5>
        {% if jogos %}
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Data</th>
                            <th>Hora</th>
                            <th>Time Casa</th>
                            <th>Time Visitante</th>
                            <th>Campeonato</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for jogo in jogos %}
                            <tr>
                                <td>{{ jogo['data'] }}</td>
                                <td>{{ jogo['hora'] }}</td>
                                <td>{{ jogo['time_casa'] }}</td>
                                <td>{{ jogo['time_visitante'] }}</td>
                                <td>{{ jogo['campeonato'] }}</td>
                                <td>
                                    <a href="{{ url_for('visualizar_estatisticas', id_jogo=jogo['id_jogo']) }}" class="btn btn-sm btn-primary">
                                        <i class="fas fa-chart-bar me-1"></i>Estatísticas
                                    </a>
                                </td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        {% else %}
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-1"></i>
                Nenhum jogo foi encontrado no texto processado.
            </div>
        {% endif %}
        
        {% if estatisticas %}
            <h5 class="mt-4">Estatísticas Encontradas:</h5>
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-1"></i>
                Foram encontradas estatísticas para o jogo. Clique no botão "Estatísticas" na tabela acima para visualizá-las.
            </div>
        {% endif %}
        
        <div class="d-grid gap-2 d-md-flex justify-content-md-end mt-4">
            <a href="{{ url_for('index') }}" class="btn btn-secondary">
                <i class="fas fa-arrow-left me-1"></i>Voltar
            </a>
        </div>
    </div>
</div>
{% endblock %}""")
    
    # Template para buscar jogo
    with open('templates/buscar_jogo.html', 'w', encoding='utf-8') as f:
        f.write("""{% extends 'base.html' %}

{% block title %}Buscar Jogo{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0"><i class="fas fa-search me-2"></i>Buscar Jogo</h4>
            </div>
            <div class="card-body">
                <p class="card-text">
                    Informe os times para buscar estatísticas diretamente do site Academia das Apostas Brasil.
                </p>
                
                <form method="POST" action="{{ url_for('buscar_jogo') }}">
                    {{ form.hidden_tag() }}
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            {{ form.time_casa.label(class="form-label") }}
                            {{ form.time_casa(class="form-control") }}
                            {% if form.time_casa.errors %}
                                <div class="invalid-feedback d-block">
                                    {% for error in form.time_casa.errors %}
                                        {{ error }}
                                    {% endfor %}
                                </div>
                            {% endif %}
                        </div>
                        
                        <div class="col-md-6">
                            {{ form.time_visitante.label(class="form-label") }}
                            {{ form.time_visitante(class="form-control") }}
                            {% if form.time_visitante.errors %}
                                <div class="invalid-feedback d-block">
                                    {% for error in form.time_visitante.errors %}
                                        {{ error }}
                                    {% endfor %}
                                </div>
                            {% endif %}
                        </div>
                    </div>
                    
                    <div class="d-grid">
                        {{ form.submit(class="btn btn-primary btn-lg") }}
                    </div>
                </form>
            </div>
            <div class="card-footer">
                <div class="text-muted small">
                    <i class="fas fa-info-circle me-1"></i>
                    Dica: Digite os nomes dos times exatamente como aparecem no site Academia das Apostas Brasil.
                </div>
            </div>
        </div>
        
        <div class="card shadow-sm mt-4">
            <div class="card-header bg-info text-white">
                <h4 class="mb-0"><i class="fas fa-lightbulb me-2"></i>Sugestões de Times</h4>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h5>Brasileirão Série A:</h5>
                        <ul class="list-group">
                            <li class="list-group-item">Flamengo</li>
                            <li class="list-group-item">Palmeiras</li>
                            <li class="list-group-item">Corinthians</li>
                            <li class="list-group-item">São Paulo</li>
                            <li class="list-group-item">Fluminense</li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <h5>Mais times:</h5>
                        <ul class="list-group">
                            <li class="list-group-item">Vasco</li>
                            <li class="list-group-item">Botafogo</li>
                            <li class="list-group-item">Grêmio</li>
                            <li class="list-group-item">Internacional</li>
                            <li class="list-group-item">Cruzeiro</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}""")
    
    # Template para visualizar estatísticas
    with open('templates/visualizar_estatisticas.html', 'w', encoding='utf-8') as f:
        f.write("""{% extends 'base.html' %}

{% block title %}Estatísticas do Jogo{% endblock %}

{% block extra_css %}
<style>
    .stat-card {
        transition: transform 0.3s;
    }
    .stat-card:hover {
        transform: translateY(-5px);
    }
    .team-logo {
        width: 64px;
        height: 64px;
        object-fit: contain;
    }
    .team-form-badge {
        width: 25px;
        height: 25px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        margin-right: 5px;
        font-weight: bold;
    }
    .form-v {
        background-color: #28a745;
        color: white;
    }
    .form-e {
        background-color: #ffc107;
        color: black;
    }
    .form-d {
        background-color: #dc3545;
        color: white;
    }
</style>
{% endblock %}

{% block content %}
<div class="card shadow-sm mb-4">
    <div class="card-header bg-primary text-white">
        <div class="d-flex justify-content-between align-items-center">
            <h4 class="mb-0"><i class="fas fa-chart-bar me-2"></i>Estatísticas do Jogo</h4>
            <a href="{{ url_for('index') }}" class="btn btn-light btn-sm">
                <i class="fas fa-arrow-left me-1"></i>Voltar
            </a>
        </div>
    </div>
    <div class="card-body">
        {% if jogo %}
            <div class="row align-items-center mb-4">
                <div class="col-md-5 text-center">
                    <h4>{{ jogo['time_casa'] }}</h4>
                    <img src="https://via.placeholder.com/64?text={{ jogo['time_casa'][0] }}" alt="{{ jogo['time_casa'] }}" class="team-logo">
                </div>
                <div class="col-md-2 text-center">
                    <h3>VS</h3>
                    <div class="small text-muted">
                        {{ jogo['data'] }} - {{ jogo['hora'] }}
                    </div>
                </div>
                <div class="col-md-5 text-center">
                    <h4>{{ jogo['time_visitante'] }}</h4>
                    <img src="https://via.placeholder.com/64?text={{ jogo['time_visitante'][0] }}" alt="{{ jogo['time_visitante'] }}" class="team-logo">
                </div>
            </div>
        {% endif %}
        
        {% if estatisticas %}
            <!-- Odds -->
            {% if estatisticas.odds %}
                <div class="card mb-4">
                    <div class="card-header bg-success text-white">
                        <h5 class="mb-0"><i class="fas fa-money-bill-wave me-2"></i>Odds</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-4">
                                <div class="card stat-card h-100">
                                    <div class="card-header text-center">Resultado Final (1X2)</div>
                                    <div class="card-body">
                                        <div class="row text-center">
                                            <div class="col-4">
                                                <div class="h4">{{ estatisticas.odds.resultado.casa }}</div>
                                                <div class="small">Casa</div>
                                            </div>
                                            <div class="col-4">
                                                <div class="h4">{{ estatisticas.odds.resultado.empate }}</div>
                                                <div class="small">Empate</div>
                                            </div>
                                            <div class="col-4">
                                                <div class="h4">{{ estatisticas.odds.resultado.visitante }}</div>
                                                <div class="small">Fora</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="col-md-4">
                                <div class="card stat-card h-100">
                                    <div class="card-header text-center">Over/Under 2.5</div>
                                    <div class="card-body">
                                        <div class="row text-center">
                                            <div class="col-6">
                                                <div class="h4">{{ estatisticas.odds.over_under.over_2_5 }}</div>
                                                <div class="small">Over 2.5</div>
                                            </div>
                                            <div class="col-6">
                                                <div class="h4">{{ estatisticas.odds.over_under.under_2_5 }}</div>
                                                <div class="small">Under 2.5</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="col-md-4">
                                <div class="card stat-card h-100">
                                    <div class="card-header text-center">Ambas Marcam</div>
                                    <div class="card-body">
                                        <div class="row text-center">
                                            <div class="col-6">
                                                <div class="h4">{{ estatisticas.odds.ambos_marcam.sim }}</div>
                                                <div class="small">Sim</div>
                                            </div>
                                            <div class="col-6">
                                                <div class="h4">{{ estatisticas.odds.ambos_marcam.nao }}</div>
                                                <div class="small">Não</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            {% endif %}
            
            <!-- Estatísticas dos Times -->
            <div class="row">
                <div class="col-md-6">
                    <div class="card mb-4">
                        <div class="card-header bg-primary text-white">
                            <h5 class="mb-0">{{ jogo['time_casa'] }}</h5>
                        </div>
                        <div class="card-body">
                            {% if estatisticas.time_casa %}
                                <div class="row mb-3">
                                    <div class="col-6">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_casa.posicao }}</h3>
                                                <div class="small text-muted">Posição</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_casa.pontos }}</h3>
                                                <div class="small text-muted">Pontos</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="row mb-3">
                                    <div class="col-4">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_casa.vitorias }}</h3>
                                                <div class="small text-muted">Vitórias</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-4">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_casa.empates }}</h3>
                                                <div class="small text-muted">Empates</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-4">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_casa.derrotas }}</h3>
                                                <div class="small text-muted">Derrotas</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="row mb-3">
                                    <div class="col-6">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_casa.gols_marcados }}</h3>
                                                <div class="small text-muted">Gols Marcados</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_casa.gols_sofridos }}</h3>
                                                <div class="small text-muted">Gols Sofridos</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="card">
                                    <div class="card-header">Últimos Jogos</div>
                                    <div class="card-body text-center">
                                        {% for resultado in estatisticas.time_casa.ultimos_jogos %}
                                            <span class="team-form-badge form-{{ resultado|lower }}">{{ resultado }}</span>
                                        {% endfor %}
                                    </div>
                                </div>
                            {% else %}
                                <div class="alert alert-warning">
                                    <i class="fas fa-exclamation-triangle me-1"></i>
                                    Estatísticas não disponíveis para {{ jogo['time_casa'] }}.
                                </div>
                            {% endif %}
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="card mb-4">
                        <div class="card-header bg-danger text-white">
                            <h5 class="mb-0">{{ jogo['time_visitante'] }}</h5>
                        </div>
                        <div class="card-body">
                            {% if estatisticas.time_visitante %}
                                <div class="row mb-3">
                                    <div class="col-6">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_visitante.posicao }}</h3>
                                                <div class="small text-muted">Posição</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_visitante.pontos }}</h3>
                                                <div class="small text-muted">Pontos</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="row mb-3">
                                    <div class="col-4">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_visitante.vitorias }}</h3>
                                                <div class="small text-muted">Vitórias</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-4">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_visitante.empates }}</h3>
                                                <div class="small text-muted">Empates</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-4">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_visitante.derrotas }}</h3>
                                                <div class="small text-muted">Derrotas</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="row mb-3">
                                    <div class="col-6">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_visitante.gols_marcados }}</h3>
                                                <div class="small text-muted">Gols Marcados</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="card stat-card">
                                            <div class="card-body text-center">
                                                <h3>{{ estatisticas.time_visitante.gols_sofridos }}</h3>
                                                <div class="small text-muted">Gols Sofridos</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="card">
                                    <div class="card-header">Últimos Jogos</div>
                                    <div class="card-body text-center">
                                        {% for resultado in estatisticas.time_visitante.ultimos_jogos %}
                                            <span class="team-form-badge form-{{ resultado|lower }}">{{ resultado }}</span>
                                        {% endfor %}
                                    </div>
                                </div>
                            {% else %}
                                <div class="alert alert-warning">
                                    <i class="fas fa-exclamation-triangle me-1"></i>
                                    Estatísticas não disponíveis para {{ jogo['time_visitante'] }}.
                                </div>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Confrontos Diretos -->
            {% if estatisticas.confrontos_diretos %}
                <div class="card mb-4">
                    <div class="card-header bg-info text-white">
                        <h5 class="mb-0"><i class="fas fa-history me-2"></i>Confrontos Diretos</h5>
                    </div>
                    <div class="card-body">
                        <div class="row mb-4">
                            <div class="col-md-3">
                                <div class="card stat-card">
                                    <div class="card-body text-center">
                                        <h3>{{ estatisticas.confrontos_diretos.resumo.total }}</h3>
                                        <div class="small text-muted">Total de Jogos</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card stat-card">
                                    <div class="card-body text-center">
                                        <h3>{{ estatisticas.confrontos_diretos.resumo.vitorias_casa }}</h3>
                                        <div class="small text-muted">Vitórias {{ jogo['time_casa'] }}</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card stat-card">
                                    <div class="card-body text-center">
                                        <h3>{{ estatisticas.confrontos_diretos.resumo.empates }}</h3>
                                        <div class="small text-muted">Empates</div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="card stat-card">
                                    <div class="card-body text-center">
                                        <h3>{{ estatisticas.confrontos_diretos.resumo.vitorias_visitante }}</h3>
                                        <div class="small text-muted">Vitórias {{ jogo['time_visitante'] }}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        {% if estatisticas.confrontos_diretos.confrontos %}
                            <div class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>Data</th>
                                            <th>Mandante</th>
                                            <th>Placar</th>
                                            <th>Visitante</th>
                                            <th>Competição</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for confronto in estatisticas.confrontos_diretos.confrontos %}
                                            <tr>
                                                <td>{{ confronto.data }}</td>
                                                <td>{{ confronto.mandante }}</td>
                                                <td class="text-center"><strong>{{ confronto.placar }}</strong></td>
                                                <td>{{ confronto.visitante }}</td>
                                                <td>{{ confronto.competicao }}</td>
                                            </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% else %}
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-1"></i>
                                Não há histórico de confrontos diretos entre os times.
                            </div>
                        {% endif %}
                    </div>
                </div>
            {% endif %}
            
            <!-- Mercados Adicionais -->
            {% if estatisticas.mercados_adicionais %}
                <div class="card mb-4">
                    <div class="card-header bg-warning text-dark">
                        <h5 class="mb-0"><i class="fas fa-chart-pie me-2"></i>Mercados Adicionais</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <!-- Escanteios -->
                            <div class="col-md-6">
                                <div class="card mb-3">
                                    <div class="card-header bg-light">
                                        <h5 class="mb-0">Escanteios</h5>
                                    </div>
                                    <div class="card-body">
                                        <div class="table-responsive">
                                            <table class="table table-striped">
                                                <thead>
                                                    <tr>
                                                        <th>Estatística</th>
                                                        <th>{{ jogo['time_casa'] }}</th>
                                                        <th>{{ jogo['time_visitante'] }}</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td>Média por jogo</td>
                                                        <td>{{ estatisticas.mercados_adicionais.escanteios.time_casa.media_por_jogo }}</td>
                                                        <td>{{ estatisticas.mercados_adicionais.escanteios.time_visitante.media_por_jogo }}</td>
                                                    </tr>
                                                    <tr>
                                                        <td>Média 1º tempo</td>
                                                        <td>{{ estatisticas.mercados_adicionais.escanteios.time_casa.media_primeiro_tempo }}</td>
                                                        <td>{{ estatisticas.mercados_adicionais.escanteios.time_visitante.media_primeiro_tempo }}</td>
                                                    </tr>
                                                    <tr>
                                                        <td>Média 2º tempo</td>
                                                        <td>{{ estatisticas.mercados_adicionais.escanteios.time_casa.media_segundo_tempo }}</td>
                                                        <td>{{ estatisticas.mercados_adicionais.escanteios.time_visitante.media_segundo_tempo }}</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Cartões -->
                            <div class="col-md-6">
                                <div class="card mb-3">
                                    <div class="card-header bg-light">
                                        <h5 class="mb-0">Cartões</h5>
                                    </div>
                                    <div class="card-body">
                                        <div class="table-responsive">
                                            <table class="table table-striped">
                                                <thead>
                                                    <tr>
                                                        <th>Estatística</th>
                                                        <th>{{ jogo['time_casa'] }}</th>
                                                        <th>{{ jogo['time_visitante'] }}</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr>
                                                        <td>Média cartões amarelos</td>
                                                        <td>{{ estatisticas.mercados_adicionais.cartoes.time_casa.cartoes_amarelos_media }}</td>
                                                        <td>{{ estatisticas.mercados_adicionais.cartoes.time_visitante.cartoes_amarelos_media }}</td>
                                                    </tr>
                                                    <tr>
                                                        <td>Total cartões vermelhos</td>
                                                        <td>{{ estatisticas.mercados_adicionais.cartoes.time_casa.cartoes_vermelhos_total }}</td>
                                                        <td>{{ estatisticas.mercados_adicionais.cartoes.time_visitante.cartoes_vermelhos_total }}</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            {% endif %}
            
        {% else %}
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-1"></i>
                Estatísticas não encontradas para este jogo.
            </div>
        {% endif %}
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Código JavaScript para gráficos ou interatividade adicional
    });
</script>
{% endblock %}""")

# Criar arquivos CSS e JS
def criar_arquivos_estaticos():
    # CSS principal
    with open('static/css/style.css', 'w', encoding='utf-8') as f:
        f.write("""/* Estilos principais */
body {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.footer {
    margin-top: auto;
}

.card {
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
}

.card-header {
    font-weight: bold;
}

.btn {
    border-radius: 5px;
}

.list-group-item {
    transition: background-color 0.3s;
}

.list-group-item:hover {
    background-color: #f8f9fa;
}

/* Estilos para formulários */
textarea.form-control {
    resize: vertical;
}

/* Estilos para tabelas */
.table-responsive {
    border-radius: 5px;
    overflow: hidden;
}

.table th {
    background-color: #343a40;
    color: white;
}

/* Animações */
.fade-in {
    animation: fadeIn 0.5s;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}""")
    
    # JavaScript principal
    with open('static/js/main.js', 'w', encoding='utf-8') as f:
        f.write("""// Funções principais

// Fechar alertas automaticamente após 5 segundos
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-warning):not(.alert-danger)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

// Função para copiar texto para a área de transferência
function copyToClipboard(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    
    // Mostrar feedback
    const toast = document.createElement('div');
    toast.className = 'position-fixed bottom-0 end-0 p-3';
    toast.style.zIndex = '5';
    toast.innerHTML = `
        <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <strong class="me-auto">Sistema de Apostas</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                Texto copiado para a área de transferência!
            </div>
        </div>
    `;
    document.body.appendChild(toast);
    
    setTimeout(function() {
        document.body.removeChild(toast);
    }, 3000);
}

// Função para formatar dados JSON
function formatJSON(json) {
    if (typeof json === 'string') {
        json = JSON.parse(json);
    }
    return JSON.stringify(json, null, 2);
}""")

# Função principal
def main():
    # Criar diretórios e arquivos
    criar_diretorio_templates()
    criar_templates()
    criar_arquivos_estaticos()
    
    # Criar aplicação Flask
    app = criar_app()
    
    # Iniciar servidor
    if __name__ == '__main__':
        app.run(debug=True, host='0.0.0.0', port=5000)
    
    return app

# Executar se for o script principal
if __name__ == "__main__":
    main()
