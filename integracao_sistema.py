"""
Integração do processador de dados copiados com o sistema de apostas esportivas
-----------------------------------------------------------------------------
Este módulo integra o processador de dados copiados com o sistema de apostas esportivas existente.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union

# Importar módulos do sistema
from processador_texto_copiado import ProcessadorTextoCopiadoAcademiaApostas
from coleta_dados_reais import ColetorDadosReais

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('integracao_sistema')

class SistemaApostasEsportivas:
    """
    Classe principal do sistema de apostas esportivas, integrando todos os componentes.
    """
    
    def __init__(self, diretorio_dados: str = None):
        """
        Inicializa o sistema de apostas esportivas.
        
        Args:
            diretorio_dados: Diretório para salvar os dados. Se None, usa o diretório atual.
        """
        if diretorio_dados is None:
            self.diretorio_dados = os.path.join(os.getcwd(), 'dados')
        else:
            self.diretorio_dados = diretorio_dados
            
        # Criar diretórios se não existirem
        os.makedirs(self.diretorio_dados, exist_ok=True)
        
        # Inicializar componentes
        self.processador = ProcessadorTextoCopiadoAcademiaApostas()
        self.coletor = ColetorDadosReais(diretorio_dados=self.diretorio_dados)
        
        logger.info(f"Sistema de apostas esportivas inicializado. Diretório de dados: {self.diretorio_dados}")
    
    def processar_texto_copiado(self, texto: str) -> Dict[str, Any]:
        """
        Processa texto copiado do site Academia das Apostas Brasil.
        
        Args:
            texto: Texto copiado do site
            
        Returns:
            Dicionário com dados extraídos do texto
        """
        logger.info("Processando texto copiado")
        
        try:
            # Processar o texto usando o processador
            resultado = self.processador.processar_texto(texto)
            
            # Salvar jogos e estatísticas extraídos
            if 'jogos' in resultado and resultado['jogos']:
                self.coletor._salvar_jogos(resultado['jogos'])
                
                # Extrair estatísticas para os jogos, se não estiverem presentes
                if 'estatisticas' not in resultado or not resultado['estatisticas']:
                    estatisticas = {}
                    for jogo in resultado['jogos']:
                        try:
                            # Tentar extrair estatísticas do texto
                            estatisticas_jogo = self.processador._extrair_estatisticas_jogo(
                                texto, jogo['time_casa'], jogo['time_visitante']
                            )
                            estatisticas[jogo['id_jogo']] = estatisticas_jogo
                        except Exception as e:
                            logger.error(f"Erro ao extrair estatísticas para o jogo {jogo['id_jogo']}: {str(e)}")
                    
                    resultado['estatisticas'] = estatisticas
                
                # Salvar estatísticas
                if 'estatisticas' in resultado and resultado['estatisticas']:
                    for id_jogo, estatisticas_jogo in resultado['estatisticas'].items():
                        self.coletor._salvar_estatisticas(id_jogo, estatisticas_jogo)
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao processar texto copiado: {str(e)}")
            return {"erro": str(e)}
    
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
        
        try:
            # Usar o coletor para obter jogos
            jogos = self.coletor.coletar_jogos_do_dia(data, dias_futuros)
            return jogos
            
        except Exception as e:
            logger.error(f"Erro ao coletar jogos: {str(e)}")
            return []
    
    def coletar_estatisticas_jogos(self, jogos: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Coleta estatísticas para uma lista de jogos.
        
        Args:
            jogos: Lista de dicionários com informações dos jogos.
            
        Returns:
            Dicionário com estatísticas dos jogos, indexado pelo ID do jogo.
        """
        logger.info(f"Coletando estatísticas para {len(jogos)} jogos")
        
        try:
            # Usar o coletor para obter estatísticas
            estatisticas = self.coletor.coletar_estatisticas_jogos(jogos)
            return estatisticas
            
        except Exception as e:
            logger.error(f"Erro ao coletar estatísticas: {str(e)}")
            return {}
    
    def carregar_jogos(self) -> List[Dict[str, Any]]:
        """
        Carrega jogos salvos anteriormente.
        
        Returns:
            Lista de dicionários com informações dos jogos.
        """
        return self.coletor.carregar_jogos()
    
    def carregar_estatisticas(self, id_jogo: str) -> Optional[Dict[str, Any]]:
        """
        Carrega estatísticas de um jogo salvo anteriormente.
        
        Args:
            id_jogo: ID único do jogo
            
        Returns:
            Dicionário com estatísticas do jogo, ou None se não encontrado.
        """
        return self.coletor.carregar_estatisticas(id_jogo)
    
    def gerar_recomendacoes(self, id_jogo: str) -> Dict[str, Any]:
        """
        Gera recomendações de apostas para um jogo.
        
        Args:
            id_jogo: ID único do jogo
            
        Returns:
            Dicionário com recomendações de apostas.
        """
        logger.info(f"Gerando recomendações para o jogo {id_jogo}")
        
        # Carregar estatísticas do jogo
        estatisticas = self.carregar_estatisticas(id_jogo)
        
        if not estatisticas:
            logger.warning(f"Estatísticas não encontradas para o jogo {id_jogo}")
            return {
                "erro": "Estatísticas não encontradas para este jogo",
                "recomendacoes": {}
            }
        
        # Carregar jogos para encontrar o jogo específico
        jogos = self.carregar_jogos()
        jogo = next((j for j in jogos if j['id_jogo'] == id_jogo), None)
        
        if not jogo:
            logger.warning(f"Jogo não encontrado: {id_jogo}")
            return {
                "erro": "Jogo não encontrado",
                "recomendacoes": {}
            }
        
        # Gerar recomendações com base nas estatísticas
        recomendacoes = self._calcular_recomendacoes(jogo, estatisticas)
        
        return {
            "jogo": jogo,
            "recomendacoes": recomendacoes
        }
    
    def _calcular_recomendacoes(self, jogo: Dict[str, Any], estatisticas: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula recomendações de apostas com base nas estatísticas.
        
        Args:
            jogo: Dicionário com informações do jogo
            estatisticas: Dicionário com estatísticas do jogo
            
        Returns:
            Dicionário com recomendações de apostas.
        """
        # Inicializar recomendações
        recomendacoes = {
            "baixo_risco": [],
            "moderado": [],
            "alto_retorno": []
        }
        
        # Extrair informações relevantes
        time_casa = estatisticas.get('time_casa', {})
        time_visitante = estatisticas.get('time_visitante', {})
        confrontos = estatisticas.get('confrontos_diretos', {}).get('resumo', {})
        odds = estatisticas.get('odds', {})
        
        # Verificar se há informações suficientes
        if not time_casa or not time_visitante or not odds:
            logger.warning("Informações insuficientes para gerar recomendações")
            return recomendacoes
        
        # Calcular força relativa dos times
        forca_casa = self._calcular_forca_time(time_casa)
        forca_visitante = self._calcular_forca_time(time_visitante)
        
        # Calcular vantagem do mandante
        vantagem_mandante = 1.2  # Fator de vantagem para o time da casa
        
        # Ajustar força com vantagem do mandante
        forca_casa_ajustada = forca_casa * vantagem_mandante
        
        # Calcular probabilidades
        prob_vitoria_casa = forca_casa_ajustada / (forca_casa_ajustada + forca_visitante)
        prob_vitoria_visitante = forca_visitante / (forca_casa_ajustada + forca_visitante)
        prob_empate = 1 - prob_vitoria_casa - prob_vitoria_visitante
        
        # Ajustar probabilidades para somar 1
        total_prob = prob_vitoria_casa + prob_empate + prob_vitoria_visitante
        prob_vitoria_casa /= total_prob
        prob_empate /= total_prob
        prob_vitoria_visitante /= total_prob
        
        # Calcular valor esperado (EV) para cada aposta
        odds_casa = odds.get('resultado', {}).get('casa', 0)
        odds_empate = odds.get('resultado', {}).get('empate', 0)
        odds_visitante = odds.get('resultado', {}).get('visitante', 0)
        
        ev_casa = (prob_vitoria_casa * odds_casa) - 1
        ev_empate = (prob_empate * odds_empate) - 1
        ev_visitante = (prob_vitoria_visitante * odds_visitante) - 1
        
        # Gerar recomendações de baixo risco
        if prob_vitoria_casa > 0.6 and ev_casa > 0:
            recomendacoes["baixo_risco"].append({
                "mercado": "Resultado Final",
                "selecao": f"Vitória {jogo['time_casa']}",
                "odd": odds_casa,
                "confianca": round(prob_vitoria_casa * 100, 2),
                "ev": round(ev_casa * 100, 2)
            })
        elif prob_vitoria_visitante > 0.6 and ev_visitante > 0:
            recomendacoes["baixo_risco"].append({
                "mercado": "Resultado Final",
                "selecao": f"Vitória {jogo['time_visitante']}",
                "odd": odds_visitante,
                "confianca": round(prob_vitoria_visitante * 100, 2),
                "ev": round(ev_visitante * 100, 2)
            })
        
        # Verificar mercado de gols
        media_gols_casa = time_casa.get('gols_marcados', 0) / max(time_casa.get('jogos', 1), 1)
        media_gols_visitante = time_visitante.get('gols_marcados', 0) / max(time_visitante.get('jogos', 1), 1)
        media_gols_total = media_gols_casa + media_gols_visitante
        
        odds_over = odds.get('over_under', {}).get('over_2_5', 0)
        odds_under = odds.get('over_under', {}).get('under_2_5', 0)
        
        prob_over = 0.6 if media_gols_total > 2.5 else 0.4
        prob_under = 1 - prob_over
        
        ev_over = (prob_over * odds_over) - 1
        ev_under = (prob_under * odds_under) - 1
        
        # Adicionar recomendação de gols
        if media_gols_total > 2.8 and ev_over > 0:
            recomendacoes["baixo_risco"].append({
                "mercado": "Over/Under 2.5",
                "selecao": "Over 2.5",
                "odd": odds_over,
                "confianca": round(prob_over * 100, 2),
                "ev": round(ev_over * 100, 2)
            })
        elif media_gols_total < 2.2 and ev_under > 0:
            recomendacoes["baixo_risco"].append({
                "mercado": "Over/Under 2.5",
                "selecao": "Under 2.5",
                "odd": odds_under,
                "confianca": round(prob_under * 100, 2),
                "ev": round(ev_under * 100, 2)
            })
        
        # Gerar recomendações de risco moderado
        if 0.45 < prob_vitoria_casa < 0.6 and ev_casa > 0.1:
            recomendacoes["moderado"].append({
                "mercado": "Resultado Final",
                "selecao": f"Vitória {jogo['time_casa']}",
                "odd": odds_casa,
                "confianca": round(prob_vitoria_casa * 100, 2),
                "ev": round(ev_casa * 100, 2)
            })
        elif 0.45 < prob_vitoria_visitante < 0.6 and ev_visitante > 0.1:
            recomendacoes["moderado"].append({
                "mercado": "Resultado Final",
                "selecao": f"Vitória {jogo['time_visitante']}",
                "odd": odds_visitante,
                "confianca": round(prob_vitoria_visitante * 100, 2),
                "ev": round(ev_visitante * 100, 2)
            })
        elif prob_empate > 0.3 and ev_empate > 0.1:
            recomendacoes["moderado"].append({
                "mercado": "Resultado Final",
                "selecao": "Empate",
                "odd": odds_empate,
                "confianca": round(prob_empate * 100, 2),
                "ev": round(ev_empate * 100, 2)
            })
        
        # Verificar mercado de ambas marcam
        media_gols_sofridos_casa = time_casa.get('gols_sofridos', 0) / max(time_casa.get('jogos', 1), 1)
        media_gols_sofridos_visitante = time_visitante.get('gols_sofridos', 0) / max(time_visitante.get('jogos', 1), 1)
        
        prob_ambas_marcam = min(1.0, (media_gols_casa * media_gols_sofridos_visitante + media_gols_visitante * media_gols_sofridos_casa) / 2)
        prob_nao_ambas = 1 - prob_ambas_marcam
        
        odds_ambas_sim = odds.get('ambos_marcam', {}).get('sim', 0)
        odds_ambas_nao = odds.get('ambos_marcam', {}).get('nao', 0)
        
        ev_ambas_sim = (prob_ambas_marcam * odds_ambas_sim) - 1
        ev_ambas_nao = (prob_nao_ambas * odds_ambas_nao) - 1
        
        if prob_ambas_marcam > 0.6 and ev_ambas_sim > 0:
            recomendacoes["moderado"].append({
                "mercado": "Ambas Marcam",
                "selecao": "Sim",
                "odd": odds_ambas_sim,
                "confianca": round(prob_ambas_marcam * 100, 2),
                "ev": round(ev_ambas_sim * 100, 2)
            })
        elif prob_nao_ambas > 0.6 and ev_ambas_nao > 0:
            recomendacoes["moderado"].append({
                "mercado": "Ambas Marcam",
                "selecao": "Não",
                "odd": odds_ambas_nao,
                "confianca": round(prob_nao_ambas * 100, 2),
                "ev": round(ev_ambas_nao * 100, 2)
            })
        
        # Gerar recomendações de alto retorno
        if 0.3 < prob_vitoria_casa < 0.45 and odds_casa > 2.5:
            recomendacoes["alto_retorno"].append({
                "mercado": "Resultado Final",
                "selecao": f"Vitória {jogo['time_casa']}",
                "odd": odds_casa,
                "confianca": round(prob_vitoria_casa * 100, 2),
                "ev": round(ev_casa * 100, 2)
            })
        elif 0.3 < prob_vitoria_visitante < 0.45 and odds_visitante > 2.5:
            recomendacoes["alto_retorno"].append({
                "mercado": "Resultado Final",
                "selecao": f"Vitória {jogo['time_visitante']}",
                "odd": odds_visitante,
                "confianca": round(prob_vitoria_visitante * 100, 2),
                "ev": round(ev_visitante * 100, 2)
            })
        elif 0.25 < prob_empate < 0.35 and odds_empate > 3.0:
            recomendacoes["alto_retorno"].append({
                "mercado": "Resultado Final",
                "selecao": "Empate",
                "odd": odds_empate,
                "confianca": round(prob_empate * 100, 2),
                "ev": round(ev_empate * 100, 2)
            })
        
        # Adicionar recomendações para mercados adicionais
        self._adicionar_recomendacoes_mercados_adicionais(recomendacoes, jogo, estatisticas)
        
        return recomendacoes
    
    def _calcular_forca_time(self, time_info: Dict[str, Any]) -> float:
        """
        Calcula a força de um time com base em suas estatísticas.
        
        Args:
            time_info: Dicionário com informações do time
            
        Returns:
            Valor numérico representando a força do time
        """
        # Extrair estatísticas relevantes
        pontos = time_info.get('pontos', 0)
        vitorias = time_info.get('vitorias', 0)
        empates = time_info.get('empates', 0)
        derrotas = time_info.get('derrotas', 0)
        gols_marcados = time_info.get('gols_marcados', 0)
        gols_sofridos = time_info.get('gols_sofridos', 0)
        
        # Calcular número de jogos
        jogos = vitorias + empates + derrotas
        
        if jogos == 0:
            return 1.0  # Valor padrão se não houver jogos
        
        # Calcular média de pontos por jogo
        media_pontos = pontos / jogos
        
        # Calcular saldo de gols
        saldo_gols = gols_marcados - gols_sofridos
        
        # Calcular média de gols marcados e sofridos
        media_gols_marcados = gols_marcados / jogos
        media_gols_sofridos = gols_sofridos / jogos if gols_sofridos > 0 else 0.5  # Evitar divisão por zero
        
        # Calcular força com base em pontos, saldo de gols e médias
        forca = (media_pontos * 2) + (saldo_gols * 0.1) + (media_gols_marcados * 0.5) - (media_gols_sofridos * 0.3)
        
        # Ajustar para valor positivo
        forca = max(0.5, forca)
        
        return forca
    
    def _adicionar_recomendacoes_mercados_adicionais(self, recomendacoes: Dict[str, List[Dict[str, Any]]], 
                                                   jogo: Dict[str, Any], estatisticas: Dict[str, Any]) -> None:
        """
        Adiciona recomendações para mercados adicionais como escanteios e cartões.
        
        Args:
            recomendacoes: Dicionário com recomendações existentes
            jogo: Dicionário com informações do jogo
            estatisticas: Dicionário com estatísticas do jogo
        """
        # Verificar se há informações sobre mercados adicionais
        mercados_adicionais = estatisticas.get('mercados_adicionais', {})
        
        if not mercados_adicionais:
            return
        
        # Processar escanteios
        escanteios = mercados_adicionais.get('escanteios', {})
        
        if escanteios:
            # Calcular média de escanteios por jogo
            media_escanteios_casa = escanteios.get('time_casa', {}).get('media_por_jogo', 0)
            media_escanteios_visitante = escanteios.get('time_visitante', {}).get('media_por_jogo', 0)
            media_escanteios_total = media_escanteios_casa + media_escanteios_visitante
            
            # Gerar recomendações de escanteios
            if media_escanteios_total > 10:
                recomendacoes["moderado"].append({
                    "mercado": "Escanteios",
                    "selecao": "Over 9.5",
                    "odd": 1.9,  # Valor padrão, ajustar se disponível
                    "confianca": round(min(90, media_escanteios_total * 8), 2),
                    "ev": round((min(0.9, media_escanteios_total / 12) * 1.9) - 1, 2) * 100
                })
            elif media_escanteios_total < 8:
                recomendacoes["moderado"].append({
                    "mercado": "Escanteios",
                    "selecao": "Under 9.5",
                    "odd": 1.9,  # Valor padrão, ajustar se disponível
                    "confianca": round(min(90, (12 - media_escanteios_total) * 8), 2),
                    "ev": round((min(0.9, (12 - media_escanteios_total) / 12) * 1.9) - 1, 2) * 100
                })
        
        # Processar cartões
        cartoes = mercados_adicionais.get('cartoes', {})
        
        if cartoes:
            # Calcular média de cartões por jogo
            media_cartoes_casa = cartoes.get('time_casa', {}).get('cartoes_amarelos_media', 0)
            media_cartoes_visitante = cartoes.get('time_visitante', {}).get('cartoes_amarelos_media', 0)
            media_cartoes_total = media_cartoes_casa + media_cartoes_visitante
            
            # Gerar recomendações de cartões
            if media_cartoes_total > 5:
                recomendacoes["alto_retorno"].append({
                    "mercado": "Cartões",
                    "selecao": "Over 4.5",
                    "odd": 2.0,  # Valor padrão, ajustar se disponível
                    "confianca": round(min(85, media_cartoes_total * 15), 2),
                    "ev": round((min(0.85, media_cartoes_total / 6) * 2.0) - 1, 2) * 100
                })
            elif media_cartoes_total < 3:
                recomendacoes["alto_retorno"].append({
                    "mercado": "Cartões",
                    "selecao": "Under 4.5",
                    "odd": 2.0,  # Valor padrão, ajustar se disponível
                    "confianca": round(min(85, (6 - media_cartoes_total) * 15), 2),
                    "ev": round((min(0.85, (6 - media_cartoes_total) / 6) * 2.0) - 1, 2) * 100
                })
    
    def gerar_estrategia_cashout(self, id_jogo: str, valor_aposta: float, odd_aposta: float) -> Dict[str, Any]:
        """
        Gera estratégia de cashout para uma aposta.
        
        Args:
            id_jogo: ID único do jogo
            valor_aposta: Valor da aposta
            odd_aposta: Odd da aposta
            
        Returns:
            Dicionário com estratégia de cashout.
        """
        logger.info(f"Gerando estratégia de cashout para o jogo {id_jogo}")
        
        # Carregar estatísticas do jogo
        estatisticas = self.carregar_estatisticas(id_jogo)
        
        if not estatisticas:
            logger.warning(f"Estatísticas não encontradas para o jogo {id_jogo}")
            return {
                "erro": "Estatísticas não encontradas para este jogo",
                "estrategia": {}
            }
        
        # Carregar jogos para encontrar o jogo específico
        jogos = self.carregar_jogos()
        jogo = next((j for j in jogos if j['id_jogo'] == id_jogo), None)
        
        if not jogo:
            logger.warning(f"Jogo não encontrado: {id_jogo}")
            return {
                "erro": "Jogo não encontrado",
                "estrategia": {}
            }
        
        # Calcular potencial retorno
        potencial_retorno = valor_aposta * odd_aposta
        
        # Calcular estratégia de cashout
        estrategia = {
            "valor_aposta": valor_aposta,
            "odd_aposta": odd_aposta,
            "potencial_retorno": potencial_retorno,
            "momentos_cashout": [
                {
                    "momento": "Antes do jogo",
                    "condicao": "Se a odd cair para menos de 80% do valor original",
                    "valor_sugerido": round(valor_aposta * 1.1, 2),
                    "percentual_lucro": "10%"
                },
                {
                    "momento": "Primeiros 15 minutos",
                    "condicao": "Se o time da aposta marcar um gol",
                    "valor_sugerido": round(potencial_retorno * 0.3, 2),
                    "percentual_lucro": "30% do potencial"
                },
                {
                    "momento": "Intervalo",
                    "condicao": "Se o time da aposta estiver vencendo",
                    "valor_sugerido": round(potencial_retorno * 0.6, 2),
                    "percentual_lucro": "60% do potencial"
                },
                {
                    "momento": "60-75 minutos",
                    "condicao": "Se o time da aposta estiver vencendo ou empatando",
                    "valor_sugerido": round(potencial_retorno * 0.8, 2),
                    "percentual_lucro": "80% do potencial"
                }
            ],
            "recomendacao_geral": "Realizar cashout se o valor oferecido for maior que 70% do potencial retorno"
        }
        
        return {
            "jogo": jogo,
            "estrategia": estrategia
        }
    
    def gerar_relatorio_json(self, id_jogo: str) -> str:
        """
        Gera relatório em formato JSON para um jogo.
        
        Args:
            id_jogo: ID único do jogo
            
        Returns:
            String JSON com relatório completo.
        """
        logger.info(f"Gerando relatório JSON para o jogo {id_jogo}")
        
        # Carregar estatísticas do jogo
        estatisticas = self.carregar_estatisticas(id_jogo)
        
        if not estatisticas:
            logger.warning(f"Estatísticas não encontradas para o jogo {id_jogo}")
            return json.dumps({
                "erro": "Estatísticas não encontradas para este jogo",
                "relatorio": {}
            }, indent=2, ensure_ascii=False)
        
        # Carregar jogos para encontrar o jogo específico
        jogos = self.carregar_jogos()
        jogo = next((j for j in jogos if j['id_jogo'] == id_jogo), None)
        
        if not jogo:
            logger.warning(f"Jogo não encontrado: {id_jogo}")
            return json.dumps({
                "erro": "Jogo não encontrado",
                "relatorio": {}
            }, indent=2, ensure_ascii=False)
        
        # Gerar recomendações
        recomendacoes = self._calcular_recomendacoes(jogo, estatisticas)
        
        # Gerar estratégia de cashout (exemplo com valores padrão)
        estrategia_cashout = self.gerar_estrategia_cashout(id_jogo, 100.0, 2.0)
        
        # Construir relatório completo
        relatorio = {
            "jogo": jogo,
            "estatisticas": estatisticas,
            "recomendacoes": recomendacoes,
            "estrategia_cashout": estrategia_cashout.get("estrategia", {})
        }
        
        return json.dumps(relatorio, indent=2, ensure_ascii=False)

# Exemplo de uso
if __name__ == "__main__":
    sistema = SistemaApostasEsportivas()
    
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
    
    # Processar texto
    resultado = sistema.processar_texto_copiado(texto_exemplo)
    print(f"Jogos encontrados: {len(resultado.get('jogos', []))}")
    
    # Carregar jogos
    jogos = sistema.carregar_jogos()
    
    if jogos:
        # Gerar relatório para o primeiro jogo
        id_jogo = jogos[0]['id_jogo']
        relatorio = sistema.gerar_relatorio_json(id_jogo)
        print(f"Relatório gerado para o jogo {id_jogo}")
        
        # Salvar relatório em arquivo
        with open(f"relatorio_{id_jogo}.json", "w", encoding="utf-8") as f:
            f.write(relatorio)
            print(f"Relatório salvo em relatorio_{id_jogo}.json")
