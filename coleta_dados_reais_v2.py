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
        self.diretorio_debug = os.path.join(self.diretorio_dados, 'debug')
        os.makedirs(self.diretorio_jogos, exist_ok=True)
        os.makedirs(self.diretorio_estatisticas, exist_ok=True)
        os.makedirs(self.diretorio_debug, exist_ok=True)

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

        # Verificar se a data está muito no futuro (mais de 30 dias)
        data_atual = datetime.datetime.now()
        if (data_inicio - data_atual).days > 30:
            logger.warning(f"Data {data} está muito no futuro. Alguns sites podem não ter dados disponíveis.")

        # Coletar jogos para cada dia
        todos_jogos = []
        for i in range(dias_futuros + 1):
            data_atual = data_inicio + datetime.timedelta(days=i)
            data_str = data_atual.strftime('%d/%m/%Y')

            # Tentar diferentes fontes de dados
            jogos_coletados = False
            
            # Tentar coletar jogos do FlashScore (prioridade 1)
            jogos_flashscore = self._coletar_jogos_flashscore(data_str)
            if jogos_flashscore:
                todos_jogos.extend(jogos_flashscore)
                jogos_coletados = True
                logger.info(f"Jogos coletados com sucesso do FlashScore para a data {data_str}")
            
            # Se não conseguir, tentar coletar jogos da Academia das Apostas (prioridade 2)
            if not jogos_coletados:
                jogos_academia = self._coletar_jogos_academia_apostas(data_str)
                if jogos_academia:
                    todos_jogos.extend(jogos_academia)
                    jogos_coletados = True
                    logger.info(f"Jogos coletados com sucesso da Academia das Apostas para a data {data_str}")
            
            # Se não conseguir de nenhuma fonte, tentar coletar de fontes alternativas (prioridade 3)
            if not jogos_coletados:
                jogos_alternativa = self._coletar_jogos_fonte_alternativa(data_str)
                if jogos_alternativa:
                    todos_jogos.extend(jogos_alternativa)
                    jogos_coletados = True
                    logger.info(f"Jogos coletados com sucesso de fonte alternativa para a data {data_str}")
            
            # Se não conseguir de nenhuma fonte, registrar falha
            if not jogos_coletados:
                logger.error(f"Não foi possível coletar jogos para a data {data_str} de nenhuma fonte")

        # Se não conseguiu coletar nenhum jogo, lançar exceção
        if not todos_jogos:
            raise Exception("Nenhum jogo encontrado")

        # Salvar jogos
        self._salvar_jogos(todos_jogos)

        # Coletar estatísticas para os jogos
        self.coletar_estatisticas_jogos(todos_jogos)

        return todos_jogos

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
            # Formatar data para o formato usado pelo FlashScore (YYYYMMDD)
            data_obj = datetime.datetime.strptime(data, '%d/%m/%Y')
            data_formatada = data_obj.strftime('%Y%m%d')
            
            # URLs alternativas para tentar
            urls = [
                f"https://www.flashscore.com.br/futebol/?d={data_formatada}",
                f"https://www.flashscore.com.br/futebol/jogos/?d={data_formatada}",
                f"https://www.flashscore.com.br/futebol/jogos-de-hoje/?d={data_formatada}"
            ]
            
            # Cabeçalhos específicos para o FlashScore
            headers_flashscore = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Referer': 'https://www.flashscore.com.br/',
                'Host': 'www.flashscore.com.br',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            
            # Tentar cada URL
            for url in urls:
                try:
                    logger.info(f"Tentando acessar URL: {url}")
                    response = requests.get(url, headers=headers_flashscore, timeout=15)
                    
                    # Salvar HTML para debug
                    debug_file = os.path.join(self.diretorio_debug, f"flashscore_{data_formatada}_{urls.index(url)}.html")
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    logger.info(f"HTML salvo para debug em {debug_file}")
                    
                    if response.status_code != 200:
                        logger.warning(f"Falha ao acessar FlashScore URL {url}: {response.status_code}")
                        continue
                    
                    # Parsear HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Tentar diferentes seletores para encontrar jogos
                    jogos = self._extrair_jogos_flashscore(soup, data)
                    
                    if jogos:
                        logger.info(f"Coletados {len(jogos)} jogos do FlashScore via URL {url}")
                        return jogos
                    
                except Exception as e:
                    logger.error(f"Erro ao acessar URL {url}: {str(e)}")
            
            # Se chegou aqui, não conseguiu coletar jogos de nenhuma URL
            logger.warning("Não foi possível coletar jogos do FlashScore de nenhuma URL")
            return []
            
        except Exception as e:
            logger.error(f"Erro ao coletar jogos do FlashScore: {str(e)}")
            return []

    def _extrair_jogos_flashscore(self, soup: BeautifulSoup, data: str) -> List[Dict[str, Any]]:
        """
        Extrai jogos do HTML do FlashScore usando diferentes seletores.

        Args:
            soup: Objeto BeautifulSoup com o HTML da página.
            data: Data no formato DD/MM/YYYY.

        Returns:
            Lista de dicionários com informações dos jogos.
        """
        jogos = []
        
        # Lista de possíveis seletores para jogos
        seletores_jogos = [
            '.event__match',                  # Seletor antigo
            '.sportName.soccer',              # Novo seletor possível
            '.event__game',                   # Outro seletor possível
            '.event__match--scheduled',       # Jogos agendados
            '.event__match--live',            # Jogos ao vivo
            'div[class*="event"][class*="match"]',  # Seletor genérico
            'div[class*="match"]',            # Seletor mais genérico
            'div[class*="event"]'             # Seletor ainda mais genérico
        ]
        
        # Tentar cada seletor
        for seletor in seletores_jogos:
            elementos_jogo = soup.select(seletor)
            logger.info(f"Seletor '{seletor}' encontrou {len(elementos_jogo)} elementos")
            
            if not elementos_jogo:
                continue
            
            # Tentar extrair informações de cada elemento
            for elemento in elementos_jogo:
                try:
                    # Tentar diferentes seletores para times
                    time_casa = None
                    time_visitante = None
                    hora = None
                    campeonato = None
                    
                    # Seletores para time da casa
                    for seletor_casa in ['.event__participant--home', '.teamName--home', '[class*="home"]', '.event__participant.event__participant--home']:
                        elem = elemento.select_one(seletor_casa)
                        if elem and elem.text.strip():
                            time_casa = elem.text.strip()
                            break
                    
                    # Seletores para time visitante
                    for seletor_visitante in ['.event__participant--away', '.teamName--away', '[class*="away"]', '.event__participant.event__participant--away']:
                        elem = elemento.select_one(seletor_visitante)
                        if elem and elem.text.strip():
                            time_visitante = elem.text.strip()
                            break
                    
                    # Seletores para hora
                    for seletor_hora in ['.event__time', '.matchTime', '[class*="time"]', '.event__time.event__time--scheduled']:
                        elem = elemento.select_one(seletor_hora)
                        if elem and elem.text.strip():
                            hora = elem.text.strip()
                            break
                    
                    # Seletores para campeonato
                    for seletor_campeonato in ['.event__title', '.tournament', '[class*="league"]', '[class*="tournament"]', '.event__title--type']:
                        elem = elemento.select_one(seletor_campeonato)
                        if elem and elem.text.strip():
                            campeonato = elem.text.strip()
                            break
                        
                        # Se não encontrou no elemento, procurar nos elementos anteriores
                        parent = elemento.parent
                        while parent and not campeonato:
                            elem = parent.select_one(seletor_campeonato)
                            if elem and elem.text.strip():
                                campeonato = elem.text.strip()
                                break
                            parent = parent.parent
                    
                    # Se não encontrou campeonato, usar um valor padrão
                    if not campeonato:
                        campeonato = "Futebol"
                    
                    # Verificar se encontrou as informações necessárias
                    if time_casa and time_visitante and hora:
                        # Criar ID único para o jogo
                        id_jogo = self._gerar_id_jogo(time_casa, time_visitante, data, hora)
                        
                        # Adicionar jogo à lista
                        jogo = {
                            "id_jogo": id_jogo,
                            "time_casa": time_casa,
                            "time_visitante": time_visitante,
                            "data": data,
                            "hora": hora,
                            "campeonato": campeonato,
                            "fonte": "FlashScore"
                        }
                        jogos.append(jogo)
                        logger.debug(f"Jogo extraído: {time_casa} vs {time_visitante}")
                
                except Exception as e:
                    logger.error(f"Erro ao extrair informações do jogo: {str(e)}")
            
            # Se encontrou jogos com este seletor, não precisa tentar os outros
            if jogos:
                break
        
        # Se não encontrou jogos com os seletores específicos, tentar uma abordagem mais genérica
        if not jogos:
            logger.info("Tentando abordagem genérica para extrair jogos")
            
            # Procurar por padrões de texto que possam indicar jogos
            # Por exemplo, textos que contenham "vs", "x", "-" entre nomes de times
            for tag in soup.find_all(['div', 'span', 'a']):
                texto = tag.get_text().strip()
                
                # Padrões comuns para jogos: "Time A vs Time B", "Time A x Time B", "Time A - Time B"
                for separador in [' vs ', ' x ', ' - ']:
                    if separador in texto:
                        partes = texto.split(separador)
                        if len(partes) == 2:
                            time_casa = partes[0].strip()
                            time_visitante = partes[1].strip()
                            
                            # Verificar se os nomes dos times parecem válidos (pelo menos 3 caracteres)
                            if len(time_casa) >= 3 and len(time_visitante) >= 3:
                                # Tentar encontrar a hora próxima a este elemento
                                hora = None
                                for elem in tag.find_all_next(['div', 'span'], limit=5):
                                    if ':' in elem.text:
                                        hora_candidata = elem.text.strip()
                                        # Verificar se parece uma hora (HH:MM)
                                        if re.match(r'\d{1,2}:\d{2}', hora_candidata):
                                            hora = hora_candidata
                                            break
                                
                                # Se não encontrou hora, usar um valor padrão
                                if not hora:
                                    hora = "00:00"
                                
                                # Criar ID único para o jogo
                                id_jogo = self._gerar_id_jogo(time_casa, time_visitante, data, hora)
                                
                                # Adicionar jogo à lista
                                jogo = {
                                    "id_jogo": id_jogo,
                                    "time_casa": time_casa,
                                    "time_visitante": time_visitante,
                                    "data": data,
                                    "hora": hora,
                                    "campeonato": "Futebol",
                                    "fonte": "FlashScore (extração genérica)"
                                }
                                jogos.append(jogo)
                                logger.debug(f"Jogo extraído (genérico): {time_casa} vs {time_visitante}")
        
        logger.info(f"Total de jogos extraídos do FlashScore: {len(jogos)}")
        return jogos

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
            # URLs alternativas para tentar
            urls = [
                f"https://www.academiadasapostasbrasil.com/futebol/jogos-do-dia/{data.replace('/', '-')}",
                f"https://www.academiadasapostasbrasil.com/futebol/jogos/{data.replace('/', '-')}",
                f"https://www.academiadasapostas.com/futebol/jogos-do-dia/{data.replace('/', '-')}"
            ]
            
            # Cabeçalhos específicos
            headers_academia = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Referer': 'https://www.google.com/',
                'Cache-Control': 'max-age=0',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Tentar cada URL
            for url in urls:
                try:
                    logger.info(f"Tentando acessar URL: {url}")
                    response = requests.get(url, headers=headers_academia, timeout=15)
                    
                    # Salvar HTML para debug
                    data_formatada = data.replace('/', '')
                    debug_file = os.path.join(self.diretorio_debug, f"academia_{data_formatada}_{urls.index(url)}.html")
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    logger.info(f"HTML salvo para debug em {debug_file}")
                    
                    if response.status_code != 200:
                        logger.warning(f"Falha ao acessar Academia das Apostas URL {url}: {response.status_code}")
                        continue
                    
                    # Parsear HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extrair jogos
                    jogos = []
                    
                    # Tentar diferentes seletores para encontrar jogos
                    seletores = [
                        '.event-row',
                        '.match-row',
                        '.game-row',
                        'div[class*="event"]',
                        'div[class*="match"]',
                        'div[class*="game"]'
                    ]
                    
                    for seletor in seletores:
                        elementos_jogo = soup.select(seletor)
                        logger.info(f"Seletor '{seletor}' encontrou {len(elementos_jogo)} elementos")
                        
                        if not elementos_jogo:
                            continue
                        
                        for elemento in elementos_jogo:
                            try:
                                # Tentar diferentes seletores para times
                                time_casa = None
                                time_visitante = None
                                hora = None
                                campeonato = None
                                
                                # Seletores para time da casa
                                for seletor_casa in ['.team-home', '.home-team', '[class*="home"]', '[class*="team-1"]']:
                                    elem = elemento.select_one(seletor_casa)
                                    if elem and elem.text.strip():
                                        time_casa = elem.text.strip()
                                        break
                                
                                # Seletores para time visitante
                                for seletor_visitante in ['.team-away', '.away-team', '[class*="away"]', '[class*="team-2"]']:
                                    elem = elemento.select_one(seletor_visitante)
                                    if elem and elem.text.strip():
                                        time_visitante = elem.text.strip()
                                        break
                                
                                # Seletores para hora
                                for seletor_hora in ['.event-time', '.match-time', '.time', '[class*="time"]', '[class*="hour"]']:
                                    elem = elemento.select_one(seletor_hora)
                                    if elem and elem.text.strip():
                                        hora = elem.text.strip()
                                        break
                                
                                # Seletores para campeonato
                                for seletor_campeonato in ['.league-name', '.tournament', '.competition', '[class*="league"]', '[class*="tournament"]']:
                                    elem = elemento.select_one(seletor_campeonato)
                                    if elem and elem.text.strip():
                                        campeonato = elem.text.strip()
                                        break
                                    
                                    # Se não encontrou no elemento, procurar nos elementos anteriores
                                    parent = elemento.parent
                                    while parent and not campeonato:
                                        elem = parent.select_one(seletor_campeonato)
                                        if elem and elem.text.strip():
                                            campeonato = elem.text.strip()
                                            break
                                        parent = parent.parent
                                
                                # Se não encontrou campeonato, usar um valor padrão
                                if not campeonato:
                                    campeonato = "Futebol"
                                
                                # Verificar se encontrou as informações necessárias
                                if time_casa and time_visitante:
                                    # Se não encontrou hora, usar um valor padrão
                                    if not hora:
                                        hora = "00:00"
                                    
                                    # Criar ID único para o jogo
                                    id_jogo = self._gerar_id_jogo(time_casa, time_visitante, data, hora)
                                    
                                    # Adicionar jogo à lista
                                    jogo = {
                                        "id_jogo": id_jogo,
                                        "time_casa": time_casa,
                                        "time_visitante": time_visitante,
                                        "data": data,
                                        "hora": hora,
                                        "campeonato": campeonato,
                                        "fonte": "Academia das Apostas"
                                    }
                                    jogos.append(jogo)
                                    logger.debug(f"Jogo extraído: {time_casa} vs {time_visitante}")
                            
                            except Exception as e:
                                logger.error(f"Erro ao extrair informações do jogo: {str(e)}")
                        
                        # Se encontrou jogos com este seletor, não precisa tentar os outros
                        if jogos:
                            break
                    
                    if jogos:
                        logger.info(f"Coletados {len(jogos)} jogos da Academia das Apostas via URL {url}")
                        return jogos
                
                except Exception as e:
                    logger.error(f"Erro ao acessar URL {url}: {str(e)}")
            
            # Se chegou aqui, não conseguiu coletar jogos de nenhuma URL
            logger.warning("Não foi possível coletar jogos da Academia das Apostas de nenhuma URL")
            return []
            
        except Exception as e:
            logger.error(f"Erro ao coletar jogos da Academia das Apostas: {str(e)}")
            return []

    def _coletar_jogos_fonte_alternativa(self, data: str) -> List[Dict[str, Any]]:
        """
        Coleta jogos de fontes alternativas.

        Args:
            data: Data no formato DD/MM/YYYY.

        Returns:
            Lista de dicionários com informações dos jogos.
        """
        logger.info(f"Tentando coletar jogos de fontes alternativas para a data: {data}")
        try:
            # Tentar coletar de outras fontes como SofaScore, ESPN, etc.
            # Implementação para SofaScore como exemplo
            url = f"https://www.sofascore.com/football/{data.replace('/', '-')}"
            
            headers_sofascore = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Referer': 'https://www.google.com/',
                'Host': 'www.sofascore.com'
            }
            
            try:
                logger.info(f"Tentando acessar SofaScore: {url}")
                response = requests.get(url, headers=headers_sofascore, timeout=15)
                
                # Salvar HTML para debug
                data_formatada = data.replace('/', '')
                debug_file = os.path.join(self.diretorio_debug, f"sofascore_{data_formatada}.html")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.info(f"HTML salvo para debug em {debug_file}")
                
                if response.status_code != 200:
                    logger.warning(f"Falha ao acessar SofaScore: {response.status_code}")
                    return []
                
                # Parsear HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extrair jogos (implementação simplificada)
                jogos = []
                elementos_jogo = soup.select('.sc-fqkvVR')
                
                for elemento in elementos_jogo:
                    try:
                        # Extrair times
                        times = elemento.select('.sc-dcJsrY')
                        if len(times) >= 2:
                            time_casa = times[0].text.strip()
                            time_visitante = times[1].text.strip()
                            
                            # Extrair hora
                            hora_elem = elemento.select_one('.sc-kAyceB')
                            hora = hora_elem.text.strip() if hora_elem else "00:00"
                            
                            # Extrair campeonato
                            campeonato_elem = elemento.select_one('.sc-gFqAkR')
                            campeonato = campeonato_elem.text.strip() if campeonato_elem else "Futebol"
                            
                            # Criar ID único para o jogo
                            id_jogo = self._gerar_id_jogo(time_casa, time_visitante, data, hora)
                            
                            # Adicionar jogo à lista
                            jogo = {
                                "id_jogo": id_jogo,
                                "time_casa": time_casa,
                                "time_visitante": time_visitante,
                                "data": data,
                                "hora": hora,
                                "campeonato": campeonato,
                                "fonte": "SofaScore"
                            }
                            jogos.append(jogo)
                    
                    except Exception as e:
                        logger.error(f"Erro ao extrair informações do jogo do SofaScore: {str(e)}")
                
                logger.info(f"Coletados {len(jogos)} jogos do SofaScore")
                return jogos
                
            except Exception as e:
                logger.error(f"Erro ao acessar SofaScore: {str(e)}")
            
            # Implementar outras fontes alternativas aqui
            
            return []
            
        except Exception as e:
            logger.error(f"Erro ao coletar jogos de fontes alternativas: {str(e)}")
            return []

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
        # Normalizar nomes dos times (remover acentos, espaços, etc.)
        time_casa_norm = self._normalizar_nome(time_casa)
        time_visitante_norm = self._normalizar_nome(time_visitante)

        # Gerar hash para o jogo
        import hashlib
        jogo_str = f"{time_casa_norm}_{time_visitante_norm}_{data}_{hora}"
        hash_obj = hashlib.md5(jogo_str.encode())
        hash_hex = hash_obj.hexdigest()[:8]

        # Retornar ID no formato time_casa_time_visitante_hash
        return f"{time_casa_norm}_{time_visitante_norm}_{hash_hex}"

    def _normalizar_nome(self, nome: str) -> str:
        """
        Normaliza o nome do time para uso em IDs.

        Args:
            nome: Nome do time.

        Returns:
            Nome normalizado.
        """
        import unicodedata
        import re

        # Remover acentos
        nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
        # Converter para minúsculas
        nome = nome.lower()
        # Remover caracteres especiais
        nome = re.sub(r'[^a-z0-9]', '', nome)

        return nome

    def _salvar_jogos(self, jogos: List[Dict[str, Any]]) -> None:
        """
        Salva os jogos em arquivos JSON.

        Args:
            jogos: Lista de dicionários com informações dos jogos.
        """
        for jogo in jogos:
            try:
                # Caminho do arquivo
                arquivo = os.path.join(self.diretorio_jogos, f"{jogo['id_jogo']}.json")
                
                # Salvar jogo
                with open(arquivo, 'w', encoding='utf-8') as f:
                    json.dump(jogo, f, ensure_ascii=False, indent=4)
                
                logger.info(f"Jogo salvo com sucesso em {arquivo}")
            except Exception as e:
                logger.error(f"Erro ao salvar jogo {jogo.get('id_jogo', 'desconhecido')}: {str(e)}")

    def coletar_estatisticas_jogos(self, jogos: List[Dict[str, Any]]) -> None:
        """
        Coleta estatísticas para os jogos.

        Args:
            jogos: Lista de dicionários com informações dos jogos.
        """
        for jogo in jogos:
            try:
                # Verificar se já temos estatísticas para este jogo
                arquivo_estatisticas = os.path.join(self.diretorio_estatisticas, f"{jogo['id_jogo']}.json")
                if os.path.exists(arquivo_estatisticas):
                    logger.info(f"Estatísticas já existem para o jogo {jogo['id_jogo']}")
                    continue

                # Tentar coletar estatísticas de diferentes fontes
                estatisticas = None
                
                # Tentar coletar estatísticas do FlashScore
                estatisticas = self._coletar_estatisticas_flashscore(jogo)
                if estatisticas:
                    # Salvar estatísticas
                    with open(arquivo_estatisticas, 'w', encoding='utf-8') as f:
                        json.dump(estatisticas, f, ensure_ascii=False, indent=4)
                    
                    logger.info(f"Estatísticas salvas com sucesso em {arquivo_estatisticas}")
                    continue
                
                # Se não conseguir, tentar coletar estatísticas da Academia das Apostas
                estatisticas = self._coletar_estatisticas_academia_apostas(jogo)
                if estatisticas:
                    # Salvar estatísticas
                    with open(arquivo_estatisticas, 'w', encoding='utf-8') as f:
                        json.dump(estatisticas, f, ensure_ascii=False, indent=4)
                    
                    logger.info(f"Estatísticas salvas com sucesso em {arquivo_estatisticas}")
                    continue
                
                # Se não conseguir de nenhuma fonte, registrar falha
                logger.warning(f"Não foi possível coletar estatísticas para o jogo {jogo['id_jogo']}")
                
            except Exception as e:
                logger.error(f"Erro ao coletar estatísticas para o jogo {jogo.get('id_jogo', 'desconhecido')}: {str(e)}")

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
            # Construir URL de busca
            time_casa = jogo['time_casa']
            time_visitante = jogo['time_visitante']
            query = f"{time_casa} {time_visitante}"
            url = f"https://www.flashscore.com.br/pesquisa/?q={query.replace(' ', '+')}"

            # Fazer requisição HTTP com cabeçalhos atualizados
            headers_flashscore = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Referer': 'https://www.flashscore.com.br/',
                'Host': 'www.flashscore.com.br',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            
            response = requests.get(url, headers=headers_flashscore, timeout=15)
            
            # Salvar HTML para debug
            debug_file = os.path.join(self.diretorio_debug, f"flashscore_stats_search_{jogo['id_jogo']}.html")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"HTML de busca salvo para debug em {debug_file}")
            
            if response.status_code != 200:
                logger.warning(f"Falha ao acessar FlashScore: {response.status_code}")
                return None

            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Encontrar link para a página do jogo
            links = soup.select('.event__match, [class*="event"], [class*="match"]')
            if not links:
                logger.warning(f"Nenhum resultado encontrado para {query}")
                return None

            # Pegar o primeiro link que parece ser um jogo
            link_jogo = None
            for link in links:
                texto_link = link.text.lower()
                if time_casa.lower() in texto_link and time_visitante.lower() in texto_link:
                    link_jogo = link
                    break

            if not link_jogo:
                logger.warning(f"Nenhum jogo encontrado para {query}")
                return None

            # Extrair ID do jogo do FlashScore
            id_flashscore = None
            for attr in ['id', 'data-id', 'data-event-id']:
                if link_jogo.has_attr(attr):
                    id_flashscore = link_jogo[attr]
                    break
            
            # Se não encontrou pelo atributo, tentar extrair da URL
            if not id_flashscore and link_jogo.has_attr('href'):
                href = link_jogo['href']
                # Extrair ID da URL (formato típico: /jogo/ABCDEF/)
                import re
                match = re.search(r'/jogo/([^/]+)', href)
                if match:
                    id_flashscore = match.group(1)

            if not id_flashscore:
                logger.warning(f"Não foi possível extrair ID do jogo do FlashScore")
                return None

            # Acessar página de estatísticas do jogo
            url_estatisticas = f"https://www.flashscore.com.br/jogo/{id_flashscore}/#/estatisticas-de-jogo/estatisticas-de-jogo"
            
            response = requests.get(url_estatisticas, headers=headers_flashscore, timeout=15)
            
            # Salvar HTML para debug
            debug_file = os.path.join(self.diretorio_debug, f"flashscore_stats_{jogo['id_jogo']}.html")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"HTML de estatísticas salvo para debug em {debug_file}")
            
            if response.status_code != 200:
                logger.warning(f"Falha ao acessar página de estatísticas: {response.status_code}")
                return None

            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extrair estatísticas
            estatisticas = {
                "id_jogo": jogo['id_jogo'],
                "time_casa": jogo['time_casa'],
                "time_visitante": jogo['time_visitante'],
                "data": jogo['data'],
                "estatisticas": {},
                "fonte": "FlashScore"
            }

            # Extrair categorias de estatísticas
            categorias = soup.select('.statCategory, [class*="statistic"], [class*="stat"]')
            
            for categoria in categorias:
                try:
                    titulo_elem = categoria.select_one('.statCategoryName, [class*="categoryName"], [class*="title"]')
                    titulo = titulo_elem.text.strip() if titulo_elem else "Estatísticas Gerais"
                    
                    estatisticas_categoria = {}

                    # Extrair linhas de estatísticas
                    linhas = categoria.select('.statRow, [class*="statRow"], [class*="row"]')
                    for linha in linhas:
                        try:
                            nome_elem = linha.select_one('.statName, [class*="statName"], [class*="name"]')
                            nome = nome_elem.text.strip() if nome_elem else "Desconhecido"
                            
                            valor_casa_elem = linha.select_one('.statHome, [class*="home"]')
                            valor_casa = valor_casa_elem.text.strip() if valor_casa_elem else "0"
                            
                            valor_visitante_elem = linha.select_one('.statAway, [class*="away"]')
                            valor_visitante = valor_visitante_elem.text.strip() if valor_visitante_elem else "0"
                            
                            estatisticas_categoria[nome] = {
                                "casa": valor_casa,
                                "visitante": valor_visitante
                            }
                        except Exception as e:
                            logger.error(f"Erro ao extrair linha de estatística: {str(e)}")

                    estatisticas["estatisticas"][titulo] = estatisticas_categoria
                except Exception as e:
                    logger.error(f"Erro ao extrair categoria de estatísticas: {str(e)}")

            # Se não encontrou estatísticas, tentar outra abordagem
            if not estatisticas["estatisticas"]:
                logger.warning(f"Não foi possível extrair estatísticas usando os seletores padrão")
                return None

            return estatisticas
        except Exception as e:
            logger.error(f"Erro ao coletar estatísticas do FlashScore: {str(e)}")
            return None

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
            # Construir URL de busca
            time_casa = jogo['time_casa']
            time_visitante = jogo['time_visitante']
            query = f"{time_casa} {time_visitante}"
            url = f"https://www.academiadasapostasbrasil.com/stats/search?q={query.replace(' ', '+')}"

            # Fazer requisição HTTP
            headers_academia = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Referer': 'https://www.academiadasapostasbrasil.com/',
                'Cache-Control': 'max-age=0',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers_academia, timeout=15)
            
            # Salvar HTML para debug
            debug_file = os.path.join(self.diretorio_debug, f"academia_stats_search_{jogo['id_jogo']}.html")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"HTML de busca salvo para debug em {debug_file}")
            
            if response.status_code != 200:
                logger.warning(f"Falha ao acessar Academia das Apostas: {response.status_code}")
                return None

            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Encontrar link para a página de estatísticas
            links = soup.select('.search-results a, [class*="search"] a')
            if not links:
                logger.warning(f"Nenhum resultado encontrado para {query}")
                return None

            # Pegar o primeiro link
            link = links[0]['href']
            url_estatisticas = f"https://www.academiadasapostasbrasil.com{link}"

            # Acessar página de estatísticas
            response = requests.get(url_estatisticas, headers=headers_academia, timeout=15)
            
            # Salvar HTML para debug
            debug_file = os.path.join(self.diretorio_debug, f"academia_stats_{jogo['id_jogo']}.html")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"HTML de estatísticas salvo para debug em {debug_file}")
            
            if response.status_code != 200:
                logger.warning(f"Falha ao acessar página de estatísticas: {response.status_code}")
                return None

            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extrair estatísticas
            estatisticas = {
                "id_jogo": jogo['id_jogo'],
                "time_casa": jogo['time_casa'],
                "time_visitante": jogo['time_visitante'],
                "data": jogo['data'],
                "estatisticas": {},
                "fonte": "Academia das Apostas"
            }

            # Extrair blocos de estatísticas
            blocos = soup.select('.stats-block, [class*="stats"]')
            for bloco in blocos:
                try:
                    titulo_elem = bloco.select_one('.stats-block-title, [class*="title"]')
                    titulo = titulo_elem.text.strip() if titulo_elem else "Estatísticas Gerais"
                    estatisticas_bloco = {}

                    # Extrair linhas de estatísticas
                    linhas = bloco.select('.stats-row, [class*="row"]')
                    for linha in linhas:
                        try:
                            nome_elem = linha.select_one('.stats-label, [class*="label"]')
                            nome = nome_elem.text.strip() if nome_elem else "Desconhecido"
                            
                            valores = linha.select('.stats-value, [class*="value"]')
                            
                            if len(valores) >= 2:
                                valor_casa = valores[0].text.strip()
                                valor_visitante = valores[1].text.strip()
                                
                                estatisticas_bloco[nome] = {
                                    "casa": valor_casa,
                                    "visitante": valor_visitante
                                }
                        except Exception as e:
                            logger.error(f"Erro ao extrair linha de estatística: {str(e)}")

                    estatisticas["estatisticas"][titulo] = estatisticas_bloco
                except Exception as e:
                    logger.error(f"Erro ao extrair bloco de estatísticas: {str(e)}")

            # Se não encontrou estatísticas, registrar falha
            if not estatisticas["estatisticas"]:
                logger.warning(f"Não foi possível extrair estatísticas da Academia das Apostas")
                return None

            return estatisticas
        except Exception as e:
            logger.error(f"Erro ao coletar estatísticas da Academia das Apostas: {str(e)}")
            return None

