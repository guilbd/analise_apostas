"""
Módulo para integração do otimizador de desempenho com a aplicação Flask
-----------------------------------------------------------------------
Este módulo atualiza a aplicação principal para incluir otimizações de desempenho.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import os
import json
import datetime
import sys

# Importar módulo de otimização de desempenho
from performance import PerformanceOptimizer

# Adicionar o diretório do sistema de apostas ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Importar módulos do sistema de apostas
try:
    from sistema_apostas.scrapers import coletor_jogos
    from sistema_apostas.analise import analisador_partidas
    from sistema_apostas.recomendacoes import gerador_recomendacoes
    from sistema_apostas.mercados_adicionais import analisador_mercados
    from sistema_apostas.cashout import calculador_cashout
    from sistema_apostas.utils import gerador_relatorio
    SISTEMA_APOSTAS_DISPONIVEL = True
except ImportError:
    print("Aviso: Módulos do sistema de apostas não encontrados. Usando dados de exemplo.")
    SISTEMA_APOSTAS_DISPONIVEL = False

# Importar módulo de autenticação
from auth import UserManager, User

# Inicializar a aplicação Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sistema-apostas-esportivas-key'
app.config['JOGOS_FILE'] = 'jogos_disponiveis.json'
app.config['RELATORIOS_DIR'] = 'relatorios'

# Configurações de otimização de desempenho
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 ano em segundos
app.config['COMPRESS_MIMETYPES'] = ['text/html', 'text/css', 'text/javascript', 'application/javascript', 'application/json']
app.config['COMPRESS_LEVEL'] = 6  # Nível de compressão gzip (1-9)
app.config['COMPRESS_MIN_SIZE'] = 500  # Tamanho mínimo para compressão (bytes)

# Inicializar otimizador de desempenho
performance_optimizer = PerformanceOptimizer(app)

# Configurar o sistema de login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'warning'

# Inicializar gerenciador de usuários
user_manager = UserManager()

# Garantir que o diretório de relatórios exista
os.makedirs(app.config['RELATORIOS_DIR'], exist_ok=True)

# Função para carregar usuário
@login_manager.user_loader
def load_user(user_id):
    return user_manager.get_user(user_id)

# Filtro Jinja para formatar timestamps
@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    if not timestamp:
        return '-'
    return datetime.datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

# Rota para a página inicial
@app.route('/')
def index():
    return render_template('index.html')

# Rota para login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Encontrar usuário pelo nome
        user = user_manager.get_user_by_username(username)
        
        if user and user.check_password(password):
            login_user(user)
            user_manager.update_last_login(user.id)
            flash('Login realizado com sucesso!', 'success')
            
            # Redirecionar para a página solicitada originalmente (se houver)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciais inválidas. Tente novamente.', 'danger')
    
    return render_template('login.html')

# Rota para logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('index'))

# Rota para o dashboard principal
@app.route('/dashboard')
@login_required
def dashboard():
    # Carregar jogos disponíveis
    jogos = []
    if os.path.exists(app.config['JOGOS_FILE']):
        with open(app.config['JOGOS_FILE'], 'r') as f:
            jogos = json.load(f)
    
    # Carregar relatórios existentes
    relatorios = []
    for filename in os.listdir(app.config['RELATORIOS_DIR']):
        if filename.startswith('relatorio_') and filename.endswith('.json'):
            relatorio_path = os.path.join(app.config['RELATORIOS_DIR'], filename)
            with open(relatorio_path, 'r') as f:
                relatorio = json.load(f)
                relatorios.append({
                    'filename': filename,
                    'jogo': relatorio.get('jogo', 'Desconhecido'),
                    'timestamp': relatorio.get('timestamp', 0),
                    'data': datetime.datetime.fromtimestamp(relatorio.get('timestamp', 0)).strftime('%d/%m/%Y %H:%M')
                })
    
    # Ordenar relatórios por data (mais recentes primeiro)
    relatorios.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('dashboard.html', jogos=jogos, relatorios=relatorios)

# Rota para coletar jogos
@app.route('/coletar-jogos', methods=['POST'])
@login_required
def coletar_jogos():
    try:
        if SISTEMA_APOSTAS_DISPONIVEL:
            jogos = coletor_jogos.coletar_jogos_do_dia()
        else:
            # Usar dados de exemplo se o sistema de apostas não estiver disponível
            jogos = []
            if os.path.exists(app.config['JOGOS_FILE']):
                with open(app.config['JOGOS_FILE'], 'r') as f:
                    jogos = json.load(f)
        
        # Salvar jogos em arquivo
        with open(app.config['JOGOS_FILE'], 'w') as f:
            json.dump(jogos, f, indent=2)
        
        flash(f'Coletados {len(jogos)} jogos com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao coletar jogos: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

# Rota para analisar jogo
@app.route('/analisar-jogo', methods=['POST'])
@login_required
def analisar_jogo():
    time_casa = request.form.get('time_casa')
    time_visitante = request.form.get('time_visitante')
    
    if not time_casa or not time_visitante:
        flash('Por favor, informe os times para análise.', 'warning')
        return redirect(url_for('dashboard'))
    
    try:
        if SISTEMA_APOSTAS_DISPONIVEL:
            # Analisar partida usando o sistema real
            analise = analisador_partidas.analisar(time_casa, time_visitante)
            recomendacoes = gerador_recomendacoes.gerar(analise)
            mercados_adicionais = analisador_mercados.analisar(analise)
            cashout = calculador_cashout.calcular(recomendacoes, analise)
            relatorio = gerador_relatorio.gerar_relatorio(time_casa, time_visitante, analise, recomendacoes, mercados_adicionais, cashout)
        else:
            # Usar dados de exemplo
            relatorio_exemplo_path = os.path.join(app.config['RELATORIOS_DIR'], 'relatorio_internacional_vs_coritiba_exemplo.json')
            if os.path.exists(relatorio_exemplo_path):
                with open(relatorio_exemplo_path, 'r') as f:
                    relatorio = json.load(f)
                    # Atualizar para os times solicitados
                    relatorio['jogo'] = f"{time_casa} vs {time_visitante}"
            else:
                # Criar relatório básico se não houver exemplo
                relatorio = {
                    "jogo": f"{time_casa} vs {time_visitante}",
                    "timestamp": datetime.datetime.now().timestamp(),
                    "recomendacoes": [
                        {
                            "tipo": "baixo_risco",
                            "aposta": "Under 3.5 gols",
                            "odd": 1.29,
                            "justificativa": "Recomendação de exemplo para demonstração."
                        }
                    ],
                    "escanteios": {
                        "recomendacoes": [
                            {
                                "aposta": "Over 8.5 escanteios",
                                "odd": 1.12,
                                "justificativa": "Recomendação de exemplo para demonstração."
                            }
                        ]
                    },
                    "cartoes": {
                        "recomendacoes": [
                            {
                                "aposta": "Over 3.5 cartões",
                                "odd": 1.12,
                                "justificativa": "Recomendação de exemplo para demonstração."
                            }
                        ]
                    },
                    "cashout": {
                        "momento": "Após 70 minutos, se estiver vencendo por 1 gol de diferença",
                        "valor_sugerido": "75% do valor potencial",
                        "justificativa": "Recomendação de exemplo para demonstração."
                    }
                }
        
        # Salvar relatório
        timestamp = datetime.datetime.now().timestamp()
        filename = f"relatorio_{time_casa.lower().replace(' ', '_')}_vs_{time_visitante.lower().replace(' ', '_')}_{int(timestamp)}.json"
        filepath = os.path.join(app.config['RELATORIOS_DIR'], filename)
        
        with open(filepath, 'w') as f:
            json.dump(relatorio, f, indent=2)
        
        flash(f'Análise completa para {time_casa} vs {time_visitante} gerada com sucesso!', 'success')
        return redirect(url_for('visualizar_relatorio', filename=filename))
    
    except Exception as e:
        flash(f'Erro ao analisar jogo: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

# Rota para visualizar relatório
@app.route('/relatorio/<filename>')
@login_required
def visualizar_relatorio(filename):
    filepath = os.path.join(app.config['RELATORIOS_DIR'], filename)
    
    if not os.path.exists(filepath):
        flash('Relatório não encontrado.', 'danger')
        return redirect(url_for('dashboard'))
    
    with open(filepath, 'r') as f:
        relatorio = json.load(f)
    
    return render_template('relatorio.html', relatorio=relatorio, filename=filename)

# Rota para gerenciamento de usuários (apenas admin)
@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    if not current_user.nivel_acesso == 'admin':
        flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    
    usuarios = list(user_manager.users.values())
    return render_template('admin_usuarios.html', usuarios=usuarios)

# Rota para criar usuário (apenas admin)
@app.route('/admin/usuarios/criar', methods=['GET', 'POST'])
@login_required
def admin_criar_usuario():
    if not current_user.nivel_acesso == 'admin':
        flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        nome_completo = request.form.get('nome_completo')
        nivel_acesso = request.form.get('nivel_acesso')
        
        if not username or not password:
            flash('Nome de usuário e senha são obrigatórios.', 'warning')
            return redirect(url_for('admin_criar_usuario'))
        
        success, result = user_manager.create_user(
            username=username,
            password=password,
            email=email,
            nome_completo=nome_completo,
            nivel_acesso=nivel_acesso
        )
        
        if success:
            flash(f'Usuário {username} criado com sucesso!', 'success')
            return redirect(url_for('admin_usuarios'))
        else:
            flash(f'Erro ao criar usuário: {result}', 'danger')
    
    return render_template('admin_criar_usuario.html')

# Rota para editar usuário (apenas admin)
@app.route('/admin/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_editar_usuario(user_id):
    if not current_user.nivel_acesso == 'admin':
        flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = user_manager.get_user(user_id)
    if not user:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('admin_usuarios'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        nome_completo = request.form.get('nome_completo')
        nivel_acesso = request.form.get('nivel_acesso')
        
        update_data = {
            'username': username,
            'email': email,
            'nome_completo': nome_completo,
            'nivel_acesso': nivel_acesso
        }
        
        if password:
            update_data['password'] = password
        
        success, result = user_manager.update_user(user_id, **update_data)
        
        if success:
            flash(f'Usuário {username} atualizado com sucesso!', 'success')
            return redirect(url_for('admin_usuarios'))
        else:
            flash(f'Erro ao atualizar usuário: {result}', 'danger')
    
    return render_template('admin_editar_usuario.html', user=user)

# Rota para excluir usuário (apenas admin)
@app.route('/admin/usuarios/excluir/<int:user_id>', methods=['POST'])
@login_required
def admin_excluir_usuario(user_id):
    if not current_user.nivel_acesso == 'admin':
        flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Não permitir excluir o próprio usuário
    if int(user_id) == current_user.id:
        flash('Não é possível excluir seu próprio usuário.', 'danger')
        return redirect(url_for('admin_usuarios'))
    
    success, message = user_manager.delete_user(user_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('admin_usuarios'))

# Rota para o manifesto do site
@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "Sistema Especialista em Apostas Esportivas",
        "short_name": "Apostas Esportivas",
        "description": "Sistema para análise de jogos e recomendações de apostas baseadas em dados",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0d6efd",
        "theme_color": "#0d6efd",
        "icons": [
            {
                "src": "/static/img/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/img/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

# Rota para o service worker
@app.route('/service-worker.js')
def service_worker():
    response = app.send_static_file('js/service-worker.js')
    response.headers['Content-Type'] = 'application/javascript'
    return response

# Rota para o sitemap
@app.route('/sitemap.xml')
def sitemap():
    response = app.send_static_file('sitemap.xml')
    response.headers['Content-Type'] = 'application/xml'
    return response

# Rota para o robots.txt
@app.route('/robots.txt')
def robots():
    response = app.send_static_file('robots.txt')
    response.headers['Content-Type'] = 'text/plain'
    return response

# Rota para API - listar jogos
@app.route('/api/jogos', methods=['GET'])
def api_jogos():
    if os.path.exists(app.config['JOGOS_FILE']):
        with open(app.config['JOGOS_FILE'], 'r') as f:
            jogos = json.load(f)
        return jsonify(jogos)
    else:
        return jsonify([])

# Rota para API - listar relatórios
@app.route('/api/relatorios', methods=['GET'])
def api_relatorios():
    relatorios = []
    for filename in os.listdir(app.config['RELATORIOS_DIR']):
        if filename.startswith('relatorio_') and filename.endswith('.json'):
            relatorio_path = os.path.join(app.config['RELATORIOS_DIR'], filename)
            with open(relatorio_path, 'r') as f:
                relatorio = json.load(f)
                relatorios.append({
                    'filename': filename,
                    'jogo': relatorio.get('jogo', 'Desconhecido'),
                    'timestamp': relatorio.get('timestamp', 0),
                    'data': datetime.datetime.fromtimestamp(relatorio.get('timestamp', 0)).strftime('%d/%m/%Y %H:%M')
                })
    
    # Ordenar relatórios por data (mais recentes primeiro)
    relatorios.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify(relatorios)

# Rota para API - obter relatório específico
@app.route('/api/relatorio/<filename>', methods=['GET'])
def api_relatorio(filename):
    filepath = os.path.join(app.config['RELATORIOS_DIR'], filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'Relatório não encontrado'}), 404
    
    with open(filepath, 'r') as f:
        relatorio = json.load(f)
    
    return jsonify(relatorio)

# Rota para API - analisar jogo
@app.route('/api/analisar', methods=['POST'])
def api_analisar():
    data = request.json
    time_casa = data.get('time_casa')
    time_visitante = data.get('time_visitante')
    
    if not time_casa or not time_visitante:
        return jsonify({'error': 'Times não informados'}), 400
    
    try:
        if SISTEMA_APOSTAS_DISPONIVEL:
            # Analisar partida usando o sistema real
            analise = analisador_partidas.analisar(time_casa, time_visitante)
            recomendacoes = gerador_recomendacoes.gerar(analise)
            mercados_adicionais = analisador_mercados.analisar(analise)
            cashout = calculador_cashout.calcular(recomendacoes, analise)
            relatorio = gerador_relatorio.gerar_relatorio(time_casa, time_visitante, analise, recomendacoes, mercados_adicionais, cashout)
        else:
            # Usar dados de exemplo
            relatorio_exemplo_path = os.path.join(app.config['RELATORIOS_DIR'], 'relatorio_internacional_vs_coritiba_exemplo.json')
            if os.path.exists(relatorio_exemplo_path):
                with open(relatorio_exemplo_path, 'r') as f:
                    relatorio = json.load(f)
                    # Atualizar para os times solicitados
                    relatorio['jogo'] = f"{time_casa} vs {time_visitante}"
            else:
                # Criar relatório básico se não houver exemplo
                relatorio = {
                    "jogo": f"{time_casa} vs {time_visitante}",
                    "timestamp": datetime.datetime.now().timestamp(),
                    "recomendacoes": [
                        {
                            "tipo": "baixo_risco",
                            "aposta": "Under 3.5 gols",
                            "odd": 1.29,
                            "justificativa": "Recomendação de exemplo para demonstração."
                        }
                    ]
                }
        
        # Salvar relatório
        timestamp = datetime.datetime.now().timestamp()
        filename = f"relatorio_{time_casa.lower().replace(' ', '_')}_vs_{time_visitante.lower().replace(' ', '_')}_{int(timestamp)}.json"
        filepath = os.path.join(app.config['RELATORIOS_DIR'], filename)
        
        with open(filepath, 'w') as f:
            json.dump(relatorio, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Análise completa para {time_casa} vs {time_visitante} gerada com sucesso!',
            'filename': filename,
            'relatorio': relatorio
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rota para análise de desempenho (apenas admin)
@app.route('/admin/performance')
@login_required
def admin_performance():
    if not current_user.nivel_acesso == 'admin':
        flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Analisar desempenho
    performance_report = performance_optimizer.analyze_performance()
    
    return render_template('admin_performance.html', report=performance_report)

# Iniciar a aplicação

# Configurações adicionais de segurança para produção
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True
app.config['REMEMBER_COOKIE_HTTPONLY'] = True

if __name__ == '__main__':
    # Otimizar imagens antes de iniciar o servidor
    performance_optimizer.optimize_images()
    
    # Gerar CSS crítico para templates principais
    performance_optimizer.generate_critical_css('index')
    performance_optimizer.generate_critical_css('dashboard')
    
    # Iniciar servidor
    # Configuração de produção - não iniciar servidor aqui
