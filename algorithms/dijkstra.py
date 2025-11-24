import heapq
import time
import sys
from typing import Dict, List, Tuple, Optional, Callable
from collections import defaultdict

from models.grafo_multimodal import GrafoMultiModal, VerticeMultiModal, ArestaMultiModal
from models.metricas import MetricasDijkstra

class DijkstraInstrumentado:
    """Implementação do algoritmo de Dijkstra com instrumentação para análise de complexidade"""
    
    def __init__(self, grafo: GrafoMultiModal):
        self.grafo = grafo
        self.metricas = MetricasDijkstra()
    
    def executar(
        self,
        origem_id: str,
        destino_id: str,
        funcao_custo: Callable[[ArestaMultiModal], float] = None
    ) -> Tuple[List[str], float, MetricasDijkstra]:
        """
        Executa o algoritmo de Dijkstra com instrumentação
        
        Args:
            origem_id: ID do vértice de origem
            destino_id: ID do vértice de destino
            funcao_custo: Função para calcular custo de uma aresta
                         Por padrão usa tempo total
        
        Returns:
            Tupla (caminho, custo_total, metricas)
        """
        # Reset métricas
        self.metricas = MetricasDijkstra()
        inicio = time.time()
        
        # Função de custo padrão: tempo total
        if funcao_custo is None:
            funcao_custo = lambda aresta: aresta.custo_total_tempo()
        
        # Validar vértices
        if origem_id not in self.grafo.vertices:
            raise ValueError(f"Vértice de origem '{origem_id}' não encontrado")
        if destino_id not in self.grafo.vertices:
            raise ValueError(f"Vértice de destino '{destino_id}' não encontrado")
        
        # Estruturas de dados
        distancias = defaultdict(lambda: float('inf'))
        distancias[origem_id] = 0
        predecessores: Dict[str, Tuple[str, ArestaMultiModal]] = {}
        visitados: Set[str] = set()
        
        # Fila de prioridade: (distancia, vertice_id)
        fila = [(0, origem_id)]
        heapq.heapify(fila)
        self.metricas.insercoes_fila += 1
        
        # Calcular memória inicial
        self.metricas.memoria_bytes = (
            sys.getsizeof(distancias) +
            sys.getsizeof(predecessores) +
            sys.getsizeof(visitados) +
            sys.getsizeof(fila)
        )
        
        # Algoritmo de Dijkstra
        while fila:
            dist_atual, u = heapq.heappop(fila)
            self.metricas.comparacoes += 1
            
            # Se já visitou, ignora
            if u in visitados:
                continue
            
            # Marca como visitado
            visitados.add(u)
            self.metricas.vertices_visitados += 1
            
            # Se chegou no destino, pode parar
            if u == destino_id:
                break
            
            # Explorar vizinhos
            for aresta in self.grafo.adjacencias.get(u, []):
                v = aresta.destino.id
                self.metricas.comparacoes += 1
                
                if v not in visitados:
                    # Calcular nova distância
                    custo_aresta = funcao_custo(aresta)
                    nova_dist = distancias[u] + custo_aresta
                    
                    # Relaxamento
                    if nova_dist < distancias[v]:
                        self.metricas.atualizacoes_distancia += 1
                        distancias[v] = nova_dist
                        predecessores[v] = (u, aresta)
                        heapq.heappush(fila, (nova_dist, v))
                        self.metricas.insercoes_fila += 1
        
        # Reconstruir caminho
        caminho = []
        arestas_caminho = []
        
        if destino_id not in predecessores and destino_id != origem_id:
            # Não há caminho
            self.metricas.tempo_execucao_ms = (time.time() - inicio) * 1000
            return ([], float('inf'), self.metricas)
        
        atual = destino_id
        while atual != origem_id:
            caminho.append(atual)
            if atual in predecessores:
                anterior, aresta = predecessores[atual]
                arestas_caminho.append(aresta)
                atual = anterior
            else:
                break
        
        caminho.append(origem_id)
        caminho.reverse()
        arestas_caminho.reverse()
        
        # Tempo de execução
        self.metricas.tempo_execucao_ms = (time.time() - inicio) * 1000
        
        return (caminho, distancias[destino_id], self.metricas)
    
    def k_caminhos_mais_curtos(
        self,
        origem_id: str,
        destino_id: str,
        k: int = 3,
        funcao_custo: Callable[[ArestaMultiModal], float] = None
    ) -> List[Tuple[List[str], float]]:
        """
        Encontra os k caminhos mais curtos (algoritmo de Yen simplificado)
        
        Returns:
            Lista de tuplas (caminho, custo) ordenada por custo
        """
        if funcao_custo is None:
            funcao_custo = lambda aresta: aresta.custo_total_tempo()
        
        # Primeiro caminho: Dijkstra padrão
        caminho_inicial, custo_inicial, _ = self.executar(origem_id, destino_id, funcao_custo)
        
        if not caminho_inicial:
            return []
        
        caminhos = [(caminho_inicial, custo_inicial)]
        candidatos = []
        
        # Encontrar k-1 caminhos adicionais
        for k_iter in range(1, k):
            for i in range(len(caminhos[-1][0]) - 1):
                # Spur node e root path
                spur_node = caminhos[-1][0][i]
                root_path = caminhos[-1][0][:i+1]
                
                # Remover arestas temporariamente
                arestas_removidas = []
                
                for caminho, _ in caminhos:
                    if len(caminho) > i and caminho[:i+1] == root_path:
                        if i + 1 < len(caminho):
                            u, v = caminho[i], caminho[i+1]
                            # Remover aresta u->v
                            for idx, aresta in enumerate(self.grafo.adjacencias[u]):
                                if aresta.destino.id == v:
                                    arestas_removidas.append((u, idx, aresta))
                                    break
                
                # Remover temporariamente
                for u, idx, aresta in arestas_removidas:
                    self.grafo.adjacencias[u].remove(aresta)
                
                # Calcular caminho alternativo
                try:
                    spur_path, spur_custo, _ = self.executar(spur_node, destino_id, funcao_custo)
                    
                    if spur_path:
                        # Combinar root + spur
                        total_path = root_path[:-1] + spur_path
                        total_custo = spur_custo + sum(
                            funcao_custo(pred[1]) 
                            for node in root_path[:-1] 
                            if node in [c[0] for c in candidatos]
                        )
                        
                        if (total_path, total_custo) not in candidatos:
                            candidatos.append((total_path, total_custo))
                except:
                    pass
                
                # Restaurar arestas
                for u, idx, aresta in arestas_removidas:
                    self.grafo.adjacencias[u].append(aresta)
            
            if not candidatos:
                break
            
            # Adicionar melhor candidato
            candidatos.sort(key=lambda x: x[1])
            caminhos.append(candidatos.pop(0))
        
        return caminhos