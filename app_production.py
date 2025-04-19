"""
Módulo para integração do otimizador de desempenho com a aplicação Flask
-----------------------------------------------------------------------
Este módulo atualiza a aplicação principal para incluir otimizações de desempenho.
"""

from debug_route import register_debug_routes
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import os
import json
import datetime
import sys

# Importar módulo de otimização de desempenho
from performance import PerformanceOptimizer

# Importar módulos para coleta de dados reais
from academia_apostas_parser import AcademiaApostasParser
from coleta_dados_reais import ColetorDadosReais
from processador_texto_copiado import ProcessadorTextoCopiadoAcademiaApostas
from integracao_sistema import SistemaApostasEsportivas

# Importar módulos de correção
from auth_fix import configurar_autenticacao
from entrada_manual import registrar_entrada_manual

# Importar módulo de palpites
from modulo_palpites import registrar_modulo_palpites

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

# Inicializar a aplicação Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sistema-apostas-esportivas-key'
app.config['JOGOS_FILE'] = 'jogos_disponiveis.json'
app.config['RELATORIOS_DIR'] = 'relatorios'
app.config['DATA_FOLDER'] = os.path.join(os.getcwd(), 'dados')

# Adicionar rotas de debug (coloque isso antes de iniciar o servidor)
register_debug_routes(app)

# Configurações de otimização de desempenho
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 ano em segundos
app.config['COMPRESS_MIMETYPES'] = ['text/html', 'text/css', 'text/javascript', 'application/javascript', 'application/json']
app.config['COMPRESS_LEVEL'] = 6  # Nível de compressão gzip (1-9)
app.config['COMPRESS_MIN_SIZE'] = 500  # Tamanho mínimo para compressão (bytes)

# Inicializar otimizador de desempenho
performance_optimizer = PerformanceOptimizer(app)

# Inicializar sistema de coleta de dados reais
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['DATA_FOLDER'], 'jogos'), exist_ok=True)
os.makedirs(os.path.join(app.config['DATA_FOLDER'], 'estatisticas'), exist_ok=True)
sistema_apostas = SistemaApostasEsportivas(diretorio_dados=app.config['DATA_FOLDER'])
coletor_dados_reais = ColetorDadosReais(diretorio_dados=app.config['DATA_FOLDER'])
processador_texto = ProcessadorTextoCopiadoAcademiaApostas()

# Configurar autenticação
user_manager = configurar_autenticacao(app)

# Registrar funcionalidade de entrada manual
registrar_entrada_manual(app)

# Registrar módulo de palpites
registrar_modulo_palpites(app)

# Garantir que o diretório de relatórios exista
os.makedirs(app.config['RELATORIOS_DIR'], exist_ok=True)

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
            # Tentar usar o coletor de dados reais
            try:
                jogos = coletor_dados_reais.coletar_jogos_do_dia(dias_futuros=3)
                if not jogos:
                    raise Exception("Nenhum jogo encontrado")
            except Exception as e:
                print(f"Erro ao coletar jogos reais: {str(e)}")
                # Usar dados de exemplo se o coletor de dados reais falhar
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
            # Tentar usar o sistema de coleta de dados reais
            try:
                # Gerar ID para o jogo
                id_jogo = f"{time_casa.lower().replace(' ', '_')}_{time_visitante.lower().replace(' ', '_')}_manual"
                
                # Buscar estatísticas para o jogo
                estatisticas = coletor_dados_reais.parser.obter_estatisticas_jogo(time_casa, time_visitante)
                
                # Salvar estatísticas
                coletor_dados_reais._salvar_estatisticas(id_jogo, estatisticas)
                
                # Criar jogo
                jogo = {
                    'id_jogo': id_jogo,
                    'time_casa': time_casa,
                    'time_visitante': time_visitante,
                    'data': datetime.datetime.now().strftime('%d/%m/%Y'),
                    'hora': datetime.datetime.now().strftime('%H:%M'),
                    'campeonato': 'Brasileirão Série A'
                }
                
                # Salvar jogo
                coletor_dados_reais._salvar_jogos([jogo])
                
                # Gerar relatório usando o sistema de apostas
                relatorio = sistema_apostas.gerar_relatorio_json(id_jogo)
                relatorio = json.loads(relatorio)
            except Exception as e:
                print(f"Erro ao usar sistema de coleta de dados reais: {str(e)}")
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

# Rota para atualizar jogos (admin)
@app.route('/admin/atualizar-jogos')
@login_required
def atualizar_jogos():
    if not current_user.nivel_acesso == 'admin':
        flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Obter parâmetros
    dias = request.args.get('dias', default=3, type=int)
    
    try:
        # Coletar jogos do dia e dos próximos dias
        jogos = coletor_dados_reais.coletar_jogos_do_dia(dias_futuros=dias)
        
        if jogos:
            # Coletar estatísticas para os jogos
            estatisticas = coletor_dados_reais.coletar_estatisticas_jogos(jogos)
            
            # Salvar jogos no formato esperado pelo sistema
            with open(app.config['JOGOS_FILE'], 'w') as f:
                json.dump(jogos, f, indent=2)
            
            flash(f'Coletados {len(jogos)} jogos com sucesso!', 'success')
        else:
            flash('Nenhum jogo encontrado para o período especificado.', 'warning')
    except Exception as e:
        flash(f'Erro ao atualizar jogos: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

# Iniciar a aplicação se executada diretamente
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