# Função para executar o coletor
def executar_coleta(diretorio_dados=None, data=None, dias_futuros=0):
    """
    Executa a coleta de dados.

    Args:
        diretorio_dados: Diretório para salvar os dados.
        data: Data no formato DD/MM/YYYY.
        dias_futuros: Número de dias futuros para coletar jogos.
    """
    try:
        coletor = ColetorDadosReais(diretorio_dados)
        jogos = coletor.coletar_jogos_do_dia(data, dias_futuros)
        return jogos
    except Exception as e:
        logger.error(f"Erro ao coletar jogos reais: {str(e)}")
        raise

if __name__ == "__main__":
    import sys
    import re
    
    # Parâmetros da linha de comando
    diretorio_dados = None
    data = None
    dias_futuros = 0
    
    # Processar argumentos
    if len(sys.argv) > 1:
        diretorio_dados = sys.argv[1]
    if len(sys.argv) > 2:
        data = sys.argv[2]
    if len(sys.argv) > 3:
        try:
            dias_futuros = int(sys.argv[3])
        except ValueError:
            print(f"Erro: dias_futuros deve ser um número inteiro. Usando 0.")
    
    # Executar coleta
    try:
        jogos = executar_coleta(diretorio_dados, data, dias_futuros)
        print(f"Coletados {len(jogos)} jogos com sucesso.")
    except Exception as e:
        print(f"Erro ao coletar jogos reais: {str(e)}")
        sys.exit(1)
