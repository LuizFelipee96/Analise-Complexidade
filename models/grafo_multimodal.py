from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from enum import Enum
import math

class TipoVertice(Enum):
    """Tipos de vértices no grafo multi-modal"""
    ENDERECO = "endereco"
    PARADA_ONIBUS = "parada_onibus"
    ESTACAO_METRO = "estacao_metro"
    CRUZAMENTO = "cruzamento"
    ESTACAO_BIKE = "estacao_bike"

class TipoModal(Enum):
    """Tipos de modais de transporte"""
    CAMINHADA = "caminhada"
    ONIBUS = "onibus"
    METRO = "metro"
    UBER_CARRO = "uber_carro"
    UBER_MOTO = "uber_moto"
    BICICLETA = "bicicleta"

@dataclass
class VerticeMultiModal:
    """Vértice no grafo multi-modal"""
    id: str
    tipo: TipoVertice
    lat: float
    lon: float
    nome: str
    
    # Dados específicos de transporte público
    linhas_onibus: List[str] = field(default_factory=list)
    linha_metro: Optional[str] = None
    
    # Amenidades
    tem_abrigo: bool = False
    tem_acessibilidade: bool = False
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, VerticeMultiModal):
            return self.id == other.id
        return False
    
    def distancia_para(self, outro: 'VerticeMultiModal') -> float:
        """Calcula distância euclidiana em metros"""
        lat1, lon1 = math.radians(self.lat), math.radians(self.lon)
        lat2, lon2 = math.radians(outro.lat), math.radians(outro.lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        raio_terra_m = 6371000
        return raio_terra_m * c

@dataclass
class ArestaMultiModal:
    """Aresta no grafo multi-modal"""
    origem: VerticeMultiModal
    destino: VerticeMultiModal
    modal: TipoModal
    
    # Custos
    distancia_m: float
    tempo_min: float
    custo_reais: float
    emissoes_co2_kg: float
    
    linha: Optional[str] = None
    frequencia_min: Optional[float] = None  # Tempo médio entre ônibus/metrôs
    
    # Penalidades
    penalidade_tempo: float = 0.0  # Ex: tempo de espera
    
    def custo_total_tempo(self) -> float:
        """Retorna tempo total incluindo penalidades"""
        return self.tempo_min + self.penalidade_tempo
    
    def __repr__(self):
        return f"{self.origem.nome} --[{self.modal.value}]--> {self.destino.nome}"

class GrafoMultiModal:
    """Grafo multi-modal para roteamento urbano"""
    
    def __init__(self):
        self.vertices: Dict[str, VerticeMultiModal] = {}
        self.adjacencias: Dict[str, List[ArestaMultiModal]] = {}
        self._indice_espacial: Dict[Tuple[int, int], Set[str]] = {}  # Grid para busca espacial
        
    def adicionar_vertice(self, vertice: VerticeMultiModal):
        """Adiciona um vértice ao grafo"""
        self.vertices[vertice.id] = vertice
        if vertice.id not in self.adjacencias:
            self.adjacencias[vertice.id] = []
        
        # Adicionar ao índice espacial (grid de 0.001° ~111m)
        grid_x = int(vertice.lat / 0.001)
        grid_y = int(vertice.lon / 0.001)
        grid_key = (grid_x, grid_y)
        
        if grid_key not in self._indice_espacial:
            self._indice_espacial[grid_key] = set()
        self._indice_espacial[grid_key].add(vertice.id)
    
    def adicionar_aresta(self, aresta: ArestaMultiModal):
        """Adiciona uma aresta ao grafo"""
        if aresta.origem.id not in self.vertices:
            self.adicionar_vertice(aresta.origem)
        if aresta.destino.id not in self.vertices:
            self.adicionar_vertice(aresta.destino)
        
        self.adjacencias[aresta.origem.id].append(aresta)
    
    def encontrar_vertices_proximos(
        self, 
        lat: float, 
        lon: float, 
        raio_m: float = 500,
        tipo_vertice: Optional[TipoVertice] = None
    ) -> List[Tuple[VerticeMultiModal, float]]:
        """
        Encontra vértices próximos a uma coordenada
        
        Returns:
            Lista de tuplas (vertice, distancia_m) ordenada por distância
        """
        # Criar vértice temporário para cálculo de distância
        temp_vertice = VerticeMultiModal(
            id="temp",
            tipo=TipoVertice.ENDERECO,
            lat=lat,
            lon=lon,
            nome="Temp"
        )
        
        # Buscar no grid espacial
        grid_x = int(lat / 0.001)
        grid_y = int(lon / 0.001)
        grid_raio = int(raio_m / 111) + 1  # ~111m por 0.001°
        
        candidatos = set()
        for dx in range(-grid_raio, grid_raio + 1):
            for dy in range(-grid_raio, grid_raio + 1):
                grid_key = (grid_x + dx, grid_y + dy)
                if grid_key in self._indice_espacial:
                    candidatos.update(self._indice_espacial[grid_key])
        
        resultados = []
        for vertice_id in candidatos:
            vertice = self.vertices[vertice_id]
            
            if tipo_vertice and vertice.tipo != tipo_vertice:
                continue
            
            distancia = temp_vertice.distancia_para(vertice)
            if distancia <= raio_m:
                resultados.append((vertice, distancia))
        
        # Ordenar por distância
        resultados.sort(key=lambda x: x[1])
        return resultados
    
    def adicionar_arestas_caminhada(self, raio_m: float = 500):
        """
        Adiciona arestas de caminhada entre vértices próximos
        
        Args:
            raio_m: Raio máximo para conectar vértices a pé
        """
        velocidade_caminhada_kmh = 4.5
        emissoes_caminhada = 0.0  # Sem emissões
        
        for vertice_id, vertice in self.vertices.items():
            proximos = self.encontrar_vertices_proximos(
                vertice.lat,
                vertice.lon,
                raio_m
            )
            
            for proximo_vertice, distancia_m in proximos:
                if proximo_vertice.id == vertice.id:
                    continue
                
                # Verificar se já existe aresta
                ja_existe = any(
                    a.destino.id == proximo_vertice.id and a.modal == TipoModal.CAMINHADA
                    for a in self.adjacencias[vertice_id]
                )
                
                if not ja_existe:
                    tempo_min = (distancia_m / 1000) / velocidade_caminhada_kmh * 60
                    
                    aresta = ArestaMultiModal(
                        origem=vertice,
                        destino=proximo_vertice,
                        modal=TipoModal.CAMINHADA,
                        distancia_m=distancia_m,
                        tempo_min=tempo_min,
                        custo_reais=0.0,
                        emissoes_co2_kg=emissoes_caminhada
                    )
                    
                    self.adicionar_aresta(aresta)
    
    def estatisticas(self) -> Dict:
        """Retorna estatísticas do grafo"""
        total_arestas = sum(len(adj) for adj in self.adjacencias.values())
        
        modais_count = {}
        for arestas in self.adjacencias.values():
            for aresta in arestas:
                modal = aresta.modal.value
                modais_count[modal] = modais_count.get(modal, 0) + 1
        
        tipos_vertices = {}
        for vertice in self.vertices.values():
            tipo = vertice.tipo.value
            tipos_vertices[tipo] = tipos_vertices.get(tipo, 0) + 1
        
        return {
            'total_vertices': len(self.vertices),
            'total_arestas': total_arestas,
            'densidade': total_arestas / (len(self.vertices) ** 2) if len(self.vertices) > 0 else 0,
            'tipos_vertices': tipos_vertices,
            'modais': modais_count
        }
    
    def __repr__(self):
        stats = self.estatisticas()
        return f"GrafoMultiModal(V={stats['total_vertices']}, E={stats['total_arestas']}, densidade={stats['densidade']:.4f})"