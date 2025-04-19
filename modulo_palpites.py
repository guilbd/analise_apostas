from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
import json
import datetime
import sys
from academia_apostas_parser_palpites import coletar_palpites

# Função para integrar o módulo de palpites à aplicação web
def integrar_modulo_palpites(app):
    """
    Integra o módulo de geração de palpites à aplicação web Flask.
    
    Args:
        app: A aplicação Flask
    """
    
    # Rota para a página de palpites
    @app.route('/palpites')
    def palpites():
        return render_template('palpites.html')
    
    # API para coletar palpites
    @app.route('/api/coletar_palpites', methods=['POST'])
    def api_coletar_palpites():
        try:
            # Coletar palpites da Academia das Apostas Brasil
            palpites = coletar_palpites()
            
            # Salvar palpites em arquivo para histórico
            data_atual = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            diretorio_palpites = os.path.join(app.config.get('DATA_FOLDER', 'dados'), 'palpites')
            os.makedirs(diretorio_palpites, exist_ok=True)
            
            with open(os.path.join(diretorio_palpites, f'palpites_{data_atual}.json'), 'w') as f:
                json.dump(palpites, f, indent=2)
            
            return jsonify({
                'status': 'success',
                'message': f'Coletados palpites para {len(palpites)} jogos',
                'palpites': palpites
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Erro ao coletar palpites: {str(e)}'
            }), 500
    
    # Rota para visualizar histórico de palpites
    @app.route('/palpites/historico')
    def historico_palpites():
        diretorio_palpites = os.path.join(app.config.get('DATA_FOLDER', 'dados'), 'palpites')
        os.makedirs(diretorio_palpites, exist_ok=True)
        
        arquivos_palpites = [f for f in os.listdir(diretorio_palpites) if f.startswith('palpites_') and f.endswith('.json')]
        arquivos_palpites.sort(reverse=True)
        
        historico = []
        
        for arquivo in arquivos_palpites[:10]:  # Mostrar apenas os 10 mais recentes
            data_str = arquivo.replace('palpites_', '').replace('.json', '')
            try:
                data = datetime.datetime.strptime(data_str, '%Y%m%d_%H%M%S')
                data_formatada = data.strftime('%d/%m/%Y %H:%M:%S')
                
                historico.append({
                    'arquivo': arquivo,
                    'data': data_formatada
                })
            except:
                continue
        
        return render_template('historico_palpites.html', historico=historico)
    
    # Rota para visualizar um arquivo específico de palpites
    @app.route('/palpites/visualizar/<arquivo>')
    def visualizar_palpites(arquivo):
        diretorio_palpites = os.path.join(app.config.get('DATA_FOLDER', 'dados'), 'palpites')
        caminho_arquivo = os.path.join(diretorio_palpites, arquivo)
        
        if not os.path.exists(caminho_arquivo):
            flash('Arquivo de palpites não encontrado', 'error')
            return redirect(url_for('historico_palpites'))
        
        try:
            with open(caminho_arquivo, 'r') as f:
                palpites = json.load(f)
            
            return render_template('visualizar_palpites.html', palpites=palpites, arquivo=arquivo)
        except Exception as e:
            flash(f'Erro ao carregar arquivo de palpites: {str(e)}', 'error')
            return redirect(url_for('historico_palpites'))

# Função para ser chamada no app_production.py
def registrar_modulo_palpites(app):
    """
    Registra o módulo de palpites na aplicação principal.
    
    Args:
        app: A aplicação Flask
    """
    integrar_modulo_palpites(app)
    
    # Adicionar link no menu de navegação
    @app.context_processor
    def inject_palpites_menu():
        return {
            'tem_modulo_palpites': True
        }
