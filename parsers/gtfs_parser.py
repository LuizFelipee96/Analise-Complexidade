
import pandas as pd
import os
from typing import Dict, List, Tuple
import logging
from datetime import datetime, timedelta

from models.grafo_multimodal import (
    GrafoMultiModal, VerticeMultiModal, ArestaMultiModal,
    TipoVertice, TipoModal
)
from config.settings import settings

logger = logging.getLogger(__name__)

class GTFSParser:
    """Parser de dados GTFS do Grande Recife"""
    
    def __init__(self, gtfs_path: str):
        self.gtfs_path = gtfs_path
        self.stops: pd.DataFrame = None
        self.routes: pd.DataFrame = None
        self.trips: pd.DataFrame = None
        self.stop_times: pd.DataFrame = None
        self.shapes: pd.DataFrame = None
        
    def carregar_dados(self):
        """Carrega todos os arquivos GTFS"""
        try:
            logger.info(f"Carregando dados GTFS de {self.gtfs_path}")
            
            self.stops = pd.read_csv(os.path.join(self.gtfs_path, 'stops.txt'))
            self.routes = pd.read_csv(os.path.join(self.gtfs_path, 'routes.txt'))
            self.trips = pd.read_csv(os.path.join(self.gtfs_path, 'trips.txt'))
            self.stop_times = pd.read_csv(os.path.join(self.gtfs_path, 'stop_times.txt'))
            
            # Shapes é opcional
            try:
                self.shapes = pd.read_csv(os.path.join(self.gtfs_path, 'shapes.txt'))
            except:
                self.shapes = None
            
            logger.info(f"✓ Carregados: {len(self.stops)} paradas, {len(self.routes)} rotas")
            
        except Exception as e:
            logger.error(f"Erro ao carregar GTFS: {e}")
            raise
    
    def popular_grafo(self, grafo: GrafoMultiModal, regiao_bbox: Tuple[float, float, float, float] = None):
        """
        Popula o grafo com dados GTFS
        
        Args:
            grafo: Grafo a ser populado
            regiao_bbox: (lat_min, lon_min, lat_max, lon_max) para filtrar região
        """
        if self.stops is None:
            self.carregar_dados()
        
        # Filtrar paradas na região (se especificado)
        stops_filtradas = self.stops
        if regiao_bbox:
            lat_min, lon_min, lat_max, lon_max = regiao_bbox
            stops_filtradas = self.stops[
                (self.stops['stop_lat'] >= lat_min) &
                (self.stops['stop_lat'] <= lat_max) &
                (self.stops['stop_lon'] >= lon_min) &
                (self.stops['stop_lon'] <= lon_max)
            ]
        
        logger.info(f"Adicionando {len(stops_filtradas)} paradas ao grafo...")
        
        # 1. Adicionar paradas como vértices
        for _, stop in stops_filtradas.iterrows():
            # Obter linhas que passam nesta parada
            linhas = self._obter_linhas_parada(stop['stop_id'])
            
            vertice = VerticeMultiModal(
                id=f"stop_{stop['stop_id']}",
                tipo=TipoVertice.PARADA_ONIBUS,
                lat=stop['stop_lat'],
                lon=stop['stop_lon'],
                nome=stop['stop_name'],
                linhas_onibus=linhas
            )
            grafo.adicionar_vertice(vertice)
        
        # 2. Adicionar conexões de ônibus (arestas entre paradas consecutivas)
        logger.info("Adicionando conexões de ônibus...")
        self._adicionar_conexoes_onibus(grafo)
        
        # 3. Adicionar arestas de caminhada entre paradas próximas
        logger.info("Adicionando conexões de caminhada...")
        grafo.adicionar_arestas_caminhada(raio_m=settings.max_walking_distance_m)
        
        logger.info(f"✓ Grafo populado: {grafo.estatisticas()}")
    
    def _obter_linhas_parada(self, stop_id: str) -> List[str]:
        """Retorna lista de linhas que passam em uma parada"""
        try:
            # Join stop_times -> trips -> routes
            paradas_trip = self.stop_times[self.stop_times['stop_id'] == stop_id]
            
            if paradas_trip.empty:
                return []
            
            trip_ids = paradas_trip['trip_id'].unique()
            
            # CORREÇÃO: Nome correto da variável
            trips_filtradas = self.trips[self.trips['trip_id'].isin(trip_ids)]
            
            if trips_filtradas.empty:
                return []
            
            route_ids = trips_filtradas['route_id'].unique()
            
            rotas = self.routes[self.routes['route_id'].isin(route_ids)]
            
            if rotas.empty:
                return []
            
            # Converter para string explicitamente
            linhas = rotas['route_short_name'].astype(str).tolist()
            
            return linhas
            
        except Exception as e:
            logger.warning(f"Erro ao obter linhas da parada {stop_id}: {e}")
            return []

    
    # CORREÇÃO: Converter para string explicitamente
        linhas = rotas['route_short_name'].astype(str).tolist()
    
        return linhas
    
    def _adicionar_conexoes_onibus(self, grafo: GrafoMultiModal):
        """Adiciona arestas representando conexões de ônibus entre paradas"""
        # Agrupar por trip_id
        for trip_id, trip_stops in self.stop_times.groupby('trip_id'):
            # Ordenar por sequência
            trip_stops = trip_stops.sort_values('stop_sequence')
            
            # Obter informações da rota
            trip_info = self.trips[self.trips['trip_id'] == trip_id].iloc[0]
            route_info = self.routes[self.routes['route_id'] == trip_info['route_id']].iloc[0]
            linha_nome = route_info['route_short_name']
            
            # Criar arestas entre paradas consecutivas
            for i in range(len(trip_stops) - 1):
                stop_atual = trip_stops.iloc[i]
                stop_prox = trip_stops.iloc[i + 1]
                
                # IDs dos vértices
                vertice_atual_id = f"stop_{stop_atual['stop_id']}"
                vertice_prox_id = f"stop_{stop_prox['stop_id']}"
                
                if vertice_atual_id not in grafo.vertices or vertice_prox_id not in grafo.vertices:
                    continue
                
                vertice_atual = grafo.vertices[vertice_atual_id]
                vertice_prox = grafo.vertices[vertice_prox_id]
                
                # Calcular tempo de viagem
                tempo_min = self._calcular_tempo_viagem(stop_atual, stop_prox)
                
                # Calcular distância
                distancia_m = vertice_atual.distancia_para(vertice_prox)
                
                # Custo e emissões (ônibus urbano)
                custo_reais = 4.10  # Tarifa padrão Recife 2025
                emissoes_co2_kg = distancia_m / 1000 * 0.08  # ~0.08 kg CO2/km para ônibus
                
                # Criar aresta
                aresta = ArestaMultiModal(
                    origem=vertice_atual,
                    destino=vertice_prox,
                    modal=TipoModal.ONIBUS,
                    distancia_m=distancia_m,
                    tempo_min=tempo_min,
                    custo_reais=custo_reais,
                    emissoes_co2_kg=emissoes_co2_kg,
                    linha=linha_nome,
                    frequencia_min=self._calcular_frequencia_linha(linha_nome),
                    penalidade_tempo=settings.default_bus_wait_time_min / 2  # Metade do tempo médio de espera
                )
                
                grafo.adicionar_aresta(aresta)
    
    def _calcular_tempo_viagem(self, stop1: pd.Series, stop2: pd.Series) -> float:
        """Calcula tempo de viagem entre duas paradas baseado em horários GTFS"""
        try:
            # Converter arrival_time para minutos
            def time_to_minutes(time_str):
                if pd.isna(time_str):
                    return None
                h, m, s = map(int, str(time_str).split(':'))
                return h * 60 + m + s / 60
            
            tempo1 = time_to_minutes(stop1['arrival_time'])
            tempo2 = time_to_minutes(stop2['arrival_time'])
            
            if tempo1 is not None and tempo2 is not None:
                return max(tempo2 - tempo1, 1)  # Mínimo 1 minuto
        except:
            pass
        
        # Fallback: estimar baseado em velocidade média de ônibus urbano (15 km/h)
        return 5.0  # Tempo padrão entre paradas
    
    def _calcular_frequencia_linha(self, linha_nome: str) -> float:
        """Calcula frequência média de uma linha (minutos entre ônibus)"""
        # Simplificado: retornar frequência padrão
        # Em implementação real, analisar horários do GTFS
        return 15.0  # 15 minutos entre ônibus