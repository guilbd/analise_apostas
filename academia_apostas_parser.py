"""
Parser para dados da Academia das Apostas Brasil
------------------------------------------------
Este módulo contém funções para extrair e processar dados do site Academia das Apostas Brasil,
tanto por web scraping quanto por processamento de texto copiado manualmente.
"""

import re
import json
import logging
import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('academia_apostas_parser')

class AcademiaApostasParser:
    """
    Classe para extrair e processar dados do site Academia das Apostas Brasil.
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'https://www.academiadasapostas.com.br/'
        }
        self.base_url = 'https://www.academiadasapostas.com.br'
        
    def obter_jogos_do_dia(self, data: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtém os jogos do dia especificado do site Academia das Apostas Brasil.
        
        Args:
            data: Data no formato DD/MM/YYYY. Se None, usa a data atual.
            
        Returns:
            Lista de dicionários com informações dos jogos.
        """
        if data is None:
            data = datetime.datetime.now().strftime('%d/%m/%Y')
            
        logger.info(f"Obtendo jogos para a data: {data}")
        
        # Converter data para o formato usado na URL
        data_partes = data.split('/')
        data_url = f"{data_partes[2]}-{data_partes[1]}-{data_partes[0]}"
        
        url = f"{self.base_url}/stats/jogos-do-dia/{data_url}/futebol/brasil/campeonato-brasileiro-serie-a"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            jogos = []
            
            # Encontrar a tabela de jogos
            tabelas = soup.find_all('table', class_='stats-table')
            
            for tabela in tabelas:
                # Verificar se é a tabela do Brasileirão
                header = tabela.find_previous('h2')
                if header and 'Brasileirão' in header.text:
                    linhas = tabela.find_all('tr')
                    
                    for linha in linhas[1:]:  # Pular o cabeçalho
                        colunas = linha.find_all('td')
                        
                        if len(colunas) >= 5:
                            hora = colunas[0].text.strip()
                            time_casa = colunas[1].text.strip()
                            time_visitante = colunas[3].text.strip()
                            
                            # Gerar ID único para o jogo
                            id_jogo = f"{time_casa.lower().replace(' ', '_')}_{time_visitante.lower().replace(' ', '_')}_{data.replace('/', '')}"
                            
                            jogo = {
                                'id_jogo': id_jogo,
                                'time_casa': time_casa,
                                'time_visitante': time_visitante,
                                'data': data,
                                'hora': hora,
                                'campeonato': 'Brasileirão Série A'
                            }
                            
                            jogos.append(jogo)
            
            logger.info(f"Encontrados {len(jogos)} jogos para a data {data}")
            return jogos
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter jogos do dia: {str(e)}")
            return []
    
    def obter_estatisticas_jogo(self, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Obtém estatísticas detalhadas para um jogo específico.
        
        Args:
            time_casa: Nome do time da casa
            time_visitante: Nome do time visitante
            
        Returns:
            Dicionário com estatísticas detalhadas do jogo
        """
        logger.info(f"Obtendo estatísticas para: {time_casa} vs {time_visitante}")
        
        # Normalizar nomes dos times para URL
        time_casa_url = time_casa.lower().replace(' ', '-')
        time_visitante_url = time_visitante.lower().replace(' ', '-')
        
        url = f"{self.base_url}/stats/previsao/{time_casa_url}-vs-{time_visitante_url}/futebol/brasil/campeonato-brasileiro-serie-a"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            estatisticas = {
                'time_casa': self._extrair_estatisticas_time(soup, time_casa, 'casa'),
                'time_visitante': self._extrair_estatisticas_time(soup, time_visitante, 'visitante'),
                'confrontos_diretos': self._extrair_confrontos_diretos(soup, time_casa, time_visitante),
                'mercados_adicionais': self._extrair_mercados_adicionais(soup),
                'odds': self._extrair_odds(soup)
            }
            
            return estatisticas
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter estatísticas do jogo: {str(e)}")
            return self._gerar_estatisticas_exemplo(time_casa, time_visitante)
    
    def _extrair_estatisticas_time(self, soup: BeautifulSoup, time: str, tipo: str) -> Dict[str, Any]:
        """
        Extrai estatísticas de um time específico da página.
        
        Args:
            soup: Objeto BeautifulSoup da página
            time: Nome do time
            tipo: 'casa' ou 'visitante'
            
        Returns:
            Dicionário com estatísticas do time
        """
        estatisticas = {}
        
        try:
            # Encontrar tabela de classificação
            tabela_classificacao = soup.find('table', class_='stats-table classificacao')
            
            if tabela_classificacao:
                linhas = tabela_classificacao.find_all('tr')
                
                for linha in linhas[1:]:  # Pular o cabeçalho
                    colunas = linha.find_all('td')
                    
                    if len(colunas) >= 10:
                        nome_time = colunas[1].text.strip()
                        
                        if nome_time.lower() == time.lower():
                            estatisticas['posicao'] = int(colunas[0].text.strip())
                            estatisticas['pontos'] = int(colunas[2].text.strip())
                            estatisticas['jogos'] = int(colunas[3].text.strip())
                            estatisticas['vitorias'] = int(colunas[4].text.strip())
                            estatisticas['empates'] = int(colunas[5].text.strip())
                            estatisticas['derrotas'] = int(colunas[6].text.strip())
                            estatisticas['gols_marcados'] = int(colunas[7].text.strip().split(':')[0])
                            estatisticas['gols_sofridos'] = int(colunas[7].text.strip().split(':')[1])
                            estatisticas['saldo_gols'] = estatisticas['gols_marcados'] - estatisticas['gols_sofridos']
                            break
            
            # Extrair sequência de resultados
            secao_sequencia = soup.find('div', class_='sequencia-resultados')
            
            if secao_sequencia:
                tabelas = secao_sequencia.find_all('table')
                
                for tabela in tabelas:
                    linhas = tabela.find_all('tr')
                    
                    for linha in linhas:
                        colunas = linha.find_all('td')
                        
                        if len(colunas) >= 2:
                            descricao = colunas[0].text.strip()
                            
                            if 'Sequência de Vitórias' in descricao and tipo in descricao.lower():
                                estatisticas['ultimos_jogos'] = ['V'] * int(colunas[1].text.strip() or '0')
                            elif 'Sequência de Empates' in descricao and tipo in descricao.lower():
                                estatisticas['ultimos_jogos'] = ['E'] * int(colunas[1].text.strip() or '0')
                            elif 'Sequência de Derrotas' in descricao and tipo in descricao.lower():
                                estatisticas['ultimos_jogos'] = ['D'] * int(colunas[1].text.strip() or '0')
            
            # Extrair médias de gols
            secao_gols = soup.find('div', id='gols')
            
            if secao_gols:
                tabelas = secao_gols.find_all('table')
                
                for tabela in tabelas:
                    linhas = tabela.find_all('tr')
                    
                    for linha in linhas:
                        colunas = linha.find_all('td')
                        
                        if len(colunas) >= 3:
                            descricao = colunas[0].text.strip()
                            
                            if 'Média de gols marcados' in descricao:
                                if tipo == 'casa' and 'Casa' in colunas[1].text:
                                    estatisticas['media_gols_marcados'] = float(colunas[1].text.strip().replace(',', '.'))
                                elif tipo == 'visitante' and 'Fora' in colunas[2].text:
                                    estatisticas['media_gols_marcados'] = float(colunas[2].text.strip().replace(',', '.'))
                            
                            elif 'Média de gols sofridos' in descricao:
                                if tipo == 'casa' and 'Casa' in colunas[1].text:
                                    estatisticas['media_gols_sofridos'] = float(colunas[1].text.strip().replace(',', '.'))
                                elif tipo == 'visitante' and 'Fora' in colunas[2].text:
                                    estatisticas['media_gols_sofridos'] = float(colunas[2].text.strip().replace(',', '.'))
            
            # Calcular aproveitamento
            if 'jogos' in estatisticas and estatisticas['jogos'] > 0:
                pontos_possiveis = estatisticas['jogos'] * 3
                pontos_obtidos = estatisticas['pontos']
                estatisticas['aproveitamento'] = round((pontos_obtidos / pontos_possiveis) * 100, 1)
            
            # Se não temos ultimos_jogos, criar uma lista vazia
            if 'ultimos_jogos' not in estatisticas:
                estatisticas['ultimos_jogos'] = []
                
            # Garantir que temos pelo menos 5 resultados nos últimos jogos
            while len(estatisticas.get('ultimos_jogos', [])) < 5:
                estatisticas['ultimos_jogos'].append('?')
                
            # Limitar a 5 resultados
            estatisticas['ultimos_jogos'] = estatisticas['ultimos_jogos'][:5]
            
        except Exception as e:
            logger.error(f"Erro ao extrair estatísticas do time {time}: {str(e)}")
        
        return estatisticas
    
    def _extrair_confrontos_diretos(self, soup: BeautifulSoup, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai informações de confrontos diretos entre os times.
        
        Args:
            soup: Objeto BeautifulSoup da página
            time_casa: Nome do time da casa
            time_visitante: Nome do time visitante
            
        Returns:
            Dicionário com informações de confrontos diretos
        """
        confrontos = {
            'confrontos': [],
            'resumo': {
                'total': 0,
                'vitorias_casa': 0,
                'vitorias_visitante': 0,
                'empates': 0
            }
        }
        
        try:
            # Encontrar seção de confrontos diretos
            secao_confrontos = soup.find('div', id='confronto-direto')
            
            if secao_confrontos:
                tabelas = secao_confrontos.find_all('table')
                
                for tabela in tabelas:
                    linhas = tabela.find_all('tr')
                    
                    for linha in linhas[1:]:  # Pular o cabeçalho
                        colunas = linha.find_all('td')
                        
                        if len(colunas) >= 5:
                            data = colunas[0].text.strip()
                            mandante = colunas[1].text.strip()
                            placar = colunas[2].text.strip()
                            visitante = colunas[3].text.strip()
                            competicao = colunas[4].text.strip() if len(colunas) > 4 else "Não especificado"
                            
                            confronto = {
                                'data': data,
                                'mandante': mandante,
                                'visitante': visitante,
                                'placar': placar,
                                'competicao': competicao
                            }
                            
                            confrontos['confrontos'].append(confronto)
                            confrontos['resumo']['total'] += 1
                            
                            # Analisar o resultado
                            try:
                                gols = placar.split('x')
                                gols_mandante = int(gols[0].strip())
                                gols_visitante = int(gols[1].strip())
                                
                                if mandante.lower() == time_casa.lower():
                                    if gols_mandante > gols_visitante:
                                        confrontos['resumo']['vitorias_casa'] += 1
                                    elif gols_mandante < gols_visitante:
                                        confrontos['resumo']['vitorias_visitante'] += 1
                                    else:
                                        confrontos['resumo']['empates'] += 1
                                else:
                                    if gols_mandante > gols_visitante:
                                        confrontos['resumo']['vitorias_visitante'] += 1
                                    elif gols_mandante < gols_visitante:
                                        confrontos['resumo']['vitorias_casa'] += 1
                                    else:
                                        confrontos['resumo']['empates'] += 1
                            except:
                                pass
            
        except Exception as e:
            logger.error(f"Erro ao extrair confrontos diretos: {str(e)}")
        
        return confrontos
    
    def _extrair_mercados_adicionais(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extrai informações de mercados adicionais como escanteios e cartões.
        
        Args:
            soup: Objeto BeautifulSoup da página
            
        Returns:
            Dicionário com informações de mercados adicionais
        """
        mercados = {
            'escanteios': {
                'time_casa': {
                    'media_por_jogo': 0.0,
                    'media_primeiro_tempo': 0.0,
                    'media_segundo_tempo': 0.0
                },
                'time_visitante': {
                    'media_por_jogo': 0.0,
                    'media_primeiro_tempo': 0.0,
                    'media_segundo_tempo': 0.0
                },
                'confrontos_diretos': {
                    'media_por_jogo': 0.0,
                    'ultimo_jogo': 0
                }
            },
            'cartoes': {
                'time_casa': {
                    'cartoes_amarelos_media': 0.0,
                    'cartoes_vermelhos_total': 0
                },
                'time_visitante': {
                    'cartoes_amarelos_media': 0.0,
                    'cartoes_vermelhos_total': 0
                },
                'confrontos_diretos': {
                    'media_cartoes_total': 0.0,
                    'ultimo_jogo_amarelos': 0,
                    'ultimo_jogo_vermelhos': 0
                }
            }
        }
        
        try:
            # Extrair informações de escanteios
            secao_escanteios = soup.find('div', id='escanteios')
            
            if secao_escanteios:
                tabelas = secao_escanteios.find_all('table')
                
                for tabela in tabelas:
                    linhas = tabela.find_all('tr')
                    
                    for linha in linhas:
                        colunas = linha.find_all('td')
                        
                        if len(colunas) >= 3:
                            descricao = colunas[0].text.strip()
                            
                            if 'Média de escanteios' in descricao:
                                # Casa
                                valor_casa = colunas[1].text.strip().replace(',', '.')
                                if valor_casa and valor_casa != '-':
                                    mercados['escanteios']['time_casa']['media_por_jogo'] = float(valor_casa)
                                
                                # Visitante
                                valor_visitante = colunas[2].text.strip().replace(',', '.')
                                if valor_visitante and valor_visitante != '-':
                                    mercados['escanteios']['time_visitante']['media_por_jogo'] = float(valor_visitante)
                            
                            elif 'Média de escanteios no 1º tempo' in descricao:
                                # Casa
                                valor_casa = colunas[1].text.strip().replace(',', '.')
                                if valor_casa and valor_casa != '-':
                                    mercados['escanteios']['time_casa']['media_primeiro_tempo'] = float(valor_casa)
                                
                                # Visitante
                                valor_visitante = colunas[2].text.strip().replace(',', '.')
                                if valor_visitante and valor_visitante != '-':
                                    mercados['escanteios']['time_visitante']['media_primeiro_tempo'] = float(valor_visitante)
                            
                            elif 'Média de escanteios no 2º tempo' in descricao:
                                # Casa
                                valor_casa = colunas[1].text.strip().replace(',', '.')
                                if valor_casa and valor_casa != '-':
                                    mercados['escanteios']['time_casa']['media_segundo_tempo'] = float(valor_casa)
                                
                                # Visitante
                                valor_visitante = colunas[2].text.strip().replace(',', '.')
                                if valor_visitante and valor_visitante != '-':
                                    mercados['escanteios']['time_visitante']['media_segundo_tempo'] = float(valor_visitante)
            
            # Extrair informações de cartões
            secao_cartoes = soup.find('div', id='cartoes')
            
            if secao_cartoes:
                tabelas = secao_cartoes.find_all('table')
                
                for tabela in tabelas:
                    linhas = tabela.find_all('tr')
                    
                    for linha in linhas:
                        colunas = linha.find_all('td')
                        
                        if len(colunas) >= 3:
                            descricao = colunas[0].text.strip()
                            
                            if 'Média de cartões amarelos' in descricao:
                                # Casa
                                valor_casa = colunas[1].text.strip().replace(',', '.')
                                if valor_casa and valor_casa != '-':
                                    mercados['cartoes']['time_casa']['cartoes_amarelos_media'] = float(valor_casa)
                                
                                # Visitante
                                valor_visitante = colunas[2].text.strip().replace(',', '.')
                                if valor_visitante and valor_visitante != '-':
                                    mercados['cartoes']['time_visitante']['cartoes_amarelos_media'] = float(valor_visitante)
                            
                            elif 'Total de cartões vermelhos' in descricao:
                                # Casa
                                valor_casa = colunas[1].text.strip()
                                if valor_casa and valor_casa != '-':
                                    mercados['cartoes']['time_casa']['cartoes_vermelhos_total'] = int(valor_casa)
                                
                                # Visitante
                                valor_visitante = colunas[2].text.strip()
                                if valor_visitante and valor_visitante != '-':
                                    mercados['cartoes']['time_visitante']['cartoes_vermelhos_total'] = int(valor_visitante)
            
            # Calcular médias para confrontos diretos
            if len(mercados['escanteios']['time_casa']) > 0 and len(mercados['escanteios']['time_visitante']) > 0:
                media_casa = mercados['escanteios']['time_casa']['media_por_jogo']
                media_visitante = mercados['escanteios']['time_visitante']['media_por_jogo']
                
                if media_casa > 0 and media_visitante > 0:
                    mercados['escanteios']['confrontos_diretos']['media_por_jogo'] = round((media_casa + media_visitante) / 2, 1)
            
            if len(mercados['cartoes']['time_casa']) > 0 and len(mercados['cartoes']['time_visitante']) > 0:
                media_casa = mercados['cartoes']['time_casa']['cartoes_amarelos_media']
                media_visitante = mercados['cartoes']['time_visitante']['cartoes_amarelos_media']
                
                if media_casa > 0 and media_visitante > 0:
                    mercados['cartoes']['confrontos_diretos']['media_cartoes_total'] = round((media_casa + media_visitante) / 2, 1)
            
        except Exception as e:
            logger.error(f"Erro ao extrair mercados adicionais: {str(e)}")
        
        return mercados
    
    def _extrair_odds(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extrai odds da partida.
        
        Args:
            soup: Objeto BeautifulSoup da página
            
        Returns:
            Dicionário com odds da partida
        """
        odds = {
            'resultado': {
                'casa': 0.0,
                'empate': 0.0,
                'visitante': 0.0
            },
            'over_under': {
                'over_2.5': 0.0,
                'under_2.5': 0.0
            },
            'ambos_marcam': {
                'sim': 0.0,
                'nao': 0.0
            }
        }
        
        try:
            # Extrair odds de resultado
            secao_odds = soup.find('div', id='odds')
            
            if secao_odds:
                tabelas = secao_odds.find_all('table')
                
                for tabela in tabelas:
                    linhas = tabela.find_all('tr')
                    
                    for linha in linhas[1:]:  # Pular o cabeçalho
                        colunas = linha.find_all('td')
                        
                        if len(colunas) >= 4:
                            casa_bookmaker = colunas[0].text.strip()
                            
                            if casa_bookmaker.lower() in ['bet365', 'betfair']:
                                odds['resultado']['casa'] = float(colunas[1].text.strip().replace(',', '.'))
                                odds['resultado']['empate'] = float(colunas[2].text.strip().replace(',', '.'))
                                odds['resultado']['visitante'] = float(colunas[3].text.strip().replace(',', '.'))
                                break
            
            # Extrair odds de over/under
            secao_over_under = soup.find('div', id='over-under')
            
            if secao_over_under:
                tabelas = secao_over_under.find_all('table')
                
                for tabela in tabelas:
                    linhas = tabela.find_all('tr')
                    
                    for linha in linhas:
                        colunas = linha.find_all('td')
                        
                        if len(colunas) >= 3:
                            descricao = colunas[0].text.strip()
                            
                            if 'Mais/Menos de 2.5 gols' in descricao:
                                over = colunas[1].text.strip().replace(',', '.')
                                under = colunas[2].text.strip().replace(',', '.')
                                
                                if over and over != '-':
                                    odds['over_under']['over_2.5'] = float(over)
                                
                                if under and under != '-':
                                    odds['over_under']['under_2.5'] = float(under)
            
            # Extrair odds de ambos marcam
            secao_ambos_marcam = soup.find('div', id='ambas-marcam')
            
            if secao_ambos_marcam:
                tabelas = secao_ambos_marcam.find_all('table')
                
                for tabela in tabelas:
                    linhas = tabela.find_all('tr')
                    
                    for linha in linhas:
                        colunas = linha.find_all('td')
                        
                        if len(colunas) >= 3:
                            descricao = colunas[0].text.strip()
                            
                            if 'Ambas as equipas marcam' in descricao:
                                sim = colunas[1].text.strip().replace(',', '.')
                                nao = colunas[2].text.strip().replace(',', '.')
                                
                                if sim and sim != '-':
                                    odds['ambos_marcam']['sim'] = float(sim)
                                
                                if nao and nao != '-':
                                    odds['ambos_marcam']['nao'] = float(nao)
            
        except Exception as e:
            logger.error(f"Erro ao extrair odds: {str(e)}")
        
        # Garantir que temos valores válidos
        if odds['resultado']['casa'] == 0:
            odds['resultado']['casa'] = 2.0
        if odds['resultado']['empate'] == 0:
            odds['resultado']['empate'] = 3.2
        if odds['resultado']['visitante'] == 0:
            odds['resultado']['visitante'] = 3.5
            
        if odds['over_under']['over_2.5'] == 0:
            odds['over_under']['over_2.5'] = 2.0
        if odds['over_under']['under_2.5'] == 0:
            odds['over_under']['under_2.5'] = 1.8
            
        if odds['ambos_marcam']['sim'] == 0:
            odds['ambos_marcam']['sim'] = 1.9
        if odds['ambos_marcam']['nao'] == 0:
            odds['ambos_marcam']['nao'] = 1.9
        
        return odds
    
    def _gerar_estatisticas_exemplo(self, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Gera estatísticas de exemplo quando não é possível obter dados reais.
        
        Args:
            time_casa: Nome do time da casa
            time_visitante: Nome do time visitante
            
        Returns:
            Dicionário com estatísticas de exemplo
        """
        import random
        
        estatisticas = {
            'time_casa': {
                'posicao': random.randint(1, 20),
                'pontos': random.randint(20, 50),
                'jogos': random.randint(15, 25),
                'vitorias': random.randint(5, 15),
                'empates': random.randint(3, 10),
                'derrotas': random.randint(3, 10),
                'gols_marcados': random.randint(15, 40),
                'gols_sofridos': random.randint(10, 35),
                'saldo_gols': random.randint(-10, 20),
                'aproveitamento': round(random.uniform(40, 70), 1),
                'ultimos_jogos': random.choices(['V', 'E', 'D'], k=5),
                'media_gols_marcados': round(random.uniform(1.0, 2.5), 2),
                'media_gols_sofridos': round(random.uniform(0.8, 2.0), 2)
            },
            'time_visitante': {
                'posicao': random.randint(1, 20),
                'pontos': random.randint(20, 50),
                'jogos': random.randint(15, 25),
                'vitorias': random.randint(5, 15),
                'empates': random.randint(3, 10),
                'derrotas': random.randint(3, 10),
                'gols_marcados': random.randint(15, 40),
                'gols_sofridos': random.randint(10, 35),
                'saldo_gols': random.randint(-10, 20),
                'aproveitamento': round(random.uniform(40, 70), 1),
                'ultimos_jogos': random.choices(['V', 'E', 'D'], k=5),
                'media_gols_marcados': round(random.uniform(1.0, 2.5), 2),
                'media_gols_sofridos': round(random.uniform(0.8, 2.0), 2)
            },
            'confrontos_diretos': {
                'confrontos': [
                    {
                        'data': (datetime.datetime.now() - datetime.timedelta(days=90)).strftime('%d/%m/%Y'),
                        'mandante': time_casa,
                        'visitante': time_visitante,
                        'placar': f"{random.randint(0, 3)}x{random.randint(0, 3)}",
                        'competicao': 'Brasileirão Série A'
                    },
                    {
                        'data': (datetime.datetime.now() - datetime.timedelta(days=180)).strftime('%d/%m/%Y'),
                        'mandante': time_visitante,
                        'visitante': time_casa,
                        'placar': f"{random.randint(0, 3)}x{random.randint(0, 3)}",
                        'competicao': 'Brasileirão Série A'
                    },
                    {
                        'data': (datetime.datetime.now() - datetime.timedelta(days=270)).strftime('%d/%m/%Y'),
                        'mandante': time_casa,
                        'visitante': time_visitante,
                        'placar': f"{random.randint(0, 3)}x{random.randint(0, 3)}",
                        'competicao': 'Copa do Brasil'
                    }
                ],
                'resumo': {
                    'total': 3,
                    'vitorias_casa': random.randint(0, 2),
                    'vitorias_visitante': random.randint(0, 2),
                    'empates': random.randint(0, 2)
                }
            },
            'mercados_adicionais': {
                'escanteios': {
                    'time_casa': {
                        'media_por_jogo': round(random.uniform(4.0, 7.0), 1),
                        'media_primeiro_tempo': round(random.uniform(2.0, 3.5), 1),
                        'media_segundo_tempo': round(random.uniform(2.0, 3.5), 1)
                    },
                    'time_visitante': {
                        'media_por_jogo': round(random.uniform(4.0, 7.0), 1),
                        'media_primeiro_tempo': round(random.uniform(2.0, 3.5), 1),
                        'media_segundo_tempo': round(random.uniform(2.0, 3.5), 1)
                    },
                    'confrontos_diretos': {
                        'media_por_jogo': round(random.uniform(8.0, 12.0), 1),
                        'ultimo_jogo': random.randint(5, 15)
                    }
                },
                'cartoes': {
                    'time_casa': {
                        'cartoes_amarelos_media': round(random.uniform(1.5, 3.5), 1),
                        'cartoes_vermelhos_total': random.randint(0, 3)
                    },
                    'time_visitante': {
                        'cartoes_amarelos_media': round(random.uniform(1.5, 3.5), 1),
                        'cartoes_vermelhos_total': random.randint(0, 3)
                    },
                    'confrontos_diretos': {
                        'media_cartoes_total': round(random.uniform(3.0, 6.0), 1),
                        'ultimo_jogo_amarelos': random.randint(2, 8),
                        'ultimo_jogo_vermelhos': random.randint(0, 2)
                    }
                }
            },
            'odds': {
                'resultado': {
                    'casa': round(random.uniform(1.5, 3.5), 2),
                    'empate': round(random.uniform(2.8, 4.0), 2),
                    'visitante': round(random.uniform(1.8, 4.5), 2)
                },
                'over_under': {
                    'over_2.5': round(random.uniform(1.7, 2.2), 2),
                    'under_2.5': round(random.uniform(1.7, 2.2), 2)
                },
                'ambos_marcam': {
                    'sim': round(random.uniform(1.7, 2.2), 2),
                    'nao': round(random.uniform(1.7, 2.2), 2)
                }
            }
        }
        
        # Ajustar o resumo dos confrontos diretos para que a soma seja igual ao total
        resumo = estatisticas['confrontos_diretos']['resumo']
        while resumo['vitorias_casa'] + resumo['vitorias_visitante'] + resumo['empates'] != resumo['total']:
            if resumo['vitorias_casa'] + resumo['vitorias_visitante'] + resumo['empates'] > resumo['total']:
                if resumo['vitorias_casa'] > 0:
                    resumo['vitorias_casa'] -= 1
                elif resumo['vitorias_visitante'] > 0:
                    resumo['vitorias_visitante'] -= 1
                elif resumo['empates'] > 0:
                    resumo['empates'] -= 1
            else:
                resumo['empates'] += 1
        
        return estatisticas
    
    def processar_texto_copiado(self, texto: str) -> Dict[str, Any]:
        """
        Processa texto copiado manualmente do site Academia das Apostas Brasil.
        
        Args:
            texto: Texto copiado do site
            
        Returns:
            Dicionário com dados extraídos do texto
        """
        logger.info("Processando texto copiado manualmente")
        
        resultado = {
            'jogos': [],
            'estatisticas': {}
        }
        
        try:
            # Identificar o tipo de conteúdo
            if 'Quem será o vencedor?' in texto:
                # Página de jogo específico
                times = self._extrair_times_do_texto(texto)
                
                if times:
                    time_casa, time_visitante = times
                    
                    # Extrair data e hora
                    data_hora = self._extrair_data_hora_do_texto(texto)
                    
                    if data_hora:
                        data, hora = data_hora
                        
                        # Gerar ID único para o jogo
                        id_jogo = f"{time_casa.lower().replace(' ', '_')}_{time_visitante.lower().replace(' ', '_')}_{data.replace('/', '')}"
                        
                        jogo = {
                            'id_jogo': id_jogo,
                            'time_casa': time_casa,
                            'time_visitante': time_visitante,
                            'data': data,
                            'hora': hora,
                            'campeonato': 'Brasileirão Série A'
                        }
                        
                        resultado['jogos'].append(jogo)
                        
                        # Extrair odds
                        odds = self._extrair_odds_do_texto(texto)
                        
                        # Extrair estatísticas
                        estatisticas = self._extrair_estatisticas_do_texto(texto, time_casa, time_visitante)
                        
                        if odds:
                            estatisticas['odds'] = odds
                            
                        resultado['estatisticas'][id_jogo] = estatisticas
                
            elif 'FUTEBOL HOJE' in texto:
                # Lista de jogos
                jogos = self._extrair_jogos_do_texto(texto)
                resultado['jogos'] = jogos
                
            elif 'CLASSIFICAÇÕES NESTA COMPETIÇÃO' in texto:
                # Página de classificação
                times = self._extrair_times_do_texto(texto)
                
                if times and len(times) >= 2:
                    time_casa, time_visitante = times[:2]
                    
                    # Extrair estatísticas
                    estatisticas = self._extrair_estatisticas_do_texto(texto, time_casa, time_visitante)
                    
                    # Gerar ID único para o jogo (sem data específica)
                    id_jogo = f"{time_casa.lower().replace(' ', '_')}_{time_visitante.lower().replace(' ', '_')}_generico"
                    
                    resultado['estatisticas'][id_jogo] = estatisticas
            
        except Exception as e:
            logger.error(f"Erro ao processar texto copiado: {str(e)}")
        
        return resultado
    
    def _extrair_times_do_texto(self, texto: str) -> Optional[Tuple[str, str]]:
        """
        Extrai nomes dos times do texto copiado.
        
        Args:
            texto: Texto copiado
            
        Returns:
            Tupla com nome do time da casa e time visitante, ou None se não encontrados
        """
        try:
            # Padrão 1: Formato "TIME vs TIME"
            padrao_vs = re.compile(r'([A-Za-zÀ-ÖØ-öø-ÿ\s-]+)\s+vs\s+([A-Za-zÀ-ÖØ-öø-ÿ\s-]+)')
            match_vs = padrao_vs.search(texto)
            
            if match_vs:
                time_casa = match_vs.group(1).strip()
                time_visitante = match_vs.group(2).strip()
                return time_casa, time_visitante
            
            # Padrão 2: Formato "CASA EMPATE FORA" com times em linhas separadas
            padrao_casa_fora = re.compile(r'Casa\s+Empate\s+Fora', re.IGNORECASE)
            match_casa_fora = padrao_casa_fora.search(texto)
            
            if match_casa_fora:
                linhas = texto.split('\n')
                
                for i, linha in enumerate(linhas):
                    if 'Casa' in linha and 'Empate' in linha and 'Fora' in linha:
                        # Procurar times antes e depois desta linha
                        for j in range(i-5, i):
                            if j >= 0 and linhas[j].strip() and not any(palavra in linhas[j].lower() for palavra in ['casa', 'empate', 'fora', 'odds']):
                                time_casa = linhas[j].strip()
                                
                                for k in range(i+1, i+6):
                                    if k < len(linhas) and linhas[k].strip() and not any(palavra in linhas[k].lower() for palavra in ['casa', 'empate', 'fora', 'odds']):
                                        time_visitante = linhas[k].strip()
                                        return time_casa, time_visitante
            
            # Padrão 3: Formato de cabeçalho com times em destaque
            linhas = texto.split('\n')
            for i, linha in enumerate(linhas):
                if 'CORINTHIANS' in linha.upper() or 'FLAMENGO' in linha.upper() or 'PALMEIRAS' in linha.upper():
                    time_casa = linha.strip()
                    
                    # Procurar o time visitante nas próximas linhas
                    for j in range(i+1, i+10):
                        if j < len(linhas) and linhas[j].strip() and linhas[j].strip().upper() != time_casa.upper():
                            # Verificar se é um nome de time válido (não é uma data, hora, etc.)
                            if re.match(r'^[A-Za-zÀ-ÖØ-öø-ÿ\s-]+$', linhas[j].strip()):
                                time_visitante = linhas[j].strip()
                                return time_casa, time_visitante
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao extrair times do texto: {str(e)}")
            return None
    
    def _extrair_data_hora_do_texto(self, texto: str) -> Optional[Tuple[str, str]]:
        """
        Extrai data e hora do texto copiado.
        
        Args:
            texto: Texto copiado
            
        Returns:
            Tupla com data (DD/MM/YYYY) e hora (HH:MM), ou None se não encontrados
        """
        try:
            # Padrão 1: Data e hora no formato "DD abr - HH:MM"
            padrao_data_hora = re.compile(r'(\d{1,2})\s+([a-z]{3})\s+-\s+(\d{1,2}):(\d{2})', re.IGNORECASE)
            match_data_hora = padrao_data_hora.search(texto)
            
            if match_data_hora:
                dia = match_data_hora.group(1).zfill(2)
                mes_abrev = match_data_hora.group(2).lower()
                hora = match_data_hora.group(3).zfill(2)
                minuto = match_data_hora.group(4)
                
                # Converter abreviação do mês para número
                meses = {
                    'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                    'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                    'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
                }
                
                if mes_abrev in meses:
                    mes = meses[mes_abrev]
                    ano = datetime.datetime.now().year
                    
                    data = f"{dia}/{mes}/{ano}"
                    hora_completa = f"{hora}:{minuto}"
                    
                    return data, hora_completa
            
            # Padrão 2: Data completa no formato "DD/MM/YYYY"
            padrao_data_completa = re.compile(r'(\d{2}/\d{2}/\d{4})')
            match_data_completa = padrao_data_completa.search(texto)
            
            if match_data_completa:
                data = match_data_completa.group(1)
                
                # Procurar hora próxima à data
                padrao_hora = re.compile(r'(\d{1,2}):(\d{2})')
                match_hora = padrao_hora.search(texto)
                
                if match_hora:
                    hora = match_hora.group(1).zfill(2)
                    minuto = match_hora.group(2)
                    hora_completa = f"{hora}:{minuto}"
                    
                    return data, hora_completa
            
            # Padrão 3: Data e hora no cabeçalho
            padrao_cabecalho = re.compile(r'(\d{1,2})\s+([a-z]+)\s+(\d{4})\s+-\s+(\d{1,2}):(\d{2})', re.IGNORECASE)
            match_cabecalho = padrao_cabecalho.search(texto)
            
            if match_cabecalho:
                dia = match_cabecalho.group(1).zfill(2)
                mes_nome = match_cabecalho.group(2).lower()
                ano = match_cabecalho.group(3)
                hora = match_cabecalho.group(4).zfill(2)
                minuto = match_cabecalho.group(5)
                
                # Converter nome do mês para número
                meses_nomes = {
                    'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
                    'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
                    'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
                }
                
                for nome, num in meses_nomes.items():
                    if mes_nome in nome:
                        mes = num
                        data = f"{dia}/{mes}/{ano}"
                        hora_completa = f"{hora}:{minuto}"
                        
                        return data, hora_completa
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao extrair data e hora do texto: {str(e)}")
            return None
    
    def _extrair_odds_do_texto(self, texto: str) -> Optional[Dict[str, Any]]:
        """
        Extrai odds do texto copiado.
        
        Args:
            texto: Texto copiado
            
        Returns:
            Dicionário com odds, ou None se não encontrados
        """
        odds = {
            'resultado': {
                'casa': 0.0,
                'empate': 0.0,
                'visitante': 0.0
            },
            'over_under': {
                'over_2.5': 0.0,
                'under_2.5': 0.0
            },
            'ambos_marcam': {
                'sim': 0.0,
                'nao': 0.0
            }
        }
        
        try:
            # Extrair odds de resultado (1X2)
            padrao_odds = re.compile(r'Casa\s+Empate\s+Fora\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)', re.IGNORECASE)
            match_odds = padrao_odds.search(texto)
            
            if match_odds:
                odds['resultado']['casa'] = float(match_odds.group(1))
                odds['resultado']['empate'] = float(match_odds.group(2))
                odds['resultado']['visitante'] = float(match_odds.group(3))
            else:
                # Tentar outro padrão
                linhas = texto.split('\n')
                for i, linha in enumerate(linhas):
                    if 'Casa' in linha and 'Empate' in linha and 'Fora' in linha:
                        # Procurar odds nas próximas linhas
                        for j in range(i+1, i+10):
                            if j < len(linhas):
                                # Procurar padrão de 3 números separados
                                numeros = re.findall(r'\d+\.\d+', linhas[j])
                                if len(numeros) >= 3:
                                    odds['resultado']['casa'] = float(numeros[0])
                                    odds['resultado']['empate'] = float(numeros[1])
                                    odds['resultado']['visitante'] = float(numeros[2])
                                    break
            
            # Extrair odds de over/under
            padrao_over_under = re.compile(r'Mais/Menos de 2.5 gols\s+(\d+\.\d+)\s+(\d+\.\d+)', re.IGNORECASE)
            match_over_under = padrao_over_under.search(texto)
            
            if match_over_under:
                odds['over_under']['over_2.5'] = float(match_over_under.group(1))
                odds['over_under']['under_2.5'] = float(match_over_under.group(2))
            else:
                # Procurar por "+/- 2.5"
                padrao_alt = re.compile(r'\+/- 2.5\s+(\d+\.\d+)\s+(\d+\.\d+)', re.IGNORECASE)
                match_alt = padrao_alt.search(texto)
                
                if match_alt:
                    odds['over_under']['over_2.5'] = float(match_alt.group(1))
                    odds['over_under']['under_2.5'] = float(match_alt.group(2))
            
            # Extrair odds de ambos marcam
            padrao_ambos = re.compile(r'Ambas as equipas marcam\s+(\d+\.\d+)\s+(\d+\.\d+)', re.IGNORECASE)
            match_ambos = padrao_ambos.search(texto)
            
            if match_ambos:
                odds['ambos_marcam']['sim'] = float(match_ambos.group(1))
                odds['ambos_marcam']['nao'] = float(match_ambos.group(2))
            
            # Verificar se encontramos pelo menos as odds de resultado
            if odds['resultado']['casa'] > 0:
                return odds
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao extrair odds do texto: {str(e)}")
            return None
    
    def _extrair_estatisticas_do_texto(self, texto: str, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai estatísticas do texto copiado.
        
        Args:
            texto: Texto copiado
            time_casa: Nome do time da casa
            time_visitante: Nome do time visitante
            
        Returns:
            Dicionário com estatísticas
        """
        estatisticas = {
            'time_casa': {},
            'time_visitante': {},
            'confrontos_diretos': {
                'confrontos': [],
                'resumo': {
                    'total': 0,
                    'vitorias_casa': 0,
                    'vitorias_visitante': 0,
                    'empates': 0
                }
            },
            'mercados_adicionais': {
                'escanteios': {
                    'time_casa': {},
                    'time_visitante': {},
                    'confrontos_diretos': {}
                },
                'cartoes': {
                    'time_casa': {},
                    'time_visitante': {},
                    'confrontos_diretos': {}
                }
            }
        }
        
        try:
            # Extrair classificação
            padrao_classificacao = re.compile(r'(\d+)\s+' + re.escape(time_casa) + r'\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+:\d+)', re.IGNORECASE)
            match_casa = padrao_classificacao.search(texto)
            
            if match_casa:
                estatisticas['time_casa']['posicao'] = int(match_casa.group(1))
                estatisticas['time_casa']['pontos'] = int(match_casa.group(2))
                estatisticas['time_casa']['jogos'] = int(match_casa.group(3))
                estatisticas['time_casa']['vitorias'] = int(match_casa.group(4))
                estatisticas['time_casa']['empates'] = int(match_casa.group(5))
                estatisticas['time_casa']['derrotas'] = int(match_casa.group(6))
                
                gols = match_casa.group(7).split(':')
                estatisticas['time_casa']['gols_marcados'] = int(gols[0])
                estatisticas['time_casa']['gols_sofridos'] = int(gols[1])
                estatisticas['time_casa']['saldo_gols'] = estatisticas['time_casa']['gols_marcados'] - estatisticas['time_casa']['gols_sofridos']
                
                # Calcular aproveitamento
                if estatisticas['time_casa']['jogos'] > 0:
                    pontos_possiveis = estatisticas['time_casa']['jogos'] * 3
                    pontos_obtidos = estatisticas['time_casa']['pontos']
                    estatisticas['time_casa']['aproveitamento'] = round((pontos_obtidos / pontos_possiveis) * 100, 1)
            
            padrao_classificacao = re.compile(r'(\d+)\s+' + re.escape(time_visitante) + r'\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+:\d+)', re.IGNORECASE)
            match_visitante = padrao_classificacao.search(texto)
            
            if match_visitante:
                estatisticas['time_visitante']['posicao'] = int(match_visitante.group(1))
                estatisticas['time_visitante']['pontos'] = int(match_visitante.group(2))
                estatisticas['time_visitante']['jogos'] = int(match_visitante.group(3))
                estatisticas['time_visitante']['vitorias'] = int(match_visitante.group(4))
                estatisticas['time_visitante']['empates'] = int(match_visitante.group(5))
                estatisticas['time_visitante']['derrotas'] = int(match_visitante.group(6))
                
                gols = match_visitante.group(7).split(':')
                estatisticas['time_visitante']['gols_marcados'] = int(gols[0])
                estatisticas['time_visitante']['gols_sofridos'] = int(gols[1])
                estatisticas['time_visitante']['saldo_gols'] = estatisticas['time_visitante']['gols_marcados'] - estatisticas['time_visitante']['gols_sofridos']
                
                # Calcular aproveitamento
                if estatisticas['time_visitante']['jogos'] > 0:
                    pontos_possiveis = estatisticas['time_visitante']['jogos'] * 3
                    pontos_obtidos = estatisticas['time_visitante']['pontos']
                    estatisticas['time_visitante']['aproveitamento'] = round((pontos_obtidos / pontos_possiveis) * 100, 1)
            
            # Extrair sequência de resultados
            padrao_sequencia = re.compile(r'Sequência de (Vitórias|Empates|Derrotas)[^0-9]*(\d+)', re.IGNORECASE)
            matches_sequencia = padrao_sequencia.finditer(texto)
            
            for match in matches_sequencia:
                tipo = match.group(1).lower()
                quantidade = int(match.group(2))
                
                if 'vitórias' in tipo:
                    estatisticas['time_casa']['ultimos_jogos'] = ['V'] * quantidade
                elif 'empates' in tipo:
                    estatisticas['time_casa']['ultimos_jogos'] = ['E'] * quantidade
                elif 'derrotas' in tipo:
                    estatisticas['time_casa']['ultimos_jogos'] = ['D'] * quantidade
            
            # Extrair médias de gols
            padrao_media_gols = re.compile(r'Média de gols marcados[^0-9]*(\d+\.\d+)[^0-9]*(\d+\.\d+)', re.IGNORECASE)
            match_media_gols = padrao_media_gols.search(texto)
            
            if match_media_gols:
                estatisticas['time_casa']['media_gols_marcados'] = float(match_media_gols.group(1))
                estatisticas['time_visitante']['media_gols_marcados'] = float(match_media_gols.group(2))
            
            padrao_media_sofridos = re.compile(r'Média de gols sofridos[^0-9]*(\d+\.\d+)[^0-9]*(\d+\.\d+)', re.IGNORECASE)
            match_media_sofridos = padrao_media_sofridos.search(texto)
            
            if match_media_sofridos:
                estatisticas['time_casa']['media_gols_sofridos'] = float(match_media_sofridos.group(1))
                estatisticas['time_visitante']['media_gols_sofridos'] = float(match_media_sofridos.group(2))
            
            # Extrair confrontos diretos
            padrao_confronto = re.compile(r'(\d{2}/\d{2}/\d{4})\s+(\w+)\s+(\d+)-(\d+)\s+(\w+)', re.IGNORECASE)
            matches_confronto = padrao_confronto.finditer(texto)
            
            for match in matches_confronto:
                data = match.group(1)
                mandante = match.group(2)
                gols_mandante = int(match.group(3))
                gols_visitante = int(match.group(4))
                visitante = match.group(5)
                
                confronto = {
                    'data': data,
                    'mandante': mandante,
                    'visitante': visitante,
                    'placar': f"{gols_mandante}x{gols_visitante}",
                    'competicao': 'Não especificado'
                }
                
                estatisticas['confrontos_diretos']['confrontos'].append(confronto)
                estatisticas['confrontos_diretos']['resumo']['total'] += 1
                
                # Analisar o resultado
                if mandante.lower() == time_casa.lower():
                    if gols_mandante > gols_visitante:
                        estatisticas['confrontos_diretos']['resumo']['vitorias_casa'] += 1
                    elif gols_mandante < gols_visitante:
                        estatisticas['confrontos_diretos']['resumo']['vitorias_visitante'] += 1
                    else:
                        estatisticas['confrontos_diretos']['resumo']['empates'] += 1
                else:
                    if gols_mandante > gols_visitante:
                        estatisticas['confrontos_diretos']['resumo']['vitorias_visitante'] += 1
                    elif gols_mandante < gols_visitante:
                        estatisticas['confrontos_diretos']['resumo']['vitorias_casa'] += 1
                    else:
                        estatisticas['confrontos_diretos']['resumo']['empates'] += 1
            
            # Extrair mercados adicionais (escanteios)
            padrao_escanteios = re.compile(r'Média de escanteios[^0-9]*(\d+\.\d+)[^0-9]*(\d+\.\d+)', re.IGNORECASE)
            match_escanteios = padrao_escanteios.search(texto)
            
            if match_escanteios:
                estatisticas['mercados_adicionais']['escanteios']['time_casa']['media_por_jogo'] = float(match_escanteios.group(1))
                estatisticas['mercados_adicionais']['escanteios']['time_visitante']['media_por_jogo'] = float(match_escanteios.group(2))
                
                # Calcular média para confrontos diretos
                media_casa = estatisticas['mercados_adicionais']['escanteios']['time_casa']['media_por_jogo']
                media_visitante = estatisticas['mercados_adicionais']['escanteios']['time_visitante']['media_por_jogo']
                
                if media_casa > 0 and media_visitante > 0:
                    estatisticas['mercados_adicionais']['escanteios']['confrontos_diretos']['media_por_jogo'] = round((media_casa + media_visitante) / 2, 1)
            
            # Extrair mercados adicionais (cartões)
            padrao_cartoes = re.compile(r'Média de cartões amarelos[^0-9]*(\d+\.\d+)[^0-9]*(\d+\.\d+)', re.IGNORECASE)
            match_cartoes = padrao_cartoes.search(texto)
            
            if match_cartoes:
                estatisticas['mercados_adicionais']['cartoes']['time_casa']['cartoes_amarelos_media'] = float(match_cartoes.group(1))
                estatisticas['mercados_adicionais']['cartoes']['time_visitante']['cartoes_amarelos_media'] = float(match_cartoes.group(2))
                
                # Calcular média para confrontos diretos
                media_casa = estatisticas['mercados_adicionais']['cartoes']['time_casa']['cartoes_amarelos_media']
                media_visitante = estatisticas['mercados_adicionais']['cartoes']['time_visitante']['cartoes_amarelos_media']
                
                if media_casa > 0 and media_visitante > 0:
                    estatisticas['mercados_adicionais']['cartoes']['confrontos_diretos']['media_cartoes_total'] = round((media_casa + media_visitante) / 2, 1)
            
            # Garantir que temos ultimos_jogos para ambos os times
            if 'ultimos_jogos' not in estatisticas['time_casa']:
                estatisticas['time_casa']['ultimos_jogos'] = ['?'] * 5
                
            if 'ultimos_jogos' not in estatisticas['time_visitante']:
                estatisticas['time_visitante']['ultimos_jogos'] = ['?'] * 5
            
        except Exception as e:
            logger.error(f"Erro ao extrair estatísticas do texto: {str(e)}")
        
        return estatisticas
    
    def _extrair_jogos_do_texto(self, texto: str) -> List[Dict[str, Any]]:
        """
        Extrai lista de jogos do texto copiado.
        
        Args:
            texto: Texto copiado
            
        Returns:
            Lista de dicionários com informações dos jogos
        """
        jogos = []
        
        try:
            # Dividir o texto em linhas
            linhas = texto.split('\n')
            
            # Procurar padrões de jogos
            for i, linha in enumerate(linhas):
                if 'vs' in linha:
                    partes = linha.split('vs')
                    
                    if len(partes) == 2:
                        time_casa = partes[0].strip()
                        time_visitante = partes[1].strip()
                        
                        # Procurar data e hora nas linhas próximas
                        data = None
                        hora = None
                        
                        for j in range(max(0, i-5), min(len(linhas), i+5)):
                            # Procurar padrão de data (DD/MM/YYYY)
                            match_data = re.search(r'(\d{2}/\d{2}/\d{4})', linhas[j])
                            if match_data and not data:
                                data = match_data.group(1)
                            
                            # Procurar padrão de hora (HH:MM)
                            match_hora = re.search(r'(\d{2}:\d{2})', linhas[j])
                            if match_hora and not hora:
                                hora = match_hora.group(1)
                        
                        # Se não encontrou data, usar data atual
                        if not data:
                            data = datetime.datetime.now().strftime('%d/%m/%Y')
                        
                        # Se não encontrou hora, usar hora padrão
                        if not hora:
                            hora = '00:00'
                        
                        # Gerar ID único para o jogo
                        id_jogo = f"{time_casa.lower().replace(' ', '_')}_{time_visitante.lower().replace(' ', '_')}_{data.replace('/', '')}"
                        
                        jogo = {
                            'id_jogo': id_jogo,
                            'time_casa': time_casa,
                            'time_visitante': time_visitante,
                            'data': data,
                            'hora': hora,
                            'campeonato': 'Brasileirão Série A'
                        }
                        
                        jogos.append(jogo)
            
            # Se não encontrou jogos com o padrão "vs", tentar outro padrão
            if not jogos:
                for i, linha in enumerate(linhas):
                    # Procurar padrão de hora (HH:MM) seguido de times
                    match_hora = re.search(r'(\d{2}:\d{2})', linha)
                    
                    if match_hora:
                        hora = match_hora.group(1)
                        
                        # Procurar times nas colunas
                        if i+1 < len(linhas) and i+2 < len(linhas):
                            time_casa = None
                            time_visitante = None
                            
                            # Verificar se as próximas linhas contêm nomes de times
                            for j in range(i+1, min(i+5, len(linhas))):
                                if linhas[j].strip() and not re.search(r'(\d{2}:\d{2})', linhas[j]):
                                    if not time_casa:
                                        time_casa = linhas[j].strip()
                                    elif not time_visitante:
                                        time_visitante = linhas[j].strip()
                                        break
                            
                            if time_casa and time_visitante:
                                # Procurar data nas linhas próximas
                                data = None
                                
                                for j in range(max(0, i-5), min(len(linhas), i+5)):
                                    # Procurar padrão de data (DD/MM/YYYY)
                                    match_data = re.search(r'(\d{2}/\d{2}/\d{4})', linhas[j])
                                    if match_data:
                                        data = match_data.group(1)
                                        break
                                
                                # Se não encontrou data, usar data atual
                                if not data:
                                    data = datetime.datetime.now().strftime('%d/%m/%Y')
                                
                                # Gerar ID único para o jogo
                                id_jogo = f"{time_casa.lower().replace(' ', '_')}_{time_visitante.lower().replace(' ', '_')}_{data.replace('/', '')}"
                                
                                jogo = {
                                    'id_jogo': id_jogo,
                                    'time_casa': time_casa,
                                    'time_visitante': time_visitante,
                                    'data': data,
                                    'hora': hora,
                                    'campeonato': 'Brasileirão Série A'
                                }
                                
                                jogos.append(jogo)
            
        except Exception as e:
            logger.error(f"Erro ao extrair jogos do texto: {str(e)}")
        
        return jogos

# Função para uso direto
def processar_texto_copiado(texto):
    """
    Função auxiliar para processar texto copiado do site Academia das Apostas Brasil.
    
    Args:
        texto: Texto copiado do site
        
    Returns:
        Dicionário com dados extraídos do texto
    """
    parser = AcademiaApostasParser()
    return parser.processar_texto_copiado(texto)

# Exemplo de uso
if __name__ == "__main__":
    parser = AcademiaApostasParser()
    
    # Exemplo de coleta de jogos do dia
    jogos = parser.obter_jogos_do_dia()
    print(f"Jogos encontrados: {len(jogos)}")
    
    if jogos:
        # Exemplo de coleta de estatísticas para o primeiro jogo
        jogo = jogos[0]
        print(f"Coletando estatísticas para: {jogo['time_casa']} vs {jogo['time_visitante']}")
        
        estatisticas = parser.obter_estatisticas_jogo(jogo['time_casa'], jogo['time_visitante'])
        
        # Salvar em arquivos JSON
        with open('jogos_disponiveis.json', 'w', encoding='utf-8') as f:
            json.dump({"jogos": jogos}, f, ensure_ascii=False, indent=4)
        
        with open(f"estatisticas_{jogo['id_jogo']}.json", 'w', encoding='utf-8') as f:
            json.dump(estatisticas, f, ensure_ascii=False, indent=4)
        
        print("Arquivos salvos com sucesso!")
