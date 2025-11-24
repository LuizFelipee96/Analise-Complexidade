from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class MetricasDijkstra:
    """Métricas de performance do algoritmo de Dijkstra"""
    comparacoes: int = 0
    insercoes_fila: int = 0
    atualizacoes_distancia: int = 0
    vertices_visitados: int = 0
    tempo_execucao_ms: float = 0.0
    memoria_bytes: int = 0
    
    def __str__(self):
        return f"""
        Métricas de Execução:
        - Comparações: {self.comparacoes:,}
        - Inserções na fila: {self.insercoes_fila:,}
        - Atualizações de distância: {self.atualizacoes_distancia:,}
        - Vértices visitados: {self.vertices_visitados:,}
        - Tempo de execução: {self.tempo_execucao_ms:.2f} ms
        - Memória utilizada: {self.memoria_bytes / 1024:.2f} KB
        """

@dataclass
class SegmentoRota:
    """Representa um segmento de uma rota multi-modal"""
    tipo_modal: str 
    origem: str
    destino: str
    origem_coords: tuple
    destino_coords: tuple
    distancia_m: float
    tempo_min: float
    custo_reais: float
    emissoes_co2_kg: float
    
    linha: Optional[str] = None
    horario_partida: Optional[datetime] = None
    horario_chegada: Optional[datetime] = None
    tempo_espera_min: Optional[float] = None
    
    instrucoes: List[str] = field(default_factory=list)
    
    def __str__(self):
        if self.tipo_modal == 'onibus':
            return f"{self.tipo_modal.upper()} {self.linha}: {self.origem} → {self.destino} ({self.tempo_min:.0f} min, R$ {self.custo_reais:.2f})"
        return f"{self.tipo_modal.upper()}: {self.origem} → {self.destino} ({self.tempo_min:.0f} min, {self.distancia_m:.0f}m)"

@dataclass
class RotaCompleta:
    """Representa uma rota completa multi-modal"""
    id_rota: str
    origem: str
    destino: str
    segmentos: List[SegmentoRota]
    
    # Totais
    distancia_total_km: float
    tempo_total_min: float
    custo_total_reais: float
    emissoes_totais_kg: float
    
    numero_transferencias: int
    modais_utilizados: List[str]
    score_multiobjetivo: float
    
    melhor_para: str 
    
    timestamp_calculo: datetime
    metricas_algoritmo: Optional[MetricasDijkstra] = None
    
    def __str__(self):
        return f"""
        Rota {self.id_rota}: {self.origem} → {self.destino}
        ============================================================
        Tempo total: {self.tempo_total_min:.1f} min
        Custo total: R$ {self.custo_total_reais:.2f}
        Distância: {self.distancia_total_km:.2f} km
        Emissões CO₂: {self.emissoes_totais_kg:.2f} kg
        Transferências: {self.numero_transferencias}
        Modais: {', '.join(self.modais_utilizados)}
        Score: {self.score_multiobjetivo:.4f}
        Melhor para: {self.melhor_para}
        """