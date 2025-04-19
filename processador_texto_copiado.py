"""
Processador para extrair dados de texto copiado do site Academia das Apostas Brasil
-------------------------------------------------------------------------------
Este módulo implementa funções para processar texto copiado do site Academia das Apostas Brasil
e extrair informações sobre jogos, estatísticas, odds e outros dados relevantes.
"""

import re
import json
import logging
import datetime
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Union

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('processador_texto_copiado')

class ProcessadorTextoCopiadoAcademiaApostas:
    """
    Classe para processar texto copiado do site Academia das Apostas Brasil.
    """
    
    def __init__(self):
        """
        Inicializa o processador de texto copiado.
        """
        self.padroes = {
            'jogo': re.compile(r'(\w+)\s+vs\s+(\w+)'),
            'data_hora': re.compile(r'(\d{1,2}/\d{1,2}/\d{4})\s+-\s+(\d{1,2}:\d{2})'),
            'campeonato': re.compile(r'Brasileirão\s+Série\s+[A-Z]|Copa\s+do\s+Brasil|Libertadores|Sul-Americana'),
            'odds': re.compile(r'Casa\s+(\d+\.\d+)\s+Empate\s+(\d+\.\d+)\s+Fora\s+(\d+\.\d+)'),
            'tabela_inicio': re.compile(r'Posição\s+Time\s+P\s+J\s+V\s+E\s+D'),
            'tabela_linha': re.compile(r'(\d+)\s+(\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)'),
            'estatisticas_inicio': re.compile(r'ESTATÍSTICAS'),
            'confrontos_diretos': re.compile(r'CONFRONTO DIRETO'),
            'ultimos_jogos': re.compile(r'ÚLTIMOS \d+ JOGOS'),
            'escanteios': re.compile(r'Escanteios'),
            'cartoes': re.compile(r'Cartões'),
        }
    
    def processar_texto(self, texto: str) -> Dict[str, Any]:
        """
        Processa texto copiado do site Academia das Apostas Brasil.
        
        Args:
            texto: Texto copiado do site
            
        Returns:
            Dicionário com dados extraídos do texto
        """
        logger.info("Processando texto copiado")
        
        # Normalizar texto
        texto = self._normalizar_texto(texto)
        
        # Identificar tipo de conteúdo
        tipo_conteudo = self._identificar_tipo_conteudo(texto)
        logger.info(f"Tipo de conteúdo identificado: {tipo_conteudo}")
        
        # Processar de acordo com o tipo de conteúdo
        if tipo_conteudo == 'jogo_especifico':
            return self._processar_jogo_especifico(texto)
        elif tipo_conteudo == 'lista_jogos':
            return self._processar_lista_jogos(texto)
        elif tipo_conteudo == 'tabela_classificacao':
            return self._processar_tabela_classificacao(texto)
        else:
            logger.warning(f"Tipo de conteúdo não reconhecido: {tipo_conteudo}")
            return {"erro": "Tipo de conteúdo não reconhecido"}
    
    def _normalizar_texto(self, texto: str) -> str:
        """
        Normaliza o texto para facilitar o processamento.
        
        Args:
            texto: Texto original
            
        Returns:
            Texto normalizado
        """
        # Remover caracteres especiais
        texto = re.sub(r'[\r\n]+', '\n', texto)
        texto = re.sub(r'\t+', ' ', texto)
        texto = re.sub(r' +', ' ', texto)
        
        # Remover espaços no início e fim de cada linha
        linhas = [linha.strip() for linha in texto.split('\n')]
        texto = '\n'.join(linhas)
        
        return texto
    
    def _identificar_tipo_conteudo(self, texto: str) -> str:
        """
        Identifica o tipo de conteúdo do texto.
        
        Args:
            texto: Texto normalizado
            
        Returns:
            Tipo de conteúdo: 'jogo_especifico', 'lista_jogos', 'tabela_classificacao' ou 'desconhecido'
        """
        # Verificar se é uma página de jogo específico
        if re.search(r'Quem será o vencedor\?', texto, re.IGNORECASE) or \
           re.search(r'CONFRONTO DIRETO', texto, re.IGNORECASE):
            return 'jogo_especifico'
        
        # Verificar se é uma lista de jogos
        if re.search(r'JOGOS DISPONÍVEIS|FUTEBOL HOJE', texto, re.IGNORECASE) and \
           len(re.findall(r'vs', texto, re.IGNORECASE)) > 3:
            return 'lista_jogos'
        
        # Verificar se é uma tabela de classificação
        if re.search(r'CLASSIFICAÇÕES?|TABELA', texto, re.IGNORECASE) and \
           re.search(self.padroes['tabela_inicio'], texto):
            return 'tabela_classificacao'
        
        # Verificar se contém pelo menos um jogo
        if re.search(self.padroes['jogo'], texto) and re.search(self.padroes['data_hora'], texto):
            # Se tiver poucas ocorrências de "vs", provavelmente é um jogo específico
            if len(re.findall(r'vs', texto, re.IGNORECASE)) <= 3:
                return 'jogo_especifico'
            else:
                return 'lista_jogos'
        
        return 'desconhecido'
    
    def _processar_jogo_especifico(self, texto: str) -> Dict[str, Any]:
        """
        Processa texto de uma página de jogo específico.
        
        Args:
            texto: Texto normalizado
            
        Returns:
            Dicionário com dados do jogo e estatísticas
        """
        logger.info("Processando página de jogo específico")
        
        resultado = {
            "jogos": [],
            "estatisticas": {}
        }
        
        # Extrair informações básicas do jogo
        jogo = self._extrair_info_jogo(texto)
        
        if jogo:
            resultado["jogos"].append(jogo)
            
            # Extrair estatísticas
            estatisticas = self._extrair_estatisticas_jogo(texto, jogo["time_casa"], jogo["time_visitante"])
            resultado["estatisticas"][jogo["id_jogo"]] = estatisticas
        
        return resultado
    
    def _processar_lista_jogos(self, texto: str) -> Dict[str, Any]:
        """
        Processa texto de uma página com lista de jogos.
        
        Args:
            texto: Texto normalizado
            
        Returns:
            Dicionário com lista de jogos
        """
        logger.info("Processando lista de jogos")
        
        resultado = {
            "jogos": [],
            "estatisticas": {}
        }
        
        # Dividir o texto em linhas
        linhas = texto.split('\n')
        
        # Procurar por padrões de jogos
        for i, linha in enumerate(linhas):
            # Verificar se a linha contém um jogo
            match_jogo = self.padroes['jogo'].search(linha)
            
            if match_jogo:
                # Extrair times
                time_casa = match_jogo.group(1).strip()
                time_visitante = match_jogo.group(2).strip()
                
                # Procurar data e hora nas linhas próximas
                data = None
                hora = None
                campeonato = None
                
                # Procurar nas 3 linhas anteriores e 3 posteriores
                for j in range(max(0, i-3), min(len(linhas), i+4)):
                    # Procurar data e hora
                    match_data_hora = self.padroes['data_hora'].search(linhas[j])
                    if match_data_hora:
                        data = match_data_hora.group(1)
                        hora = match_data_hora.group(2)
                    
                    # Procurar campeonato
                    match_campeonato = self.padroes['campeonato'].search(linhas[j])
                    if match_campeonato:
                        campeonato = match_campeonato.group(0)
                
                # Se encontrou pelo menos data ou hora, adicionar o jogo
                if data or hora:
                    # Valores padrão
                    if not data:
                        data = datetime.datetime.now().strftime('%d/%m/%Y')
                    if not hora:
                        hora = '00:00'
                    if not campeonato:
                        campeonato = 'Não especificado'
                    
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
                    
                    resultado["jogos"].append(jogo)
        
        return resultado
    
    def _processar_tabela_classificacao(self, texto: str) -> Dict[str, Any]:
        """
        Processa texto de uma página com tabela de classificação.
        
        Args:
            texto: Texto normalizado
            
        Returns:
            Dicionário com dados da tabela de classificação
        """
        logger.info("Processando tabela de classificação")
        
        resultado = {
            "tabela_classificacao": []
        }
        
        # Dividir o texto em linhas
        linhas = texto.split('\n')
        
        # Procurar pelo início da tabela
        inicio_tabela = -1
        for i, linha in enumerate(linhas):
            if self.padroes['tabela_inicio'].search(linha):
                inicio_tabela = i
                break
        
        if inicio_tabela >= 0:
            # Processar linhas da tabela
            for i in range(inicio_tabela + 1, len(linhas)):
                match_linha = self.padroes['tabela_linha'].search(linhas[i])
                
                if match_linha:
                    posicao = int(match_linha.group(1))
                    time = match_linha.group(2)
                    pontos = int(match_linha.group(3))
                    jogos = int(match_linha.group(4))
                    vitorias = int(match_linha.group(5))
                    empates = int(match_linha.group(6))
                    derrotas = int(match_linha.group(7))
                    
                    # Adicionar time à tabela
                    time_info = {
                        "posicao": posicao,
                        "time": time,
                        "pontos": pontos,
                        "jogos": jogos,
                        "vitorias": vitorias,
                        "empates": empates,
                        "derrotas": derrotas
                    }
                    
                    resultado["tabela_classificacao"].append(time_info)
        
        return resultado
    
    def _extrair_info_jogo(self, texto: str) -> Optional[Dict[str, Any]]:
        """
        Extrai informações básicas de um jogo.
        
        Args:
            texto: Texto normalizado
            
        Returns:
            Dicionário com informações do jogo, ou None se não encontrado
        """
        # Extrair times
        match_jogo = self.padroes['jogo'].search(texto)
        if not match_jogo:
            return None
        
        time_casa = match_jogo.group(1).strip()
        time_visitante = match_jogo.group(2).strip()
        
        # Extrair data e hora
        match_data_hora = self.padroes['data_hora'].search(texto)
        data = match_data_hora.group(1) if match_data_hora else datetime.datetime.now().strftime('%d/%m/%Y')
        hora = match_data_hora.group(2) if match_data_hora else '00:00'
        
        # Extrair campeonato
        match_campeonato = self.padroes['campeonato'].search(texto)
        campeonato = match_campeonato.group(0) if match_campeonato else 'Não especificado'
        
        # Criar ID único para o jogo
        id_jogo = self._gerar_id_jogo(time_casa, time_visitante, data, hora)
        
        return {
            "id_jogo": id_jogo,
            "time_casa": time_casa,
            "time_visitante": time_visitante,
            "data": data,
            "hora": hora,
            "campeonato": campeonato
        }
    
    def _extrair_estatisticas_jogo(self, texto: str, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai estatísticas de um jogo.
        
        Args:
            texto: Texto normalizado
            time_casa: Nome do time da casa
            time_visitante: Nome do time visitante
            
        Returns:
            Dicionário com estatísticas do jogo
        """
        estatisticas = {
            "time_casa": self._extrair_estatisticas_time(texto, time_casa),
            "time_visitante": self._extrair_estatisticas_time(texto, time_visitante),
            "confrontos_diretos": self._extrair_confrontos_diretos(texto, time_casa, time_visitante),
            "odds": self._extrair_odds(texto),
            "mercados_adicionais": {
                "escanteios": self._extrair_estatisticas_escanteios(texto, time_casa, time_visitante),
                "cartoes": self._extrair_estatisticas_cartoes(texto, time_casa, time_visitante)
            }
        }
        
        return estatisticas
    
    def _extrair_estatisticas_time(self, texto: str, time: str) -> Dict[str, Any]:
        """
        Extrai estatísticas de um time.
        
        Args:
            texto: Texto normalizado
            time: Nome do time
            
        Returns:
            Dicionário com estatísticas do time
        """
        # Padrões para extrair estatísticas do time
        padrao_posicao = re.compile(rf'{time}.*?Posição.*?(\d+)', re.IGNORECASE | re.DOTALL)
        padrao_pontos = re.compile(rf'{time}.*?Pontos.*?(\d+)', re.IGNORECASE | re.DOTALL)
        padrao_vitorias = re.compile(rf'{time}.*?Vitórias.*?(\d+)', re.IGNORECASE | re.DOTALL)
        padrao_empates = re.compile(rf'{time}.*?Empates.*?(\d+)', re.IGNORECASE | re.DOTALL)
        padrao_derrotas = re.compile(rf'{time}.*?Derrotas.*?(\d+)', re.IGNORECASE | re.DOTALL)
        padrao_gols_marcados = re.compile(rf'{time}.*?Gols Marcados.*?(\d+)', re.IGNORECASE | re.DOTALL)
        padrao_gols_sofridos = re.compile(rf'{time}.*?Gols Sofridos.*?(\d+)', re.IGNORECASE | re.DOTALL)
        
        # Extrair valores
        posicao = self._extrair_valor_numerico(texto, padrao_posicao, 0)
        pontos = self._extrair_valor_numerico(texto, padrao_pontos, 0)
        vitorias = self._extrair_valor_numerico(texto, padrao_vitorias, 0)
        empates = self._extrair_valor_numerico(texto, padrao_empates, 0)
        derrotas = self._extrair_valor_numerico(texto, padrao_derrotas, 0)
        gols_marcados = self._extrair_valor_numerico(texto, padrao_gols_marcados, 0)
        gols_sofridos = self._extrair_valor_numerico(texto, padrao_gols_sofridos, 0)
        
        # Extrair últimos jogos
        ultimos_jogos = self._extrair_ultimos_jogos(texto, time)
        
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
    
    def _extrair_confrontos_diretos(self, texto: str, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai informações sobre confrontos diretos entre os times.
        
        Args:
            texto: Texto normalizado
            time_casa: Nome do time da casa
            time_visitante: Nome do time visitante
            
        Returns:
            Dicionário com informações sobre confrontos diretos
        """
        # Procurar seção de confrontos diretos
        match_confrontos = re.search(r'CONFRONTO DIRETO.*?(\d+)\s+jogo', texto, re.IGNORECASE | re.DOTALL)
        
        if not match_confrontos:
            return {
                "resumo": {
                    "total": 0,
                    "vitorias_casa": 0,
                    "empates": 0,
                    "vitorias_visitante": 0
                },
                "confrontos": []
            }
        
        # Extrair número total de jogos
        total_jogos = int(match_confrontos.group(1))
        
        # Extrair vitórias, empates e derrotas
        padrao_vitorias_casa = re.compile(rf'Vitórias\s+{time_casa}.*?(\d+)', re.IGNORECASE | re.DOTALL)
        padrao_empates = re.compile(r'Empates.*?(\d+)', re.IGNORECASE | re.DOTALL)
        padrao_vitorias_visitante = re.compile(rf'Vitórias\s+{time_visitante}.*?(\d+)', re.IGNORECASE | re.DOTALL)
        
        vitorias_casa = self._extrair_valor_numerico(texto, padrao_vitorias_casa, 0)
        empates = self._extrair_valor_numerico(texto, padrao_empates, 0)
        vitorias_visitante = self._extrair_valor_numerico(texto, padrao_vitorias_visitante, 0)
        
        # Extrair lista de confrontos
        confrontos = []
        
        # Padrão para extrair confrontos
        padrao_confronto = re.compile(r'(\d{2}/\d{2}/\d{4}).*?(\w+)\s+(\d+)-(\d+)\s+(\w+).*?([\w\s]+)', re.IGNORECASE | re.DOTALL)
        
        # Procurar todos os confrontos
        for match in padrao_confronto.finditer(texto):
            data = match.group(1)
            mandante = match.group(2)
            gols_mandante = int(match.group(3))
            gols_visitante = int(match.group(4))
            visitante = match.group(5)
            competicao = match.group(6).strip()
            
            confronto = {
                "data": data,
                "mandante": mandante,
                "visitante": visitante,
                "placar": f"{gols_mandante}-{gols_visitante}",
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
    
    def _extrair_odds(self, texto: str) -> Dict[str, Any]:
        """
        Extrai odds do jogo.
        
        Args:
            texto: Texto normalizado
            
        Returns:
            Dicionário com odds do jogo
        """
        # Extrair odds de resultado (1X2)
        match_odds = self.padroes['odds'].search(texto)
        
        if match_odds:
            casa = float(match_odds.group(1))
            empate = float(match_odds.group(2))
            visitante = float(match_odds.group(3))
        else:
            # Tentar outro padrão
            padrao_alternativo = re.compile(r'(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)')
            match_alternativo = padrao_alternativo.search(texto)
            
            if match_alternativo:
                casa = float(match_alternativo.group(1))
                empate = float(match_alternativo.group(2))
                visitante = float(match_alternativo.group(3))
            else:
                casa = 0.0
                empate = 0.0
                visitante = 0.0
        
        # Extrair odds de over/under
        padrao_over_under = re.compile(r'Over\s+(\d+\.\d+).*?Under\s+(\d+\.\d+)', re.IGNORECASE | re.DOTALL)
        match_over_under = padrao_over_under.search(texto)
        
        if match_over_under:
            over_2_5 = float(match_over_under.group(1))
            under_2_5 = float(match_over_under.group(2))
        else:
            over_2_5 = 0.0
            under_2_5 = 0.0
        
        # Extrair odds de ambas marcam
        padrao_ambos_marcam = re.compile(r'Sim\s+(\d+\.\d+).*?Não\s+(\d+\.\d+)', re.IGNORECASE | re.DOTALL)
        match_ambos_marcam = padrao_ambos_marcam.search(texto)
        
        if match_ambos_marcam:
            ambos_sim = float(match_ambos_marcam.group(1))
            ambos_nao = float(match_ambos_marcam.group(2))
        else:
            ambos_sim = 0.0
            ambos_nao = 0.0
        
        return {
            "resultado": {
                "casa": casa,
                "empate": empate,
                "visitante": visitante
            },
            "over_under": {
                "over_2_5": over_2_5,
                "under_2_5": under_2_5
            },
            "ambos_marcam": {
                "sim": ambos_sim,
                "nao": ambos_nao
            }
        }
    
    def _extrair_estatisticas_escanteios(self, texto: str, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai estatísticas de escanteios.
        
        Args:
            texto: Texto normalizado
            time_casa: Nome do time da casa
            time_visitante: Nome do time visitante
            
        Returns:
            Dicionário com estatísticas de escanteios
        """
        # Padrões para extrair estatísticas de escanteios
        padrao_media_casa = re.compile(rf'{time_casa}.*?Média.*?escanteios.*?(\d+\.\d+)', re.IGNORECASE | re.DOTALL)
        padrao_media_visitante = re.compile(rf'{time_visitante}.*?Média.*?escanteios.*?(\d+\.\d+)', re.IGNORECASE | re.DOTALL)
        padrao_primeiro_tempo_casa = re.compile(rf'{time_casa}.*?1º tempo.*?(\d+\.\d+)', re.IGNORECASE | re.DOTALL)
        padrao_primeiro_tempo_visitante = re.compile(rf'{time_visitante}.*?1º tempo.*?(\d+\.\d+)', re.IGNORECASE | re.DOTALL)
        padrao_segundo_tempo_casa = re.compile(rf'{time_casa}.*?2º tempo.*?(\d+\.\d+)', re.IGNORECASE | re.DOTALL)
        padrao_segundo_tempo_visitante = re.compile(rf'{time_visitante}.*?2º tempo.*?(\d+\.\d+)', re.IGNORECASE | re.DOTALL)
        
        # Extrair valores
        media_casa = self._extrair_valor_decimal(texto, padrao_media_casa, 0.0)
        media_visitante = self._extrair_valor_decimal(texto, padrao_media_visitante, 0.0)
        primeiro_tempo_casa = self._extrair_valor_decimal(texto, padrao_primeiro_tempo_casa, 0.0)
        primeiro_tempo_visitante = self._extrair_valor_decimal(texto, padrao_primeiro_tempo_visitante, 0.0)
        segundo_tempo_casa = self._extrair_valor_decimal(texto, padrao_segundo_tempo_casa, 0.0)
        segundo_tempo_visitante = self._extrair_valor_decimal(texto, padrao_segundo_tempo_visitante, 0.0)
        
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
    
    def _extrair_estatisticas_cartoes(self, texto: str, time_casa: str, time_visitante: str) -> Dict[str, Any]:
        """
        Extrai estatísticas de cartões.
        
        Args:
            texto: Texto normalizado
            time_casa: Nome do time da casa
            time_visitante: Nome do time visitante
            
        Returns:
            Dicionário com estatísticas de cartões
        """
        # Padrões para extrair estatísticas de cartões
        padrao_amarelos_casa = re.compile(rf'{time_casa}.*?Cartões Amarelos.*?(\d+\.\d+)', re.IGNORECASE | re.DOTALL)
        padrao_amarelos_visitante = re.compile(rf'{time_visitante}.*?Cartões Amarelos.*?(\d+\.\d+)', re.IGNORECASE | re.DOTALL)
        padrao_vermelhos_casa = re.compile(rf'{time_casa}.*?Cartões Vermelhos.*?(\d+)', re.IGNORECASE | re.DOTALL)
        padrao_vermelhos_visitante = re.compile(rf'{time_visitante}.*?Cartões Vermelhos.*?(\d+)', re.IGNORECASE | re.DOTALL)
        
        # Extrair valores
        amarelos_casa = self._extrair_valor_decimal(texto, padrao_amarelos_casa, 0.0)
        amarelos_visitante = self._extrair_valor_decimal(texto, padrao_amarelos_visitante, 0.0)
        vermelhos_casa = self._extrair_valor_numerico(texto, padrao_vermelhos_casa, 0)
        vermelhos_visitante = self._extrair_valor_numerico(texto, padrao_vermelhos_visitante, 0)
        
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
    
    def _extrair_ultimos_jogos(self, texto: str, time: str) -> List[str]:
        """
        Extrai resultados dos últimos jogos de um time.
        
        Args:
            texto: Texto normalizado
            time: Nome do time
            
        Returns:
            Lista com resultados dos últimos jogos (V, E, D)
        """
        # Procurar seção de últimos jogos
        padrao_ultimos_jogos = re.compile(rf'{time}.*?Últimos.*?jogos.*?(V.*?D)', re.IGNORECASE | re.DOTALL)
        match_ultimos_jogos = padrao_ultimos_jogos.search(texto)
        
        if not match_ultimos_jogos:
            # Tentar outro padrão
            padrao_alternativo = re.compile(rf'{time}.*?Forma.*?(V.*?D)', re.IGNORECASE | re.DOTALL)
            match_ultimos_jogos = padrao_alternativo.search(texto)
            
            if not match_ultimos_jogos:
                return ["V", "E", "D", "V", "E"]  # Valores padrão
        
        # Extrair resultados
        resultados_texto = match_ultimos_jogos.group(1)
        resultados = re.findall(r'[VED]', resultados_texto, re.IGNORECASE)
        
        # Limitar a 5 resultados
        return resultados[:5]
    
    def _extrair_valor_numerico(self, texto: str, padrao: re.Pattern, valor_padrao: int) -> int:
        """
        Extrai um valor numérico do texto usando um padrão regex.
        
        Args:
            texto: Texto normalizado
            padrao: Padrão regex para extrair o valor
            valor_padrao: Valor padrão se não encontrar
            
        Returns:
            Valor numérico extraído ou valor padrão
        """
        match = padrao.search(texto)
        
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                return valor_padrao
        
        return valor_padrao
    
    def _extrair_valor_decimal(self, texto: str, padrao: re.Pattern, valor_padrao: float) -> float:
        """
        Extrai um valor decimal do texto usando um padrão regex.
        
        Args:
            texto: Texto normalizado
            padrao: Padrão regex para extrair o valor
            valor_padrao: Valor padrão se não encontrar
            
        Returns:
            Valor decimal extraído ou valor padrão
        """
        match = padrao.search(texto)
        
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                return valor_padrao
        
        return valor_padrao
    
    def _gerar_id_jogo(self, time_casa: str, time_visitante: str, data: str, hora: str) -> str:
        """
        Gera um ID único para o jogo.
        
        Args:
            time_casa: Nome do time da casa
            time_visitante: Nome do time visitante
            data: Data do jogo
            hora: Hora do jogo
            
        Returns:
            ID único para o jogo
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
        hash_md5 = hashlib.md5(string_hash.encode()).hexdigest()[:8]
        
        # Retornar ID no formato: time_casa_time_visitante_hash
        return f"{time_casa_norm}_{time_visitante_norm}_{hash_md5}"

# Exemplo de uso
if __name__ == "__main__":
    processador = ProcessadorTextoCopiadoAcademiaApostas()
    
    # Exemplo de texto copiado
    texto_exemplo = """
    Corinthians vs Sport
    19/04/2025 - 16:00
    Brasileirão Série A
    
    Quem será o vencedor?
    Casa    Empate    Fora
    1.5     3.9       7.5
    
    ESTATÍSTICAS
    
    Corinthians
    Posição: 14
    Pontos: 4
    Vitórias: 1
    Empates: 1
    Derrotas: 2
    Gols Marcados: 4
    Gols Sofridos: 5
    Últimos jogos: V E D V E
    
    Sport
    Posição: 20
    Pontos: 2
    Vitórias: 0
    Empates: 2
    Derrotas: 3
    Gols Marcados: 2
    Gols Sofridos: 6
    Últimos jogos: D E D E D
    
    CONFRONTO DIRETO NOS ÚLTIMOS 3 ANOS
    2 jogos
    Vitórias Corinthians: 1
    Empates: 0
    Vitórias Sport: 1
    
    09/10/2021 - Sport 1-0 Corinthians - Brasileirão Série A
    24/09/2021 - Corinthians 2-1 Sport - Brasileirão Série A
    """
    
    resultado = processador.processar_texto(texto_exemplo)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
