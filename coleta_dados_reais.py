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
            # Corrigindo o formato da URL para o FlashScore
            data_formatada = data.replace('/', '')
            url = f"https://www.flashscore.com.br/futebol/?d={data_formatada}"

            # Fazer requisição HTTP com cabeçalhos atualizados
            headers_flashscore = self.headers.copy()
            headers_flashscore['Host'] = 'www.flashscore.com.br'
            headers_flashscore['Referer'] = 'https://www.flashscore.com.br/'
            
            response = requests.get(url, headers=headers_flashscore, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Falha ao acessar FlashScore: {response.status_code}")
                return []

            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extrair jogos
            jogos = []
            
            # Atualizar seletores para corresponder à estrutura atual do FlashScore
            # Encontrar elementos de jogo (ajustando seletores conforme necessário)
            elementos_jogo = soup.select('.event__match, .sportName, .soccer')
            
            if not elementos_jogo:
                logger.warning("Nenhum elemento de jogo encontrado no FlashScore. Verificando estrutura HTML.")
                # Salvar HTML para debug
                debug_path = os.path.join(self.diretorio_dados, 'debug')
                os.makedirs(debug_path, exist_ok=True)
                with open(os.path.join(debug_path, f'flashscore_html_{data_formatada}.html'), 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                # Tentar encontrar qualquer tabela ou estrutura de jogo
                elementos_jogo = soup.select('div[class*="event"], div[class*="match"]')
            
            for elemento in elementos_jogo:
                try:
                    # Tentar diferentes seletores para extrair informações
                    # Para times
                    time_casa_elem = elemento.select_one('.event__participant--home, .teamName--home, [class*="home"]')
                    time_visitante_elem = elemento.select_one('.event__participant--away, .teamName--away, [class*="away"]')
                    
                    # Para hora
                    hora_elem = elemento.select_one('.event__time, .matchTime, [class*="time"]')
                    
                    # Para campeonato
                    campeonato_elem = elemento.select_one('.event__title, .tournament, [class*="league"], [class*="tournament"]')
                    
                    # Verificar se encontrou os elementos necessários
                    if not (time_casa_elem and time_visitante_elem and hora_elem):
                        continue
                    
                    time_casa = time_casa_elem.text.strip()
                    time_visitante = time_visitante_elem.text.strip()
                    hora = hora_elem.text.strip()
                    campeonato = campeonato_elem.text.strip() if campeonato_elem else "Não especificado"

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

                # Tentar coletar estatísticas da Academia das Apostas
                estatisticas = self._coletar_estatisticas_academia_apostas(jogo)
                if estatisticas:
                    # Salvar estatísticas
                    with open(arquivo_estatisticas, 'w', encoding='utf-8') as f:
                        json.dump(estatisticas, f, ensure_ascii=False, indent=4)
                    
                    logger.info(f"Estatísticas salvas com sucesso em {arquivo_estatisticas}")
                    continue

                # Se não conseguir, tentar coletar estatísticas do FlashScore
                estatisticas = self._coletar_estatisticas_flashscore(jogo)
                if estatisticas:
                    # Salvar estatísticas
                    with open(arquivo_estatisticas, 'w', encoding='utf-8') as f:
                        json.dump(estatisticas, f, ensure_ascii=False, indent=4)
                    
                    logger.info(f"Estatísticas salvas com sucesso em {arquivo_estatisticas}")
                    continue

                logger.warning(f"Não foi possível coletar estatísticas para o jogo {jogo['id_jogo']}")
            except Exception as e:
                logger.error(f"Erro ao coletar estatísticas para o jogo {jogo.get('id_jogo', 'desconhecido')}: {str(e)}")

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
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Falha ao acessar Academia das Apostas: {response.status_code}")
                return None

            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Encontrar link para a página de estatísticas
            links = soup.select('.search-results a')
            if not links:
                logger.warning(f"Nenhum resultado encontrado para {query}")
                return None

            # Pegar o primeiro link
            link = links[0]['href']
            url_estatisticas = f"https://www.academiadasapostasbrasil.com{link}"

            # Acessar página de estatísticas
            response = requests.get(url_estatisticas, headers=self.headers, timeout=10)
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
                "estatisticas": {}
            }

            # Extrair blocos de estatísticas
            blocos = soup.select('.stats-block')
            for bloco in blocos:
                try:
                    titulo = bloco.select_one('.stats-block-title').text.strip()
                    estatisticas_bloco = {}

                    # Extrair linhas de estatísticas
                    linhas = bloco.select('.stats-row')
                    for linha in linhas:
                        try:
                            nome = linha.select_one('.stats-label').text.strip()
                            valores = linha.select('.stats-value')
                            
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

            return estatisticas
        except Exception as e:
            logger.error(f"Erro ao coletar estatísticas da Academia das Apostas: {str(e)}")
            return None

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
            headers_flashscore = self.headers.copy()
            headers_flashscore['Host'] = 'www.flashscore.com.br'
            headers_flashscore['Referer'] = 'https://www.flashscore.com.br/'
            
            response = requests.get(url, headers=headers_flashscore, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Falha ao acessar FlashScore: {response.status_code}")
                return None

            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Encontrar link para a página do jogo
            links = soup.select('.event__match')
            if not links:
                # Tentar seletores alternativos
                links = soup.select('[class*="event"], [class*="match"]')
                if not links:
                    logger.warning(f"Nenhum resultado encontrado para {query}")
                    return None

            # Pegar o primeiro link que parece ser um jogo
            link_jogo = None
            for link in links:
                if time_casa.lower() in link.text.lower() and time_visitante.lower() in link.text.lower():
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

            if not id_flashscore:
                logger.warning(f"Não foi possível extrair ID do jogo do FlashScore")
                return None

            # Acessar página de estatísticas do jogo
            url_estatisticas = f"https://www.flashscore.com.br/jogo/{id_flashscore}/#/estatisticas-de-jogo/estatisticas-de-jogo"
            
            response = requests.get(url_estatisticas, headers=headers_flashscore, timeout=15)
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
                "estatisticas": {}
            }

            # Extrair categorias de estatísticas
            categorias = soup.select('.statCategory')
            if not categorias:
                # Tentar seletores alternativos
                categorias = soup.select('[class*="statistic"], [class*="stat"]')
                
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
                # Salvar HTML para debug
                debug_path = os.path.join(self.diretorio_dados, 'debug')
                os.makedirs(debug_path, exist_ok=True)
                with open(os.path.join(debug_path, f'flashscore_stats_{jogo["id_jogo"]}.html'), 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                logger.warning(f"Não foi possível extrair estatísticas usando os seletores padrão. HTML salvo para debug.")
                return None

            return estatisticas
        except Exception as e:
            logger.error(f"Erro ao coletar estatísticas do FlashScore: {str(e)}")
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
    coletor = ColetorDadosReais(diretorio_dados)
    jogos = coletor.coletar_jogos_do_dia(data, dias_futuros)
    return jogos

if __name__ == "__main__":
    import sys
    
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
    executar_coleta(diretorio_dados, data, dias_futuros)

        print(f"Estatísticas carregadas para o jogo {id_jogo}")
