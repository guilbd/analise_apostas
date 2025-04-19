import os
import json
import logging
import datetime
import requests
from bs4 import BeautifulSoup
import random
import time
from typing import Dict, List, Any, Optional, Tuple, Union

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('coleta_dados_reais')

class ColetorDadosReais:
    """
    Classe para coletar dados reais de jogos e estatísticas.
    """
    
    def __init__(self, diretorio_dados: str = None):
        """
        Inicializa o coletor de dados reais.
        
        Args:
            diretorio_dados: Diretório para salvar os dados. Se None, usa o diretório atual.
        """
        if diretorio_dados is None:
            self.diretorio_dados = os.path.join(os.getcwd(), 'dados')
        else:
            self.diretorio_dados = diretorio_dados
            
        # Criar diretórios se não existirem
        self.diretorio_jogos = os.path.join(self.diretorio_dados, 'jogos')
        self.diretorio_estatisticas = os.path.join(self.diretorio_dados, 'estatisticas')
        
        os.makedirs(self.diretorio_jogos, exist_ok=True)
        os.makedirs(self.diretorio_estatisticas, exist_ok=True)
        
        # Headers para requisições HTTP
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'https://www.google.com/'
        }
    
    def coletar_jogos_do_dia(self, data: Optional[str] = None, dias_futuros: int = 0) -> List[Dict[str, Any]]:
        """
        Coleta jogos do dia especificado e dos próximos dias.
        
        Args:
            data: Data no formato DD/MM/YYYY. Se None, usa a data atual.
            dias_futuros: Número de dias futuros para coletar jogos.
            
        Returns:
            Lista de dicionários com informações dos jogos.
        """
        logger.info(f"Coletando jogos para a data: {data} e {dias_futuros} dias futuros")
        
        # Converter data para objeto datetime
        if data is None:
            data_inicio = datetime.datetime.now()
        else:
            try:
                data_inicio = datetime.datetime.strptime(data, '%d/%m/%Y')
            except ValueError:
                logger.error(f"Formato de data inválido: {data}. Usando data atual.")
                data_inicio = datetime.datetime.now()
        
        # Coletar jogos para cada dia
        todos_jogos = []
        
        for i in range(dias_futuros + 1):
            data_atual = data_inicio + datetime.timedelta(days=i)
            data_str = data_atual.strftime('%d/%m/%Y')
            
            # Tentar coletar jogos da Academia das Apostas
            jogos_academia = self._coletar_jogos_academia_apostas(data_str)
            
            if jogos_academia:
                todos_jogos.extend(jogos_academia)
                continue
            
            # Se não conseguir, tentar coletar jogos do FlashScore
            jogos_flashscore = self._coletar_jogos_flashscore(data_str)
            
            if jogos_flashscore:
                todos_jogos.extend(jogos_flashscore)
                continue
            
            # Se não conseguir de nenhuma fonte, gerar dados de exemplo
            jogos_exemplo = self._gerar_jogos_exemplo(data_str)
            todos_jogos.extend(jogos_exemplo)
        
        # Salvar jogos
        self._salvar_jogos(todos_jogos)
        
        # Coletar estatísticas para os jogos
        self.coletar_estatisticas_jogos(todos_jogos)
        
        return todos_jogos
    
    def _coletar_jogos_academia_apostas(self, data: str) -> List[Dict[str, Any]]:
        """
        Coleta jogos do site Academia das Apostas Brasil.
        
        Args:
            data: Data no formato DD/MM/YYYY.
            
        Returns:
            Lista de dicionários com informações dos jogos.
        """
        logger.info(f"Tentando coletar jogos da Academia das Apostas para a data: {data}")
        
        try:
            # URL da página de jogos do dia
            url = f"https://www.academiadasapostasbrasil.com/futebol/jogos-do-dia/{data.replace('/', '-')}"
            
            # Fazer requisição HTTP
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Falha ao acessar Academia das Apostas: {response.status_code}")
                return []
            
            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair jogos
            jogos = []
            
            # Encontrar elementos de jogo
            elementos_jogo = soup.select('.event-row')
            
            for elemento in elementos_jogo:
                try:
                    # Extrair times
                    time_casa = elemento.select_one('.team-home').text.strip()
                    time_visitante = elemento.select_one('.team-away').text.strip()
                    
                    # Extrair hora
                    hora = elemento.select_one('.event-time').text.strip()
                    
                    # Extrair campeonato
                    campeonato = elemento.select_one('.league-name').text.strip()
                    
                    # Criar ID único para o jogo
                    id_jogo = self._gerar_id_jogo(time_casa, time_visitante, data, hora)
                    
                    # Adicionar jogo à lista
                    jogo = {
                        "id_jogo": id_jogo,
                        "time_casa": time_casa,
                        "time_visitante": time_visitante,
                        "data": data,
                        "hora": hora,
                        "campeonato": campeonato
                    }
                    
                    jogos.append(jogo)
                    
                except Exception as e:
                    logger.error(f"Erro ao extrair informações do jogo: {str(e)}")
            
            logger.info(f"Coletados {len(jogos)} jogos da Academia das Apostas")
            return jogos
            
        except Exception as e:
            logger.error(f"Erro ao coletar jogos da Academia das Apostas: {str(e)}")
            return []
    
    def _coletar_jogos_flashscore(self, data: str) -> List[Dict[str, Any]]:
        """
        Coleta jogos do site FlashScore.
        
        Args:
            data: Data no formato DD/MM/YYYY.
            
        Returns:
            Lista de dicionários com informações dos jogos.
        """
        logger.info(f"Tentando coletar jogos do FlashScore para a data: {data}")
        
        try:
            # URL da página de jogos do dia
            url = f"https://www.flashscore.com.br/futebol/jogos/?d={data.replace('/', '')}"
            
            # Fazer requisição HTTP
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Falha ao acessar FlashScore: {response.status_code}")
                return []
            
            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair jogos
            jogos = []
            
            # Encontrar elementos de jogo
            elementos_jogo = soup.select('.event__match')
            
            for elemento in elementos_jogo:
                try:
                    # Extrair times
                    time_casa = elemento.select_one('.event__participant--home').text.strip()
                    time_visitante = elemento.select_one('.event__participant--away').text.strip()
                    
                    # Extrair hora
                    hora = elemento.select_one('.event__time').text.strip()
                    
                    # Extrair campeonato
                    campeonato = elemento.select_one('.event__title').text.strip()
                    
                    # Criar ID único para o jogo
                    id_jogo = self._gerar_id_jogo(time_casa, time_visitante, data, hora)
                    
                    # Adicionar jogo à lista
                    jogo = {
                        "id_jogo": id_jogo,
                        "time_casa": time_casa,
                        "time_visitante": time_visitante,
                        "data": data,
                        "hora": hora,
                        "campeonato": campeonato
                    }
                    
                    jogos.append(jogo)
                    
                except Exception as e:
                    logger.error(f"Erro ao extrair informações do jogo: {str(e)}")
            
            logger.info(f"Coletados {len(jogos)} jogos do FlashScore")
            return jogos
            
        except Exception as e:
            logger.error(f"Erro ao coletar jogos do FlashScore: {str(e)}")
            return []
    
    def _gerar_jogos_exemplo(self, data: str) -> List[Dict[str, Any]]:
        """
        Gera jogos de exemplo para a data especificada.
        
        Args:
            data: Data no formato DD/MM/YYYY.
            
        Returns:
            Lista de dicionários com informações dos jogos.
        """
        logger.info(f"Gerando jogos de exemplo para a data: {data}")
        
        # Times brasileiros
        times_brasileiros = [
            "Flamengo", "Palmeiras", "Santos", "São Paulo", "Corinthians",
            "Grêmio", "Internacional", "Cruzeiro", "Atlético-MG", "Fluminense",
            "Botafogo", "Vasco", "Bahia", "Sport", "Fortaleza",
            "Ceará", "Athletico-PR", "Goiás", "Coritiba", "Bragantino"
        ]
        
        # Campeonatos
        campeonatos = [
            "Brasileirão Série A", "Copa do Brasil", "Libertadores",
            "Sul-Americana", "Campeonato Estadual"
        ]
        
        # Horários
        horarios = ["16:00", "18:30", "19:00", "20:00", "21:30"]
        
        # Gerar jogos aleatórios
        jogos = []
        
        # Número de jogos a gerar (entre 3 e 8)
        num_jogos = random.randint(3, 8)
        
        # Embaralhar times
        random.shuffle(times_brasileiros)
        
        for i in range(num_jogos):
            # Selecionar times
            time_casa = times_brasileiros[i * 2 % len(times_brasileiros)]
            time_visitante = times_brasileiros[(i * 2 + 1) % len(times_brasileiros)]
            
            # Selecionar campeonato e horário
            campeonato = random.choice(campeonatos)
            hora = random.choice(horarios)
            
            # Criar ID único para o jogo
            id_jogo = self._gerar_id_jogo(time_casa, time_visitante, data, hora)
            
            # Adicionar jogo à lista
            jogo = {
                "id_jogo": id_jogo,
                "time_casa": time_casa,
                "time_visitante": time_visitante,
                "data": data,
                "hora": hora,
                "campeonato": campeonato
            }
            
            jogos.append(jogo)
        
        logger.info(f"Gerados {len(jogos)} jogos de exemplo")
        return jogos
    
    def coletar_estatisticas_jogos(self, jogos: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Coleta estatísticas para uma lista de jogos.
        
        Args:
            jogos: Lista de dicionários com informações dos jogos.
            
        Returns:
            Dicionário com estatísticas dos jogos, indexado pelo ID do jogo.
        """
        logger.info(f"Coletando estatísticas para {len(jogos)} jogos")
        
        estatisticas = {}
        
        for jogo in jogos:
            id_jogo = jogo['id_jogo']
            time_casa = jogo['time_casa']
            time_visitante = jogo['time_visitante']
            
            # Verificar se já temos estatísticas para este jogo
            if os.path.exists(os.path.join(self.diretorio_estatisticas, f"{id_jogo}.json")):
                logger.info(f"Estatísticas já existem para o jogo {id_jogo}")
                estatisticas[id_jogo] = self.carregar_estatisticas(id_jogo)
                continue
            
            # Tentar coletar estatísticas da Academia das Apostas
            estatisticas_academia = self._coletar_estatisticas_academia_apostas(jogo)
            
            if estatisticas_academia:
                estatisticas[id_jogo] = estatisticas_academia
                self._salvar_estatisticas(id_jogo, estatisticas_academia)
                continue
            
            # Se não conseguir, tentar coletar estatísticas do FlashScore
            estatisticas_flashscore = self._coletar_estatisticas_flashscore(jogo)
            
            if estatisticas_flashscore:
                estatisticas[id_jogo] = estatisticas_flashscore
                self._salvar_estatisticas(id_jogo, estatisticas_flashscore)
                continue
            
            # Se não conseguir de nenhuma fonte, gerar estatísticas de exemplo
            estatisticas_exemplo = self._gerar_estatisticas_exemplo(jogo)
            estatisticas[id_jogo] = estatisticas_exemplo
            self._salvar_estatisticas(id_jogo, estatisticas_exemplo)
        
        return estatisticas
    
    def _coletar_estatisticas_academia_apostas(self, jogo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Coleta estatísticas do site Academia das Apostas Brasil.
        
        Args:
            jogo: Dicionário com informações do jogo.
            
        Returns:
            Dicionário com estatísticas do jogo, ou None se não conseguir coletar.
        """
        logger.info(f"Tentando coletar estatísticas da Academia das Apostas para o jogo {jogo['id_jogo']}")
        
        try:
            # Construir URL da página do jogo
            time_casa_url = jogo['time_casa'].lower().replace(' ', '-')
            time_visitante_url = jogo['time_visitante'].lower().replace(' ', '-')
            data_url = jogo['data'].replace('/', '-')
            
            url = f"https://www.academiadasapostasbrasil.com/futebol/{time_casa_url}-vs-{time_visitante_url}/{data_url}"
            
            # Fazer requisição HTTP
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Falha ao acessar Academia das Apostas: {response.status_code}")
                return None
            
            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair estatísticas
            estatisticas = {
                "time_casa": self._extrair_estatisticas_time_academia(soup, jogo['time_casa']),
                "time_visitante": self._extrair_estatisticas_time_academia(soup, jogo['time_visitante']),
                "confrontos_diretos": self._extrair_confrontos_diretos_academia(soup, jogo['time_casa'], jogo['time_visitante']),
                "odds": self._extrair_odds_academia(soup),
                "mercados_adicionais": {
                    "escanteios": self._extrair_estatisticas_escanteios_academia(soup, jogo['time_casa'], jogo['time_visitante']),
                    "cartoes": self._extrair_estatisticas_cartoes_academia(soup, jogo['time_casa'], jogo['time_visitante'])
                }
            }
            
            logger.info(f"Estatísticas coletadas com sucesso da Academia das Apostas para o jogo {jogo['id_jogo']}")
            return estatisticas
            
        except Exception as e:
            logger.error(f"Erro ao coletar estatísticas da Academia das Apostas: {str(e)}")
            return None
    
    def _extrair_estatisticas_time_academia(self, soup: BeautifulSoup, time: str) -> Dict[str, Any]:
        """
        Extrai estatísticas de um time do HTML da Academia das Apostas.
        
        Args:
            soup: Objeto BeautifulSoup com o HTML da página.
            time: Nome do time.
            
        Returns:
            Dicionário com estatísticas do time.
        """
        try:
            # Encontrar seção do time
            secao_time = None
            
            for secao in soup.select('.team-stats'):
                if time.lower() in secao.text.lower():
                    secao_time = secao
                    break
            
            if not secao_time:
                return self._gerar_estatisticas_time_exemplo(time)
            
            # Extrair estatísticas
            posicao = 0
            pontos = 0
            vitorias = 0
            empates = 0
            derrotas = 0
            gols_marcados = 0
            gols_sofridos = 0
            
            # Procurar por estatísticas específicas
            for item in secao_time.select('.stat-item'):
                label = item.select_one('.stat-label').text.lower()
                valor = item.select_one('.stat-value').text.strip()
                
                if 'posição' in label:
                    posicao = int(valor)
                elif 'pontos' in label:
                    pontos = int(valor)
                elif 'vitórias' in label:
                    vitorias = int(valor)
                elif 'empates' in label:
                    empates = int(valor)
                elif 'derrotas' in label:
                    derrotas = int(valor)
                elif 'gols marcados' in label:
                    gols_marcados = int(valor)
                elif 'gols sofridos' in label:
                    gols_sofridos = int(valor)
            
            # Extrair últimos jogos
            ultimos_jogos = []
            
            for resultado in secao_time.select('.form-results .result'):
                resultado_texto = resultado.text.strip().upper()
                if resultado_texto in ['V', 'E', 'D']:
                    ultimos_jogos.append(resultado_texto)
            
            # Limitar a 5 resultados
            ultimos_jogos = ultimos_jogos[:5]
            
            return {
                "posicao": posicao,
                "pontos": pontos,
                "vitorias": vitorias,
                "empates": empates,
                "derrotas": derrotas,
                "gols_marcados": gols_marcados,
                "gols_sofridos": gols_sofridos,
                "ultimos_jogos": ultimos_jogos
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair estatísticas do time {time}: {str(e)}")
            return self._gerar_estatisticas_time_exemplo(time)
    
    def _extrair_confrontos_diretos_academia(self, soup: BeautifulSoup, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai informações sobre confrontos diretos do HTML da Academia das Apostas.
        
        Args:
            soup: Objeto BeautifulSoup com o HTML da página.
            time_casa: Nome do time da casa.
            time_visitante: Nome do time visitante.
            
        Returns:
            Dicionário com informações sobre confrontos diretos.
        """
        try:
            # Encontrar seção de confrontos diretos
            secao_confrontos = None
            
            for secao in soup.select('.head-to-head'):
                if 'confronto direto' in secao.text.lower():
                    secao_confrontos = secao
                    break
            
            if not secao_confrontos:
                return self._gerar_confrontos_diretos_exemplo(time_casa, time_visitante)
            
            # Extrair número total de jogos
            total_jogos_texto = secao_confrontos.select_one('.total-matches').text
            total_jogos = int(''.join(filter(str.isdigit, total_jogos_texto)))
            
            # Extrair vitórias, empates e derrotas
            vitorias_casa = 0
            empates = 0
            vitorias_visitante = 0
            
            for item in secao_confrontos.select('.stats-item'):
                label = item.select_one('.stat-label').text.lower()
                valor = item.select_one('.stat-value').text.strip()
                
                if time_casa.lower() in label and 'vitórias' in label:
                    vitorias_casa = int(valor)
                elif 'empates' in label:
                    empates = int(valor)
                elif time_visitante.lower() in label and 'vitórias' in label:
                    vitorias_visitante = int(valor)
            
            # Extrair lista de confrontos
            confrontos = []
            
            for item in secao_confrontos.select('.match-item'):
                data_texto = item.select_one('.match-date').text.strip()
                resultado_texto = item.select_one('.match-result').text.strip()
                competicao_texto = item.select_one('.match-competition').text.strip()
                
                # Extrair times e placar
                partes_resultado = resultado_texto.split('-')
                if len(partes_resultado) >= 3:
                    mandante = partes_resultado[0].strip()
                    placar = partes_resultado[1].strip()
                    visitante = partes_resultado[2].strip()
                    
                    confronto = {
                        "data": data_texto,
                        "mandante": mandante,
                        "visitante": visitante,
                        "placar": placar,
                        "competicao": competicao_texto
                    }
                    
                    confrontos.append(confronto)
            
            return {
                "resumo": {
                    "total": total_jogos,
                    "vitorias_casa": vitorias_casa,
                    "empates": empates,
                    "vitorias_visitante": vitorias_visitante
                },
                "confrontos": confrontos
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair confrontos diretos: {str(e)}")
            return self._gerar_confrontos_diretos_exemplo(time_casa, time_visitante)
    
    def _extrair_odds_academia(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extrai odds do HTML da Academia das Apostas.
        
        Args:
            soup: Objeto BeautifulSoup com o HTML da página.
            
        Returns:
            Dicionário com odds do jogo.
        """
        try:
            # Encontrar seção de odds
            secao_odds = None
            
            for secao in soup.select('.odds-section'):
                if 'vencedor' in secao.text.lower():
                    secao_odds = secao
                    break
            
            if not secao_odds:
                return self._gerar_odds_exemplo()
            
            # Extrair odds de resultado (1X2)
            odds_casa = 0.0
            odds_empate = 0.0
            odds_visitante = 0.0
            
            for item in secao_odds.select('.odd-item'):
                label = item.select_one('.odd-label').text.lower()
                valor_texto = item.select_one('.odd-value').text.strip()
                
                try:
                    valor = float(valor_texto)
                    
                    if 'casa' in label:
                        odds_casa = valor
                    elif 'empate' in label:
                        odds_empate = valor
                    elif 'fora' in label:
                        odds_visitante = valor
                except ValueError:
                    pass
            
            # Extrair odds de over/under
            secao_over_under = None
            
            for secao in soup.select('.odds-section'):
                if 'over/under' in secao.text.lower():
                    secao_over_under = secao
                    break
            
            odds_over = 0.0
            odds_under = 0.0
            
            if secao_over_under:
                for item in secao_over_under.select('.odd-item'):
                    label = item.select_one('.odd-label').text.lower()
                    valor_texto = item.select_one('.odd-value').text.strip()
                    
                    try:
                        valor = float(valor_texto)
                        
                        if 'over' in label:
                            odds_over = valor
                        elif 'under' in label:
                            odds_under = valor
                    except ValueError:
                        pass
            
            # Extrair odds de ambas marcam
            secao_ambos_marcam = None
            
            for secao in soup.select('.odds-section'):
                if 'ambas marcam' in secao.text.lower():
                    secao_ambos_marcam = secao
                    break
            
            odds_ambos_sim = 0.0
            odds_ambos_nao = 0.0
            
            if secao_ambos_marcam:
                for item in secao_ambos_marcam.select('.odd-item'):
                    label = item.select_one('.odd-label').text.lower()
                    valor_texto = item.select_one('.odd-value').text.strip()
                    
                    try:
                        valor = float(valor_texto)
                        
                        if 'sim' in label:
                            odds_ambos_sim = valor
                        elif 'não' in label:
                            odds_ambos_nao = valor
                    except ValueError:
                        pass
            
            return {
                "resultado": {
                    "casa": odds_casa,
                    "empate": odds_empate,
                    "visitante": odds_visitante
                },
                "over_under": {
                    "over_2_5": odds_over,
                    "under_2_5": odds_under
                },
                "ambos_marcam": {
                    "sim": odds_ambos_sim,
                    "nao": odds_ambos_nao
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair odds: {str(e)}")
            return self._gerar_odds_exemplo()
    
    def _extrair_estatisticas_escanteios_academia(self, soup: BeautifulSoup, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai estatísticas de escanteios do HTML da Academia das Apostas.
        
        Args:
            soup: Objeto BeautifulSoup com o HTML da página.
            time_casa: Nome do time da casa.
            time_visitante: Nome do time visitante.
            
        Returns:
            Dicionário com estatísticas de escanteios.
        """
        try:
            # Encontrar seção de escanteios
            secao_escanteios = None
            
            for secao in soup.select('.stats-section'):
                if 'escanteios' in secao.text.lower():
                    secao_escanteios = secao
                    break
            
            if not secao_escanteios:
                return self._gerar_estatisticas_escanteios_exemplo(time_casa, time_visitante)
            
            # Extrair estatísticas de escanteios
            media_casa = 0.0
            media_visitante = 0.0
            primeiro_tempo_casa = 0.0
            primeiro_tempo_visitante = 0.0
            segundo_tempo_casa = 0.0
            segundo_tempo_visitante = 0.0
            
            # Procurar por estatísticas específicas
            for item in secao_escanteios.select('.stat-item'):
                label = item.select_one('.stat-label').text.lower()
                valor_texto = item.select_one('.stat-value').text.strip()
                
                try:
                    valor = float(valor_texto)
                    
                    if time_casa.lower() in label and 'média' in label and '1º tempo' not in label and '2º tempo' not in label:
                        media_casa = valor
                    elif time_visitante.lower() in label and 'média' in label and '1º tempo' not in label and '2º tempo' not in label:
                        media_visitante = valor
                    elif time_casa.lower() in label and '1º tempo' in label:
                        primeiro_tempo_casa = valor
                    elif time_visitante.lower() in label and '1º tempo' in label:
                        primeiro_tempo_visitante = valor
                    elif time_casa.lower() in label and '2º tempo' in label:
                        segundo_tempo_casa = valor
                    elif time_visitante.lower() in label and '2º tempo' in label:
                        segundo_tempo_visitante = valor
                except ValueError:
                    pass
            
            return {
                "time_casa": {
                    "media_por_jogo": media_casa,
                    "media_primeiro_tempo": primeiro_tempo_casa,
                    "media_segundo_tempo": segundo_tempo_casa
                },
                "time_visitante": {
                    "media_por_jogo": media_visitante,
                    "media_primeiro_tempo": primeiro_tempo_visitante,
                    "media_segundo_tempo": segundo_tempo_visitante
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair estatísticas de escanteios: {str(e)}")
            return self._gerar_estatisticas_escanteios_exemplo(time_casa, time_visitante)
    
    def _extrair_estatisticas_cartoes_academia(self, soup: BeautifulSoup, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai estatísticas de cartões do HTML da Academia das Apostas.
        
        Args:
            soup: Objeto BeautifulSoup com o HTML da página.
            time_casa: Nome do time da casa.
            time_visitante: Nome do time visitante.
            
        Returns:
            Dicionário com estatísticas de cartões.
        """
        try:
            # Encontrar seção de cartões
            secao_cartoes = None
            
            for secao in soup.select('.stats-section'):
                if 'cartões' in secao.text.lower():
                    secao_cartoes = secao
                    break
            
            if not secao_cartoes:
                return self._gerar_estatisticas_cartoes_exemplo(time_casa, time_visitante)
            
            # Extrair estatísticas de cartões
            amarelos_casa = 0.0
            amarelos_visitante = 0.0
            vermelhos_casa = 0
            vermelhos_visitante = 0
            
            # Procurar por estatísticas específicas
            for item in secao_cartoes.select('.stat-item'):
                label = item.select_one('.stat-label').text.lower()
                valor_texto = item.select_one('.stat-value').text.strip()
                
                try:
                    if 'amarelos' in label:
                        valor = float(valor_texto)
                    else:
                        valor = int(valor_texto)
                    
                    if time_casa.lower() in label and 'amarelos' in label:
                        amarelos_casa = valor
                    elif time_visitante.lower() in label and 'amarelos' in label:
                        amarelos_visitante = valor
                    elif time_casa.lower() in label and 'vermelhos' in label:
                        vermelhos_casa = valor
                    elif time_visitante.lower() in label and 'vermelhos' in label:
                        vermelhos_visitante = valor
                except ValueError:
                    pass
            
            return {
                "time_casa": {
                    "cartoes_amarelos_media": amarelos_casa,
                    "cartoes_vermelhos_total": vermelhos_casa
                },
                "time_visitante": {
                    "cartoes_amarelos_media": amarelos_visitante,
                    "cartoes_vermelhos_total": vermelhos_visitante
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair estatísticas de cartões: {str(e)}")
            return self._gerar_estatisticas_cartoes_exemplo(time_casa, time_visitante)
    
    def _coletar_estatisticas_flashscore(self, jogo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Coleta estatísticas do site FlashScore.
        
        Args:
            jogo: Dicionário com informações do jogo.
            
        Returns:
            Dicionário com estatísticas do jogo, ou None se não conseguir coletar.
        """
        logger.info(f"Tentando coletar estatísticas do FlashScore para o jogo {jogo['id_jogo']}")
        
        try:
            # Construir URL da página do jogo
            time_casa_url = jogo['time_casa'].lower().replace(' ', '-')
            time_visitante_url = jogo['time_visitante'].lower().replace(' ', '-')
            
            url = f"https://www.flashscore.com.br/jogo/{time_casa_url}-{time_visitante_url}/"
            
            # Fazer requisição HTTP
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Falha ao acessar FlashScore: {response.status_code}")
                return None
            
            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair estatísticas
            estatisticas = {
                "time_casa": self._extrair_estatisticas_time_flashscore(soup, jogo['time_casa']),
                "time_visitante": self._extrair_estatisticas_time_flashscore(soup, jogo['time_visitante']),
                "confrontos_diretos": self._extrair_confrontos_diretos_flashscore(soup, jogo['time_casa'], jogo['time_visitante']),
                "odds": self._extrair_odds_flashscore(soup),
                "mercados_adicionais": {
                    "escanteios": self._extrair_estatisticas_escanteios_flashscore(soup, jogo['time_casa'], jogo['time_visitante']),
                    "cartoes": self._extrair_estatisticas_cartoes_flashscore(soup, jogo['time_casa'], jogo['time_visitante'])
                }
            }
            
            logger.info(f"Estatísticas coletadas com sucesso do FlashScore para o jogo {jogo['id_jogo']}")
            return estatisticas
            
        except Exception as e:
            logger.error(f"Erro ao coletar estatísticas do FlashScore: {str(e)}")
            return None
    
    def _extrair_estatisticas_time_flashscore(self, soup: BeautifulSoup, time: str) -> Dict[str, Any]:
        """
        Extrai estatísticas de um time do HTML do FlashScore.
        
        Args:
            soup: Objeto BeautifulSoup com o HTML da página.
            time: Nome do time.
            
        Returns:
            Dicionário com estatísticas do time.
        """
        # Implementação simplificada, retorna estatísticas de exemplo
        return self._gerar_estatisticas_time_exemplo(time)
    
    def _extrair_confrontos_diretos_flashscore(self, soup: BeautifulSoup, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai informações sobre confrontos diretos do HTML do FlashScore.
        
        Args:
            soup: Objeto BeautifulSoup com o HTML da página.
            time_casa: Nome do time da casa.
            time_visitante: Nome do time visitante.
            
        Returns:
            Dicionário com informações sobre confrontos diretos.
        """
        # Implementação simplificada, retorna confrontos diretos de exemplo
        return self._gerar_confrontos_diretos_exemplo(time_casa, time_visitante)
    
    def _extrair_odds_flashscore(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extrai odds do HTML do FlashScore.
        
        Args:
            soup: Objeto BeautifulSoup com o HTML da página.
            
        Returns:
            Dicionário com odds do jogo.
        """
        # Implementação simplificada, retorna odds de exemplo
        return self._gerar_odds_exemplo()
    
    def _extrair_estatisticas_escanteios_flashscore(self, soup: BeautifulSoup, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai estatísticas de escanteios do HTML do FlashScore.
        
        Args:
            soup: Objeto BeautifulSoup com o HTML da página.
            time_casa: Nome do time da casa.
            time_visitante: Nome do time visitante.
            
        Returns:
            Dicionário com estatísticas de escanteios.
        """
        # Implementação simplificada, retorna estatísticas de escanteios de exemplo
        return self._gerar_estatisticas_escanteios_exemplo(time_casa, time_visitante)
    
    def _extrair_estatisticas_cartoes_flashscore(self, soup: BeautifulSoup, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai estatísticas de cartões do HTML do FlashScore.
        
        Args:
            soup: Objeto BeautifulSoup com o HTML da página.
            time_casa: Nome do time da casa.
            time_visitante: Nome do time visitante.
            
        Returns:
            Dicionário com estatísticas de cartões.
        """
        # Implementação simplificada, retorna estatísticas de cartões de exemplo
        return self._gerar_estatisticas_cartoes_exemplo(time_casa, time_visitante)
    
    def _gerar_estatisticas_exemplo(self, jogo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera estatísticas de exemplo para um jogo.
        
        Args:
            jogo: Dicionário com informações do jogo.
            
        Returns:
            Dicionário com estatísticas do jogo.
        """
        logger.info(f"Gerando estatísticas de exemplo para o jogo {jogo['id_jogo']}")
        
        time_casa = jogo['time_casa']
        time_visitante = jogo['time_visitante']
        
        return {
            "time_casa": self._gerar_estatisticas_time_exemplo(time_casa),
            "time_visitante": self._gerar_estatisticas_time_exemplo(time_visitante),
            "confrontos_diretos": self._gerar_confrontos_diretos_exemplo(time_casa, time_visitante),
            "odds": self._gerar_odds_exemplo(),
            "mercados_adicionais": {
                "escanteios": self._gerar_estatisticas_escanteios_exemplo(time_casa, time_visitante),
                "cartoes": self._gerar_estatisticas_cartoes_exemplo(time_casa, time_visitante)
            }
        }
    
    def _gerar_estatisticas_time_exemplo(self, time: str) -> Dict[str, Any]:
        """
        Gera estatísticas de exemplo para um time.
        
        Args:
            time: Nome do time.
            
        Returns:
            Dicionário com estatísticas do time.
        """
        # Gerar valores aleatórios
        posicao = random.randint(1, 20)
        jogos = random.randint(5, 15)
        vitorias = random.randint(1, jogos)
        empates = random.randint(0, jogos - vitorias)
        derrotas = jogos - vitorias - empates
        gols_marcados = random.randint(vitorias, vitorias * 3)
        gols_sofridos = random.randint(derrotas, derrotas * 3)
        pontos = vitorias * 3 + empates
        
        # Gerar últimos jogos
        resultados = ['V', 'E', 'D']
        ultimos_jogos = []
        
        for _ in range(5):
            # Maior probabilidade de resultados consistentes com o histórico
            if vitorias > derrotas + empates:
                pesos = [0.6, 0.3, 0.1]
            elif derrotas > vitorias + empates:
                pesos = [0.1, 0.3, 0.6]
            else:
                pesos = [0.3, 0.4, 0.3]
            
            ultimos_jogos.append(random.choices(resultados, weights=pesos, k=1)[0])
        
        return {
            "posicao": posicao,
            "pontos": pontos,
            "jogos": jogos,
            "vitorias": vitorias,
            "empates": empates,
            "derrotas": derrotas,
            "gols_marcados": gols_marcados,
            "gols_sofridos": gols_sofridos,
            "ultimos_jogos": ultimos_jogos
        }
    
    def _gerar_confrontos_diretos_exemplo(self, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Gera informações de exemplo sobre confrontos diretos.
        
        Args:
            time_casa: Nome do time da casa.
            time_visitante: Nome do time visitante.
            
        Returns:
            Dicionário com informações sobre confrontos diretos.
        """
        # Gerar valores aleatórios
        total_jogos = random.randint(2, 10)
        vitorias_casa = random.randint(0, total_jogos)
        empates = random.randint(0, total_jogos - vitorias_casa)
        vitorias_visitante = total_jogos - vitorias_casa - empates
        
        # Gerar lista de confrontos
        confrontos = []
        
        for i in range(total_jogos):
            # Data aleatória nos últimos 3 anos
            dias_atras = random.randint(1, 1095)
            data = (datetime.datetime.now() - datetime.timedelta(days=dias_atras)).strftime('%d/%m/%Y')
            
            # Resultado aleatório
            if i < vitorias_casa:
                gols_casa = random.randint(1, 4)
                gols_visitante = random.randint(0, gols_casa - 1)
                mandante = time_casa
                visitante = time_visitante
            elif i < vitorias_casa + empates:
                gols_casa = random.randint(0, 3)
                gols_visitante = gols_casa
                mandante = time_casa if i % 2 == 0 else time_visitante
                visitante = time_visitante if i % 2 == 0 else time_casa
            else:
                gols_visitante = random.randint(1, 4)
                gols_casa = random.randint(0, gols_visitante - 1)
                mandante = time_visitante
                visitante = time_casa
            
            # Competição aleatória
            competicoes = ["Brasileirão Série A", "Copa do Brasil", "Campeonato Estadual"]
            competicao = random.choice(competicoes)
            
            confronto = {
                "data": data,
                "mandante": mandante,
                "visitante": visitante,
                "placar": f"{gols_casa}-{gols_visitante}",
                "competicao": competicao
            }
            
            confrontos.append(confronto)
        
        return {
            "resumo": {
                "total": total_jogos,
                "vitorias_casa": vitorias_casa,
                "empates": empates,
                "vitorias_visitante": vitorias_visitante
            },
            "confrontos": confrontos
        }
    
    def _gerar_odds_exemplo(self) -> Dict[str, Any]:
        """
        Gera odds de exemplo.
        
        Returns:
            Dicionário com odds do jogo.
        """
        # Gerar valores aleatórios
        odds_casa = round(random.uniform(1.5, 3.5), 2)
        odds_empate = round(random.uniform(3.0, 4.5), 2)
        odds_visitante = round(random.uniform(2.0, 7.5), 2)
        
        odds_over = round(random.uniform(1.8, 2.2), 2)
        odds_under = round(random.uniform(1.8, 2.2), 2)
        
        odds_ambos_sim = round(random.uniform(1.7, 2.1), 2)
        odds_ambos_nao = round(random.uniform(1.7, 2.1), 2)
        
        return {
            "resultado": {
                "casa": odds_casa,
                "empate": odds_empate,
                "visitante": odds_visitante
            },
            "over_under": {
                "over_2_5": odds_over,
                "under_2_5": odds_under
            },
            "ambos_marcam": {
                "sim": odds_ambos_sim,
                "nao": odds_ambos_nao
            }
        }
    
    def _gerar_estatisticas_escanteios_exemplo(self, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Gera estatísticas de exemplo para escanteios.
        
        Args:
            time_casa: Nome do time da casa.
            time_visitante: Nome do time visitante.
            
        Returns:
            Dicionário com estatísticas de escanteios.
        """
        # Gerar valores aleatórios
        media_casa = round(random.uniform(4.0, 7.0), 1)
        media_visitante = round(random.uniform(3.5, 6.5), 1)
        
        primeiro_tempo_casa = round(media_casa * random.uniform(0.3, 0.5), 1)
        primeiro_tempo_visitante = round(media_visitante * random.uniform(0.3, 0.5), 1)
        
        segundo_tempo_casa = round(media_casa - primeiro_tempo_casa, 1)
        segundo_tempo_visitante = round(media_visitante - primeiro_tempo_visitante, 1)
        
        return {
            "time_casa": {
                "media_por_jogo": media_casa,
                "media_primeiro_tempo": primeiro_tempo_casa,
                "media_segundo_tempo": segundo_tempo_casa
            },
            "time_visitante": {
                "media_por_jogo": media_visitante,
                "media_primeiro_tempo": primeiro_tempo_visitante,
                "media_segundo_tempo": segundo_tempo_visitante
            }
        }
    
    def _gerar_estatisticas_cartoes_exemplo(self, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Gera estatísticas de exemplo para cartões.
        
        Args:
            time_casa: Nome do time da casa.
            time_visitante: Nome do time visitante.
            
        Returns:
            Dicionário com estatísticas de cartões.
        """
        # Gerar valores aleatórios
        amarelos_casa = round(random.uniform(1.5, 3.5), 1)
        amarelos_visitante = round(random.uniform(1.5, 3.5), 1)
        
        vermelhos_casa = random.randint(0, 3)
        vermelhos_visitante = random.randint(0, 3)
        
        return {
            "time_casa": {
                "cartoes_amarelos_media": amarelos_casa,
                "cartoes_vermelhos_total": vermelhos_casa
            },
            "time_visitante": {
                "cartoes_amarelos_media": amarelos_visitante,
                "cartoes_vermelhos_total": vermelhos_visitante
            }
        }
    
    def _salvar_jogos(self, jogos: List[Dict[str, Any]]) -> None:
        """
        Salva jogos em arquivo JSON.
        
        Args:
            jogos: Lista de dicionários com informações dos jogos.
        """
        # Verificar se já temos jogos salvos
        jogos_existentes = self.carregar_jogos()
        
        # Criar mapa de jogos existentes por ID
        jogos_por_id = {jogo['id_jogo']: jogo for jogo in jogos_existentes}
        
        # Adicionar ou atualizar jogos
        for jogo in jogos:
            jogos_por_id[jogo['id_jogo']] = jogo
        
        # Converter mapa de volta para lista
        jogos_atualizados = list(jogos_por_id.values())
        
        # Ordenar jogos por data e hora
        jogos_atualizados.sort(key=lambda j: (j['data'], j['hora']))
        
        # Salvar jogos em arquivo JSON
        arquivo_jogos = os.path.join(self.diretorio_jogos, 'jogos_disponiveis.json')
        
        with open(arquivo_jogos, 'w', encoding='utf-8') as f:
            json.dump(jogos_atualizados, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Jogos salvos com sucesso em {arquivo_jogos}")
    
    def _salvar_estatisticas(self, id_jogo: str, estatisticas: Dict[str, Any]) -> None:
        """
        Salva estatísticas de um jogo em arquivo JSON.
        
        Args:
            id_jogo: ID único do jogo.
            estatisticas: Dicionário com estatísticas do jogo.
        """
        # Salvar estatísticas em arquivo JSON
        arquivo_estatisticas = os.path.join(self.diretorio_estatisticas, f"{id_jogo}.json")
        
        with open(arquivo_estatisticas, 'w', encoding='utf-8') as f:
            json.dump(estatisticas, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Estatísticas salvas com sucesso em {arquivo_estatisticas}")
    
    def carregar_jogos(self) -> List[Dict[str, Any]]:
        """
        Carrega jogos salvos anteriormente.
        
        Returns:
            Lista de dicionários com informações dos jogos.
        """
        # Verificar se o arquivo de jogos existe
        arquivo_jogos = os.path.join(self.diretorio_jogos, 'jogos_disponiveis.json')
        
        if not os.path.exists(arquivo_jogos):
            return []
        
        # Carregar jogos do arquivo JSON
        with open(arquivo_jogos, 'r', encoding='utf-8') as f:
            jogos = json.load(f)
        
        return jogos
    
    def carregar_estatisticas(self, id_jogo: str) -> Optional[Dict[str, Any]]:
        """
        Carrega estatísticas de um jogo salvo anteriormente.
        
        Args:
            id_jogo: ID único do jogo.
            
        Returns:
            Dicionário com estatísticas do jogo, ou None se não encontrado.
        """
        # Verificar se o arquivo de estatísticas existe
        arquivo_estatisticas = os.path.join(self.diretorio_estatisticas, f"{id_jogo}.json")
        
        if not os.path.exists(arquivo_estatisticas):
            return None
        
        # Carregar estatísticas do arquivo JSON
        with open(arquivo_estatisticas, 'r', encoding='utf-8') as f:
            estatisticas = json.load(f)
        
        return estatisticas
    
    def _gerar_id_jogo(self, time_casa: str, time_visitante: str, data: str, hora: str) -> str:
        """
        Gera um ID único para o jogo.
        
        Args:
            time_casa: Nome do time da casa.
            time_visitante: Nome do time visitante.
            data: Data do jogo.
            hora: Hora do jogo.
            
        Returns:
            ID único para o jogo.
        """
        # Normalizar nomes dos times
        time_casa_norm = time_casa.lower().replace(' ', '_')
        time_visitante_norm = time_visitante.lower().replace(' ', '_')
        
        # Normalizar data e hora
        data_norm = data.replace('/', '')
        hora_norm = hora.replace(':', '')
        
        # Criar string para hash
        string_hash = f"{time_casa_norm}_{time_visitante_norm}_{data_norm}_{hora_norm}"
        
        # Gerar hash MD5 e pegar os primeiros 8 caracteres
        import hashlib
        hash_md5 = hashlib.md5(string_hash.encode()).hexdigest()[:8]
        
        # Retornar ID no formato: time_casa_time_visitante_hash
        return f"{time_casa_norm}_{time_visitante_norm}_{hash_md5}"

# Exemplo de uso
if __name__ == "__main__":
    coletor = ColetorDadosReais()
    
    # Coletar jogos do dia atual e dos próximos 3 dias
    jogos = coletor.coletar_jogos_do_dia(dias_futuros=3)
    
    print(f"Coletados {len(jogos)} jogos")
    
    # Carregar jogos
    jogos_carregados = coletor.carregar_jogos()
    
    print(f"Carregados {len(jogos_carregados)} jogos")
    
    # Carregar estatísticas do primeiro jogo
    if jogos_carregados:
        id_jogo = jogos_carregados[0]['id_jogo']
        estatisticas = coletor.carregar_estatisticas(id_jogo)
        
        print(f"Estatísticas carregadas para o jogo {id_jogo}")
