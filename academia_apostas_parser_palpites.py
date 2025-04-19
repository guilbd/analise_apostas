import requests
from bs4 import BeautifulSoup
import re
import json
import numpy as np
from scipy.stats import poisson
import pandas as pd
from datetime import datetime

class AcademiaApostasParser:
    """
    Módulo para coletar dados da Academia das Apostas Brasil e gerar palpites
    baseados em análise estatística para diversos mercados.
    """
    
    def __init__(self):
        self.base_url = "https://www.academiadasapostasbrasil.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.session = requests.Session()
        # Confirmar que é maior de idade (necessário para acessar o site)
        self.session.cookies.set("age_check", "1")
    
    def get_jogos_do_dia(self):
        """Coleta os jogos do dia da página inicial da Academia das Apostas Brasil"""
        try:
            url = f"{self.base_url}/stats"
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            jogos_hoje = []
            
            # Encontrar a seção de jogos do dia
            jogos_section = soup.find('div', class_='matches-today')
            if not jogos_section:
                return jogos_hoje
                
            jogos_items = jogos_section.find_all('div', class_='match-item')
            
            for jogo in jogos_items:
                try:
                    # Extrair informações básicas do jogo
                    equipes = jogo.find('div', class_='teams').text.strip()
                    casa, fora = equipes.split(' vs ')
                    
                    # Extrair link para estatísticas detalhadas
                    link_element = jogo.find('a', href=True)
                    link = link_element['href'] if link_element else None
                    
                    # Extrair competição e horário
                    competicao = jogo.find('div', class_='competition').text.strip()
                    horario = jogo.find('div', class_='time').text.strip()
                    
                    jogos_hoje.append({
                        'casa': casa.strip(),
                        'fora': fora.strip(),
                        'competicao': competicao,
                        'horario': horario,
                        'link': f"{self.base_url}{link}" if link else None
                    })
                except Exception as e:
                    print(f"Erro ao processar jogo: {e}")
                    continue
            
            return jogos_hoje
        
        except Exception as e:
            print(f"Erro ao coletar jogos do dia: {e}")
            return []
    
    def get_estatisticas_jogo(self, link):
        """Coleta estatísticas detalhadas de um jogo específico"""
        try:
            response = self.session.get(link, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            estatisticas = {
                'casa': {},
                'fora': {},
                'confrontos_diretos': [],
                'odds': {}
            }
            
            # Extrair nomes das equipes
            equipe_casa = soup.select_one('a[href*="/team/"]').text.strip()
            equipe_fora = soup.select_one('a[href*="/team/"]').text.strip()
            estatisticas['casa']['nome'] = equipe_casa
            estatisticas['fora']['nome'] = equipe_fora
            
            # Extrair estatísticas da equipe da casa
            tabela_casa = soup.find('table', {'class': 'team-stats'})
            if tabela_casa:
                rows = tabela_casa.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        stat_name = cols[0].text.strip()
                        stat_value = cols[1].text.strip()
                        estatisticas['casa'][stat_name] = stat_value
            
            # Extrair estatísticas da equipe visitante
            tabela_fora = soup.find_all('table', {'class': 'team-stats'})[1] if len(soup.find_all('table', {'class': 'team-stats'})) > 1 else None
            if tabela_fora:
                rows = tabela_fora.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        stat_name = cols[0].text.strip()
                        stat_value = cols[2].text.strip()
                        estatisticas['fora'][stat_name] = stat_value
            
            # Extrair confrontos diretos
            tabela_confrontos = soup.find('table', {'class': 'h2h-table'})
            if tabela_confrontos:
                rows = tabela_confrontos.find_all('tr')[1:]  # Pular cabeçalho
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        data = cols[0].text.strip()
                        casa = cols[1].text.strip()
                        resultado = cols[2].text.strip()
                        fora = cols[3].text.strip()
                        estatisticas['confrontos_diretos'].append({
                            'data': data,
                            'casa': casa,
                            'resultado': resultado,
                            'fora': fora
                        })
            
            # Extrair odds
            tabela_odds = soup.find('table', {'class': 'odds-table'})
            if tabela_odds:
                rows = tabela_odds.find_all('tr')[1:]  # Pular cabeçalho
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        casa_de_apostas = cols[0].text.strip()
                        odd_casa = cols[1].text.strip()
                        odd_empate = cols[2].text.strip()
                        odd_fora = cols[3].text.strip()
                        estatisticas['odds'][casa_de_apostas] = {
                            'casa': float(odd_casa) if odd_casa and odd_casa != '-' else None,
                            'empate': float(odd_empate) if odd_empate and odd_empate != '-' else None,
                            'fora': float(odd_fora) if odd_fora and odd_fora != '-' else None
                        }
            
            # Extrair últimos jogos de cada equipe
            ultimos_jogos_casa = []
            ultimos_jogos_fora = []
            
            tabela_ultimos_casa = soup.find('table', {'class': 'last-matches-table'})
            if tabela_ultimos_casa:
                rows = tabela_ultimos_casa.find_all('tr')[1:]  # Pular cabeçalho
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        data = cols[0].text.strip()
                        adversario = cols[2].text.strip()
                        resultado = cols[1].text.strip()
                        ultimos_jogos_casa.append({
                            'data': data,
                            'adversario': adversario,
                            'resultado': resultado
                        })
            
            tabela_ultimos_fora = soup.find_all('table', {'class': 'last-matches-table'})[1] if len(soup.find_all('table', {'class': 'last-matches-table'})) > 1 else None
            if tabela_ultimos_fora:
                rows = tabela_ultimos_fora.find_all('tr')[1:]  # Pular cabeçalho
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        data = cols[0].text.strip()
                        adversario = cols[2].text.strip()
                        resultado = cols[1].text.strip()
                        ultimos_jogos_fora.append({
                            'data': data,
                            'adversario': adversario,
                            'resultado': resultado
                        })
            
            estatisticas['casa']['ultimos_jogos'] = ultimos_jogos_casa
            estatisticas['fora']['ultimos_jogos'] = ultimos_jogos_fora
            
            return estatisticas
        
        except Exception as e:
            print(f"Erro ao coletar estatísticas do jogo: {e}")
            return None

    def extrair_dados_numericos(self, estatisticas):
        """Extrai e converte dados estatísticos para formato numérico para análise"""
        dados = {
            'casa': {},
            'fora': {}
        }
        
        # Extrair médias de gols
        try:
            dados['casa']['media_gols_marcados'] = float(re.search(r'(\d+\.\d+)', estatisticas['casa'].get('Média de gols marcados por jogo', '0')).group(1))
        except:
            dados['casa']['media_gols_marcados'] = 1.0
            
        try:
            dados['casa']['media_gols_sofridos'] = float(re.search(r'(\d+\.\d+)', estatisticas['casa'].get('Média de gols sofridos por jogo', '0')).group(1))
        except:
            dados['casa']['media_gols_sofridos'] = 1.0
            
        try:
            dados['fora']['media_gols_marcados'] = float(re.search(r'(\d+\.\d+)', estatisticas['fora'].get('Média de gols marcados por jogo', '0')).group(1))
        except:
            dados['fora']['media_gols_marcados'] = 0.7
            
        try:
            dados['fora']['media_gols_sofridos'] = float(re.search(r'(\d+\.\d+)', estatisticas['fora'].get('Média de gols sofridos por jogo', '0')).group(1))
        except:
            dados['fora']['media_gols_sofridos'] = 1.3
        
        # Extrair percentuais de jogos
        try:
            dados['casa']['jogos_sem_sofrer'] = int(re.search(r'(\d+)%', estatisticas['casa'].get('Jogos sem sofrer', '0%')).group(1)) / 100
        except:
            dados['casa']['jogos_sem_sofrer'] = 0.3
            
        try:
            dados['casa']['jogos_sem_marcar'] = int(re.search(r'(\d+)%', estatisticas['casa'].get('Jogos sem marcar gols', '0%')).group(1)) / 100
        except:
            dados['casa']['jogos_sem_marcar'] = 0.2
            
        try:
            dados['casa']['jogos_over_25'] = int(re.search(r'(\d+)%', estatisticas['casa'].get('Jogos com Mais de 2,5 Gols', '0%')).group(1)) / 100
        except:
            dados['casa']['jogos_over_25'] = 0.5
            
        try:
            dados['fora']['jogos_sem_sofrer'] = int(re.search(r'(\d+)%', estatisticas['fora'].get('Jogos sem sofrer', '0%')).group(1)) / 100
        except:
            dados['fora']['jogos_sem_sofrer'] = 0.2
            
        try:
            dados['fora']['jogos_sem_marcar'] = int(re.search(r'(\d+)%', estatisticas['fora'].get('Jogos sem marcar gols', '0%')).group(1)) / 100
        except:
            dados['fora']['jogos_sem_marcar'] = 0.3
            
        try:
            dados['fora']['jogos_over_25'] = int(re.search(r'(\d+)%', estatisticas['fora'].get('Jogos com Mais de 2,5 Gols', '0%')).group(1)) / 100
        except:
            dados['fora']['jogos_over_25'] = 0.4
        
        # Extrair dados de primeiro tempo
        try:
            dados['casa']['marca_primeiro'] = int(re.search(r'(\d+)%', estatisticas['casa'].get('Abre marcador (qualquer altura)', '0%')).group(1)) / 100
        except:
            dados['casa']['marca_primeiro'] = 0.6
            
        try:
            dados['fora']['marca_primeiro'] = int(re.search(r'(\d+)%', estatisticas['fora'].get('Abre marcador (qualquer altura)', '0%')).group(1)) / 100
        except:
            dados['fora']['marca_primeiro'] = 0.4
        
        # Calcular força de ataque e defesa (ajustados para casa/fora)
        media_gols_liga = 2.5  # Média típica de gols por jogo no futebol brasileiro
        
        dados['casa']['forca_ataque'] = dados['casa']['media_gols_marcados'] / (media_gols_liga / 2)
        dados['casa']['forca_defesa'] = dados['casa']['media_gols_sofridos'] / (media_gols_liga / 2)
        dados['fora']['forca_ataque'] = dados['fora']['media_gols_marcados'] / (media_gols_liga / 2)
        dados['fora']['forca_defesa'] = dados['fora']['media_gols_sofridos'] / (media_gols_liga / 2)
        
        # Extrair odds médias
        odds_casa = []
        odds_empate = []
        odds_fora = []
        
        for casa_apostas, odds in estatisticas.get('odds', {}).items():
            if odds.get('casa'):
                odds_casa.append(odds['casa'])
            if odds.get('empate'):
                odds_empate.append(odds['empate'])
            if odds.get('fora'):
                odds_fora.append(odds['fora'])
        
        dados['odds'] = {
            'casa': sum(odds_casa) / len(odds_casa) if odds_casa else 1.8,
            'empate': sum(odds_empate) / len(odds_empate) if odds_empate else 3.5,
            'fora': sum(odds_fora) / len(odds_fora) if odds_fora else 4.5
        }
        
        return dados

    def calcular_probabilidades_poisson(self, dados):
        """Calcula probabilidades usando distribuição de Poisson"""
        # Estimar número esperado de gols para cada equipe
        lambda_casa = dados['casa']['forca_ataque'] * dados['fora']['forca_defesa'] * 1.3  # Fator de vantagem em casa
        lambda_fora = dados['fora']['forca_ataque'] * dados['casa']['forca_defesa']
        
        # Calcular matriz de probabilidades para resultados exatos
        max_gols = 5  # Considerar até 5 gols por equipe
        matriz_prob = np.zeros((max_gols+1, max_gols+1))
        
        for i in range(max_gols+1):
            for j in range(max_gols+1):
                matriz_prob[i, j] = poisson.pmf(i, lambda_casa) * poisson.pmf(j, lambda_fora)
        
        # Calcular probabilidades para 1X2
        prob_casa = np.sum(np.tril(matriz_prob, -1))
        prob_empate = np.sum(np.diag(matriz_prob))
        prob_fora = np.sum(np.triu(matriz_prob, 1))
        
        # Calcular probabilidades para Over/Under
        prob_under_05 = matriz_prob[0, 0]
        prob_over_05 = 1 - prob_under_05
        
        prob_under_15 = np.sum(matriz_prob[0:2, 0:2]) - matriz_prob[1, 1]
        prob_over_15 = 1 - prob_under_15
        
        prob_under_25 = np.sum(matriz_prob[0:3, 0:3]) - matriz_prob[2, 1] - matriz_prob[1, 2]
        prob_over_25 = 1 - prob_under_25
        
        prob_under_35 = np.sum(matriz_prob[0:4, 0:4]) - matriz_prob[3, 1] - matriz_prob[2, 2] - matriz_prob[1, 3]
        prob_over_35 = 1 - prob_under_35
        
        # Calcular probabilidades para Ambas Marcam
        prob_ambas_sim = 1 - (np.sum(matriz_prob[0, :]) + np.sum(matriz_prob[:, 0]) - matriz_prob[0, 0])
        prob_ambas_nao = 1 - prob_ambas_sim
        
        # Calcular probabilidades para gols no primeiro tempo
        # Assumindo que 40% dos gols ocorrem no primeiro tempo
        lambda_casa_ht = lambda_casa * 0.4
        lambda_fora_ht = lambda_fora * 0.4
        
        prob_over_05_ht = 1 - (poisson.pmf(0, lambda_casa_ht) * poisson.pmf(0, lambda_fora_ht))
        prob_over_15_ht = 1 - (poisson.pmf(0, lambda_casa_ht) * poisson.pmf(0, lambda_fora_ht) + 
                              poisson.pmf(1, lambda_casa_ht) * poisson.pmf(0, lambda_fora_ht) + 
                              poisson.pmf(0, lambda_casa_ht) * poisson.pmf(1, lambda_fora_ht))
        
        # Encontrar os 3 resultados exatos mais prováveis
        resultados_exatos = []
        for i in range(max_gols+1):
            for j in range(max_gols+1):
                resultados_exatos.append(((i, j), matriz_prob[i, j]))
        
        resultados_exatos.sort(key=lambda x: x[1], reverse=True)
        top3_resultados = resultados_exatos[:3]
        
        # Calcular probabilidades para tempo com mais gols
        # Assumindo que 40% dos gols ocorrem no primeiro tempo e 60% no segundo
        prob_mais_gols_1t = 0.2
        prob_mais_gols_2t = 0.6
        prob_igual = 0.2
        
        return {
            '1x2': {
                'casa': prob_casa,
                'empate': prob_empate,
                'fora': prob_fora
            },
            'over_under': {
                'over_05': prob_over_05,
                'under_05': prob_under_05,
                'over_15': prob_over_15,
                'under_15': prob_under_15,
                'over_25': prob_over_25,
                'under_25': prob_under_25,
                'over_35': prob_over_35,
                'under_35': prob_under_35
            },
            'ambas_marcam': {
                'sim': prob_ambas_sim,
                'nao': prob_ambas_nao
            },
            'gols_ht': {
                'over_05': prob_over_05_ht,
                'under_05': 1 - prob_over_05_ht,
                'over_15': prob_over_15_ht,
                'under_15': 1 - prob_over_15_ht
            },
            'resultado_exato': [
                {'resultado': f"{res[0][0]}-{res[0][1]}", 'probabilidade': res[1]}
                for res in top3_resultados
            ],
            'gols_por_equipe': {
                'casa_over_05': 1 - poisson.pmf(0, lambda_casa),
                'casa_over_15': 1 - poisson.pmf(0, lambda_casa) - poisson.pmf(1, lambda_casa),
                'fora_over_05': 1 - poisson.pmf(0, lambda_fora),
                'fora_over_15': 1 - poisson.pmf(0, lambda_fora) - poisson.pmf(1, lambda_fora)
            },
            'tempo_mais_gols': {
                'primeiro': prob_mais_gols_1t,
                'segundo': prob_mais_gols_2t,
                'igual': prob_igual
            },
            'handicap_asiatico': self.calcular_handicap_asiatico(lambda_casa, lambda_fora)
        }
    
    def calcular_handicap_asiatico(self, lambda_casa, lambda_fora):
        """Calcula probabilidades para handicap asiático"""
        handicaps = {}
        
        # Calcular para diferentes linhas de handicap
        for linha in [-2.0, -1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5, 2.0]:
            # Simular 10000 resultados
            np.random.seed(42)  # Para reprodutibilidade
            gols_casa = np.random.poisson(lambda_casa, 10000)
            gols_fora = np.random.poisson(lambda_fora, 10000)
            
            # Aplicar handicap
            resultados_handicap = (gols_casa - gols_fora) + linha
            
            # Calcular probabilidades
            prob_casa = np.mean(resultados_handicap > 0)
            prob_empate = np.mean(resultados_handicap == 0)
            prob_fora = np.mean(resultados_handicap < 0)
            
            handicaps[f"ha_{linha}"] = {
                'casa': prob_casa,
                'empate': prob_empate,
                'fora': prob_fora
            }
        
        return handicaps

    def gerar_palpites(self, probabilidades, dados):
        """Gera palpites com base nas probabilidades calculadas"""
        palpites = {}
        
        # Palpite para 1X2
        max_prob_1x2 = max(probabilidades['1x2'].items(), key=lambda x: x[1])
        palpites['1x2'] = {
            'palpite': max_prob_1x2[0],
            'probabilidade': max_prob_1x2[1],
            'odd_referencia': dados['odds'].get(max_prob_1x2[0], 2.0),
            'valor_esperado': max_prob_1x2[1] * dados['odds'].get(max_prob_1x2[0], 2.0)
        }
        
        # Palpite para Over/Under
        if probabilidades['over_under']['over_25'] > 0.55:
            palpites['over_under'] = {
                'palpite': 'over_25',
                'probabilidade': probabilidades['over_under']['over_25'],
                'odd_referencia': 1.9
            }
        elif probabilidades['over_under']['under_25'] > 0.55:
            palpites['over_under'] = {
                'palpite': 'under_25',
                'probabilidade': probabilidades['over_under']['under_25'],
                'odd_referencia': 1.9
            }
        else:
            # Verificar outras linhas
            for linha in ['over_15', 'under_35', 'over_35']:
                if probabilidades['over_under'][linha] > 0.6:
                    palpites['over_under'] = {
                        'palpite': linha,
                        'probabilidade': probabilidades['over_under'][linha],
                        'odd_referencia': 1.8
                    }
                    break
        
        # Palpite para Ambas Marcam
        if max(probabilidades['ambas_marcam']['sim'], probabilidades['ambas_marcam']['nao']) > 0.6:
            max_prob_ambas = max(probabilidades['ambas_marcam'].items(), key=lambda x: x[1])
            palpites['ambas_marcam'] = {
                'palpite': max_prob_ambas[0],
                'probabilidade': max_prob_ambas[1],
                'odd_referencia': 1.9
            }
        
        # Palpite para Gols HT
        if probabilidades['gols_ht']['over_05'] > 0.65:
            palpites['gols_ht'] = {
                'palpite': 'over_05',
                'probabilidade': probabilidades['gols_ht']['over_05'],
                'odd_referencia': 1.7
            }
        elif probabilidades['gols_ht']['under_15'] > 0.65:
            palpites['gols_ht'] = {
                'palpite': 'under_15',
                'probabilidade': probabilidades['gols_ht']['under_15'],
                'odd_referencia': 1.7
            }
        
        # Palpite para Resultado Exato
        palpites['resultado_exato'] = probabilidades['resultado_exato']
        
        # Palpite para Gols por Equipe
        palpites['gols_por_equipe'] = {}
        
        if probabilidades['gols_por_equipe']['casa_over_15'] > 0.6:
            palpites['gols_por_equipe']['casa'] = {
                'palpite': 'over_15',
                'probabilidade': probabilidades['gols_por_equipe']['casa_over_15'],
                'odd_referencia': 2.0
            }
        elif probabilidades['gols_por_equipe']['casa_over_05'] > 0.7:
            palpites['gols_por_equipe']['casa'] = {
                'palpite': 'over_05',
                'probabilidade': probabilidades['gols_por_equipe']['casa_over_05'],
                'odd_referencia': 1.5
            }
        
        if probabilidades['gols_por_equipe']['fora_over_05'] > 0.6:
            palpites['gols_por_equipe']['fora'] = {
                'palpite': 'over_05',
                'probabilidade': probabilidades['gols_por_equipe']['fora_over_05'],
                'odd_referencia': 1.7
            }
        
        # Palpite para Tempo com Mais Gols
        max_prob_tempo = max(probabilidades['tempo_mais_gols'].items(), key=lambda x: x[1])
        if max_prob_tempo[1] > 0.5:
            palpites['tempo_mais_gols'] = {
                'palpite': max_prob_tempo[0],
                'probabilidade': max_prob_tempo[1],
                'odd_referencia': 2.0
            }
        
        # Palpite para Handicap Asiático
        melhor_handicap = None
        melhor_valor = 0
        
        for handicap, valores in probabilidades['handicap_asiatico'].items():
            # Verificar se há valor na aposta
            if valores['casa'] > 0.6 and valores['casa'] * 1.9 > melhor_valor:
                melhor_handicap = handicap
                melhor_valor = valores['casa'] * 1.9
                melhor_lado = 'casa'
            elif valores['fora'] > 0.6 and valores['fora'] * 1.9 > melhor_valor:
                melhor_handicap = handicap
                melhor_valor = valores['fora'] * 1.9
                melhor_lado = 'fora'
        
        if melhor_handicap:
            linha = float(melhor_handicap.split('_')[1])
            palpites['handicap_asiatico'] = {
                'palpite': f"{melhor_lado} ({linha:+g})",
                'probabilidade': probabilidades['handicap_asiatico'][melhor_handicap][melhor_lado],
                'odd_referencia': 1.9
            }
        
        return palpites

    def processar_jogo(self, jogo):
        """Processa um jogo completo, coletando estatísticas e gerando palpites"""
        if not jogo.get('link'):
            return None
            
        # Coletar estatísticas detalhadas
        estatisticas = self.get_estatisticas_jogo(jogo['link'])
        if not estatisticas:
            return None
            
        # Extrair dados numéricos
        dados = self.extrair_dados_numericos(estatisticas)
        
        # Calcular probabilidades
        probabilidades = self.calcular_probabilidades_poisson(dados)
        
        # Gerar palpites
        palpites = self.gerar_palpites(probabilidades, dados)
        
        return {
            'jogo': jogo,
            'estatisticas': estatisticas,
            'dados_numericos': dados,
            'probabilidades': probabilidades,
            'palpites': palpites
        }

    def processar_jogos_do_dia(self):
        """Processa todos os jogos do dia e gera palpites"""
        jogos = self.get_jogos_do_dia()
        resultados = []
        
        for jogo in jogos:
            resultado = self.processar_jogo(jogo)
            if resultado:
                resultados.append(resultado)
        
        return resultados

# Função para ser chamada pela interface web
def coletar_palpites():
    parser = AcademiaApostasParser()
    resultados = parser.processar_jogos_do_dia()
    
    # Formatar resultados para exibição na interface
    palpites_formatados = []
    
    for resultado in resultados:
        jogo = resultado['jogo']
        palpites = resultado['palpites']
        
        palpite_formatado = {
            'jogo': f"{jogo['casa']} vs {jogo['fora']}",
            'competicao': jogo['competicao'],
            'horario': jogo['horario'],
            'mercados': {}
        }
        
        # Formatar palpites por mercado
        if '1x2' in palpites:
            palpite_formatado['mercados']['1x2'] = {
                'palpite': palpites['1x2']['palpite'].upper(),
                'confianca': f"{palpites['1x2']['probabilidade']*100:.1f}%"
            }
        
        if 'over_under' in palpites:
            palpite_formatado['mercados']['over_under'] = {
                'palpite': palpites['over_under']['palpite'].replace('_', ' ').upper(),
                'confianca': f"{palpites['over_under']['probabilidade']*100:.1f}%"
            }
        
        if 'ambas_marcam' in palpites:
            palpite_formatado['mercados']['ambas_marcam'] = {
                'palpite': palpites['ambas_marcam']['palpite'].upper(),
                'confianca': f"{palpites['ambas_marcam']['probabilidade']*100:.1f}%"
            }
        
        if 'gols_ht' in palpites:
            palpite_formatado['mercados']['gols_ht'] = {
                'palpite': palpites['gols_ht']['palpite'].replace('_', ' ').upper(),
                'confianca': f"{palpites['gols_ht']['probabilidade']*100:.1f}%"
            }
        
        if 'resultado_exato' in palpites:
            palpite_formatado['mercados']['resultado_exato'] = [
                {
                    'palpite': res['resultado'],
                    'confianca': f"{res['probabilidade']*100:.1f}%"
                }
                for res in palpites['resultado_exato']
            ]
        
        if 'gols_por_equipe' in palpites:
            palpite_formatado['mercados']['gols_por_equipe'] = {}
            
            if 'casa' in palpites['gols_por_equipe']:
                palpite_formatado['mercados']['gols_por_equipe']['casa'] = {
                    'palpite': palpites['gols_por_equipe']['casa']['palpite'].replace('_', ' ').upper(),
                    'confianca': f"{palpites['gols_por_equipe']['casa']['probabilidade']*100:.1f}%"
                }
            
            if 'fora' in palpites['gols_por_equipe']:
                palpite_formatado['mercados']['gols_por_equipe']['fora'] = {
                    'palpite': palpites['gols_por_equipe']['fora']['palpite'].replace('_', ' ').upper(),
                    'confianca': f"{palpites['gols_por_equipe']['fora']['probabilidade']*100:.1f}%"
                }
        
        if 'tempo_mais_gols' in palpites:
            palpite_formatado['mercados']['tempo_mais_gols'] = {
                'palpite': palpites['tempo_mais_gols']['palpite'].upper(),
                'confianca': f"{palpites['tempo_mais_gols']['probabilidade']*100:.1f}%"
            }
        
        if 'handicap_asiatico' in palpites:
            palpite_formatado['mercados']['handicap_asiatico'] = {
                'palpite': palpites['handicap_asiatico']['palpite'],
                'confianca': f"{palpites['handicap_asiatico']['probabilidade']*100:.1f}%"
            }
        
        palpites_formatados.append(palpite_formatado)
    
    return palpites_formatados

# Teste da função
if __name__ == "__main__":
    palpites = coletar_palpites()
    print(json.dumps(palpites, indent=2))
