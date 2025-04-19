"""
Módulo para integração da funcionalidade de entrada manual de dados
"""

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
import json
import os
import re
import datetime

def processar_texto_copiado(texto):
    """
    Processa texto copiado do site Academia das Apostas Brasil
    """
    resultado = {
        'jogos': [],
        'tabela_classificacao': []
    }
    
    # Verificar se o texto está vazio
    if not texto or len(texto.strip()) < 10:
        return {'erro': 'Texto muito curto ou vazio'}
    
    linhas = texto.strip().split('\n')
    linhas = [l.strip() for l in linhas if l.strip()]
    
    # Tentar identificar jogos
    for i in range(len(linhas) - 2):
        if 'vs' in linhas[i] and i+2 < len(linhas):
            # Possível jogo encontrado
            times = linhas[i].split('vs')
            if len(times) == 2:
                time_casa = times[0].strip()
                time_visitante = times[1].strip()
                
                # Verificar se a próxima linha contém data/hora
                data_hora = ""
                campeonato = ""
                
                if i+1 < len(linhas) and re.search(r'\d{2}/\d{2}/\d{4}', linhas[i+1]):
                    data_hora = linhas[i+1].strip()
                    
                    # Verificar se a linha seguinte contém o campeonato
                    if i+2 < len(linhas) and ('Brasileirão' in linhas[i+2] or 'Série' in linhas[i+2] or 'Copa' in linhas[i+2] or 'Campeonato' in linhas[i+2]):
                        campeonato = linhas[i+2].strip()
                    else:
                        campeonato = "Campeonato não identificado"
                
                    # Extrair data e hora
                    data = data_hora.split(' - ')[0] if ' - ' in data_hora else data_hora
                    hora = data_hora.split(' - ')[1] if ' - ' in data_hora else '00:00'
                    
                    # Gerar ID único para o jogo
                    id_jogo = f"{time_casa.lower().replace(' ', '_')}_{time_visitante.lower().replace(' ', '_')}_{data.replace('/', '')}"
                    
                    # Criar objeto do jogo
                    jogo = {
                        'id_jogo': id_jogo,
                        'time_casa': time_casa,
                        'time_visitante': time_visitante,
                        'data': data,
                        'hora': hora,
                        'campeonato': campeonato
                    }
                    
                    # Adicionar à lista de jogos
                    resultado['jogos'].append(jogo)
    
    # Tentar identificar tabela de classificação
    posicao_pattern = re.compile(r'Posição:\s*(\d+)')
    pontos_pattern = re.compile(r'Pontos:\s*(\d+)')
    vitorias_pattern = re.compile(r'Vitórias:\s*(\d+)')
    
    for i in range(len(linhas)):
        if i+6 < len(linhas) and posicao_pattern.search(linhas[i+1]) and pontos_pattern.search(linhas[i+2]) and vitorias_pattern.search(linhas[i+3]):
            time = linhas[i].strip()
            posicao = int(posicao_pattern.search(linhas[i+1]).group(1))
            pontos = int(pontos_pattern.search(linhas[i+2]).group(1))
            
            # Adicionar à tabela de classificação
            resultado['tabela_classificacao'].append({
                'time': time,
                'posicao': posicao,
                'pontos': pontos
            })
    
    return resultado

def registrar_entrada_manual(app):
    """
    Registra as rotas para entrada manual de dados
    """
    
    @app.route('/entrada-manual', methods=['GET', 'POST'])
    @login_required
    def entrada_manual():
        if request.method == 'POST':
            texto_copiado = request.form.get('texto_copiado', '')
            tipo_conteudo = request.form.get('tipo_conteudo', 'auto')
            
            if not texto_copiado:
                flash('Por favor, cole o texto copiado do site Academia das Apostas Brasil.', 'warning')
                return render_template('entrada_manual.html')
            
            try:
                # Processar texto copiado
                resultado = processar_texto_copiado(texto_copiado)
                
                if 'erro' in resultado:
                    flash(f'Erro ao processar texto: {resultado["erro"]}', 'danger')
                    return render_template('entrada_manual.html', texto_copiado=texto_copiado)
                
                # Verificar resultados
                if 'jogos' in resultado and resultado['jogos']:
                    # Salvar jogos em arquivo
                    jogos_file = app.config.get('JOGOS_FILE', 'jogos_disponiveis.json')
                    
                    jogos_existentes = []
                    if os.path.exists(jogos_file):
                        try:
                            with open(jogos_file, 'r') as f:
                                jogos_existentes = json.load(f)
                        except:
                            jogos_existentes = []
                    
                    # Adicionar novos jogos
                    ids_existentes = [j.get('id_jogo') for j in jogos_existentes]
                    novos_jogos = 0
                    
                    for jogo in resultado['jogos']:
                        if jogo['id_jogo'] not in ids_existentes:
                            jogos_existentes.append(jogo)
                            novos_jogos += 1
                    
                    # Salvar jogos atualizados
                    with open(jogos_file, 'w') as f:
                        json.dump(jogos_existentes, f, indent=2)
                    
                    flash(f'Processamento concluído com sucesso! {novos_jogos} novos jogos adicionados.', 'success')
                    return redirect(url_for('dashboard'))
                    
                elif 'tabela_classificacao' in resultado and resultado['tabela_classificacao']:
                    flash(f'Tabela de classificação processada com sucesso! {len(resultado["tabela_classificacao"])} times encontrados.', 'success')
                    return redirect(url_for('dashboard'))
                    
                else:
                    flash('Nenhum jogo ou tabela encontrada no texto. Verifique o conteúdo e tente novamente.', 'warning')
                    return render_template('entrada_manual.html', texto_copiado=texto_copiado)
                
            except Exception as e:
                flash(f'Erro ao processar texto: {str(e)}', 'danger')
                return render_template('entrada_manual.html', texto_copiado=texto_copiado)
        
        return render_template('entrada_manual.html')
