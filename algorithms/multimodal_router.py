from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging

from models.grafo_multimodal import (
    GrafoMultiModal, VerticeMultiModal, ArestaMultiModal,
    TipoVertice, TipoModal
)
from models.metricas import SegmentoRota, RotaCompleta, MetricasDijkstra
from algorithms.dijkstra import DijkstraInstrumentado
from config.settings import settings

logger = logging.getLogger(__name__)

class RoteadorMultiModal:
    """Roteador multi-modal com suporte a múltiplos critérios de otimização"""
    
    def __init__(self, grafo: GrafoMultiModal):
        self.grafo = grafo
        self.dijkstra = DijkstraInstrumentado(grafo)
    
    def calcular_rotas(
        self,
        origem_coords: Tuple[float, float],
        destino_coords: Tuple[float, float],
        origem_nome: str = "Origem",
        destino_nome: str = "Destino",
        modais_permitidos: Optional[List[TipoModal]] = None,
        k_rotas: int = 3,
        criterio: str = 'tempo'  # 'tempo', 'custo', 'emissoes', 'multiobjetivo'
    ) -> List[RotaCompleta]:
        """
        Calcula k rotas alternativas entre origem e destino
        
        Args:
            origem_coords: (lat, lon) da origem
            destino_coords: (lat, lon) do destino
            origem_nome: Nome do local de origem
            destino_nome: Nome do local de destino
            modais_permitidos: Lista de modais permitidos (None = todos)
            k_rotas: Número de rotas alternativas
            criterio: Critério de otimização
        
        Returns:
            Lista de RotaCompleta ordenada por score
        """
        # 1. Criar/encontrar vértices de origem e destino
        vertice_origem = self._criar_vertice_temporario(
            origem_coords[0], origem_coords[1], origem_nome
        )
        vertice_destino = self._criar_vertice_temporario(
            destino_coords[0], destino_coords[1], destino_nome
        )
        
        # 2. Conectar origem e destino ao grafo (arestas de caminhada)
        self._conectar_vertice_ao_grafo(vertice_origem)
        self._conectar_vertice_ao_grafo(vertice_destino)
        
        # 3. Definir função de custo baseada no critério
        funcao_custo = self._obter_funcao_custo(criterio)
        
        # 4. Calcular k caminhos usando Dijkstra
        caminhos = self.dijkstra.k_caminhos_mais_curtos(
            vertice_origem.id,
            vertice_destino.id,
            k=k_rotas,
            funcao_custo=funcao_custo
        )
        
        # 5. Converter caminhos em RotaCompleta
        rotas_completas = []
        for idx, (caminho_ids, custo_total) in enumerate(caminhos):
            rota = self._construir_rota_completa(
                caminho_ids,
                origem_nome,
                destino_nome,
                idx + 1
            )
            rotas_completas.append(rota)
        
        # 6. Calcular scores multi-objetivo e classificar
        rotas_completas = self._classificar_rotas(rotas_completas)
        
        # 7. Limpar vértices temporários
        self._remover_vertice_temporario(vertice_origem)
        self._remover_vertice_temporario(vertice_destino)
        
        return rotas_completas
    
    def _criar_vertice_temporario(self, lat: float, lon: float, nome: str) -> VerticeMultiModal:
        """Cria um vértice temporário para origem/destino"""
        vertice = VerticeMultiModal(
            id=f"temp_{nome}_{lat}_{lon}",
            tipo=TipoVertice.ENDERECO,
            lat=lat,
            lon=lon,
            nome=nome
        )
        self.grafo.adicionar_vertice(vertice)
        return vertice
    
    def _conectar_vertice_ao_grafo(self, vertice: VerticeMultiModal):
        """Conecta um vértice temporário aos vértices próximos por caminhada"""
        proximos = self.grafo.encontrar_vertices_proximos(
            vertice.lat,
            vertice.lon,
            raio_m=settings.max_walking_distance_m
        )
        
        velocidade_caminhada_kmh = settings.walking_speed_kmh
        
        for proximo_vertice, distancia_m in proximos:
            tempo_min = (distancia_m / 1000) / velocidade_caminhada_kmh * 60
            
            # Aresta de ida
            aresta_ida = ArestaMultiModal(
                origem=vertice,
                destino=proximo_vertice,
                modal=TipoModal.CAMINHADA,
                distancia_m=distancia_m,
                tempo_min=tempo_min,
                custo_reais=0.0,
                emissoes_co2_kg=0.0
            )
            self.grafo.adicionar_aresta(aresta_ida)
            
            # Aresta de volta
            aresta_volta = ArestaMultiModal(
                origem=proximo_vertice,
                destino=vertice,
                modal=TipoModal.CAMINHADA,
                distancia_m=distancia_m,
                tempo_min=tempo_min,
                custo_reais=0.0,
                emissoes_co2_kg=0.0
            )
            self.grafo.adicionar_aresta(aresta_volta)
    
    def _remover_vertice_temporario(self, vertice: VerticeMultiModal):
        """Remove vértice temporário do grafo"""
        if vertice.id in self.grafo.vertices:
            del self.grafo.vertices[vertice.id]
        if vertice.id in self.grafo.adjacencias:
            del self.grafo.adjacencias[vertice.id]
        
        # Remover arestas que chegam neste vértice
        for vid in list(self.grafo.adjacencias.keys()):
            self.grafo.adjacencias[vid] = [
                a for a in self.grafo.adjacencias[vid]
                if a.destino.id != vertice.id
            ]
    
    def _obter_funcao_custo(self, criterio: str):
        """Retorna função de custo baseada no critério"""
        if criterio == 'tempo':
            return lambda aresta: aresta.custo_total_tempo()
        elif criterio == 'custo':
            return lambda aresta: aresta.custo_reais
        elif criterio == 'emissoes':
            return lambda aresta: aresta.emissoes_co2_kg
        elif criterio == 'distancia':
            return lambda aresta: aresta.distancia_m / 1000
        else:  # multiobjetivo
            return lambda aresta: (
                settings.peso_tempo * aresta.custo_total_tempo() / 60 +
                settings.peso_custo * aresta.custo_reais / 50 +
                settings.peso_emissoes * aresta.emissoes_co2_kg / 10
            )
    
    def _construir_rota_completa(
        self,
        caminho_ids: List[str],
        origem_nome: str,
        destino_nome: str,
        id_rota: int
    ) -> RotaCompleta:
        """Constrói objeto RotaCompleta a partir de um caminho"""
        segmentos = []
        
        for i in range(len(caminho_ids) - 1):
            u_id = caminho_ids[i]
            v_id = caminho_ids[i + 1]
            
            # Encontrar aresta correspondente
            aresta = None
            for a in self.grafo.adjacencias[u_id]:
                if a.destino.id == v_id:
                    aresta = a
                    break
            
            if aresta:
                segmento = SegmentoRota(
                    tipo_modal=aresta.modal.value,
                    origem=aresta.origem.nome,
                    destino=aresta.destino.nome,
                    origem_coords=(aresta.origem.lat, aresta.origem.lon),
                    destino_coords=(aresta.destino.lat, aresta.destino.lon),
                    distancia_m=aresta.distancia_m,
                    tempo_min=aresta.tempo_min,
                    custo_reais=aresta.custo_reais,
                    emissoes_co2_kg=aresta.emissoes_co2_kg,
                    linha=aresta.linha
                )
                segmentos.append(segmento)
        
        # Agrupar segmentos consecutivos do mesmo modal
        segmentos_agrupados = self._agrupar_segmentos(segmentos)
        
        # Calcular totais
        distancia_total_km = sum(s.distancia_m for s in segmentos_agrupados) / 1000
        tempo_total_min = sum(s.tempo_min for s in segmentos_agrupados)
        custo_total_reais = sum(s.custo_reais for s in segmentos_agrupados)
        emissoes_totais_kg = sum(s.emissoes_co2_kg for s in segmentos_agrupados)
        
        # Contar transferências
        modais_utilizados = list(set(s.tipo_modal for s in segmentos_agrupados))
        numero_transferencias = len(segmentos_agrupados) - 1
        
        # Score multi-objetivo normalizado
        score = (
            settings.peso_tempo * (tempo_total_min / 60) +
            settings.peso_custo * (custo_total_reais / 50) +
            settings.peso_emissoes * (emissoes_totais_kg / 10)
        )
        
        rota = RotaCompleta(
            id_rota=f"R{id_rota}",
            origem=origem_nome,
            destino=destino_nome,
            segmentos=segmentos_agrupados,
            distancia_total_km=distancia_total_km,
            tempo_total_min=tempo_total_min,
            custo_total_reais=custo_total_reais,
            emissoes_totais_kg=emissoes_totais_kg,
            numero_transferencias=numero_transferencias,
            modais_utilizados=modais_utilizados,
            score_multiobjetivo=score,
            melhor_para="equilibrado",  # Será atualizado em _classificar_rotas
            timestamp_calculo=datetime.now()
        )
        
        return rota
    
    def _agrupar_segmentos(self, segmentos: List[SegmentoRota]) -> List[SegmentoRota]:
        """Agrupa segmentos consecutivos do mesmo modal"""
        if not segmentos:
            return []
        
        agrupados = []
        atual = segmentos[0]
        
        for i in range(1, len(segmentos)):
            prox = segmentos[i]
            
            # Se mesmo modal e mesma linha (para ônibus), agrupa
            if (atual.tipo_modal == prox.tipo_modal and 
                atual.linha == prox.linha):
                # Combinar
                atual.destino = prox.destino
                atual.destino_coords = prox.destino_coords
                atual.distancia_m += prox.distancia_m
                atual.tempo_min += prox.tempo_min
                atual.custo_reais += prox.custo_reais
                atual.emissoes_co2_kg += prox.emissoes_co2_kg
            else:
                agrupados.append(atual)
                atual = prox
        
        agrupados.append(atual)
        return agrupados
    
    def _classificar_rotas(self, rotas: List[RotaCompleta]) -> List[RotaCompleta]:
        """Classifica rotas e determina qual é melhor para cada critério"""
        if not rotas:
            return rotas
        
        # Encontrar melhor rota para cada critério
        melhor_tempo = min(rotas, key=lambda r: r.tempo_total_min)
        melhor_custo = min(rotas, key=lambda r: r.custo_total_reais)
        melhor_emissoes = min(rotas, key=lambda r: r.emissoes_totais_kg)
        
        for rota in rotas:
            if rota == melhor_tempo:
                rota.melhor_para = "tempo"
            elif rota == melhor_custo:
                rota.melhor_para = "custo"
            elif rota == melhor_emissoes:
                rota.melhor_para = "sustentavel"
            else:
                rota.melhor_para = "equilibrado"
        
        # Ordenar por score multi-objetivo
        rotas.sort(key=lambda r: r.score_multiobjetivo)
        
        return rotas