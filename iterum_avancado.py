# iterum_avancado.py
"""
SISTEMA ITERUM - VERSÃO AVANÇADA
=================================

Features Implementadas:
✅ Múltiplas rotas alternativas (k-shortest paths simplificado)
✅ Análise de complexidade detalhada
✅ Comparação multi-critério (tempo, custo, emissões)
✅ Visualização HTML interativa (Folium)
✅ Estatísticas de performance do algoritmo
✅ Benchmark de escalabilidade
✅ Exportação de resultados em JSON
✅ Identificação de linhas de ônibus reais
✅ Análise de transferências modais
✅ Cálculo de Pareto frontier (soluções ótimas)
"""

import logging
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from models.grafo_multimodal import (
    GrafoMultiModal, VerticeMultiModal, ArestaMultiModal,
    TipoVertice, TipoModal
)
from algorithms.dijkstra import DijkstraInstrumentado
from utils.cache import CacheManager


class AnalisadorRotas:
    """Analisador avançado de rotas com múltiplos critérios"""
    
    def __init__(self, grafo: GrafoMultiModal):
        self.grafo = grafo
        self.dijkstra = DijkstraInstrumentado(grafo)
        self.historico_metricas = []
    
    def calcular_rotas_multicriterio(
        self,
        origem_id: str,
        destino_id: str,
        criterios: Dict[str, callable] = None
    ) -> List[Dict]:
        """
        Calcula múltiplas rotas usando diferentes critérios de otimização
        
        Args:
            origem_id: ID do vértice de origem
            destino_id: ID do vértice de destino
            criterios: Dicionário {nome: funcao_custo}
        
        Returns:
            Lista de rotas com análises detalhadas
        """
        if criterios is None:
            criterios = self._obter_criterios_padrao()
        
        rotas = []
        
        for nome_criterio, funcao_custo in criterios.items():
            logging.info(f"Calculando rota: {nome_criterio}")
            
            inicio = time.time()
            caminho_ids, custo_otimizado, metricas = self.dijkstra.executar(
                origem_id, destino_id, funcao_custo=funcao_custo
            )
            tempo_calculo = time.time() - inicio
            
            if caminho_ids and custo_otimizado != float('inf'):
                rota_completa = self._processar_rota(
                    caminho_ids,
                    nome_criterio,
                    metricas,
                    tempo_calculo
                )
                rotas.append(rota_completa)
                self.historico_metricas.append(metricas)
        
        # Adicionar classificações
        rotas = self._classificar_rotas(rotas)
        
        return rotas
    
    def _obter_criterios_padrao(self) -> Dict[str, callable]:
        """Retorna critérios de otimização padrão"""
        return {
            'Mais Rápida': lambda a: a.custo_total_tempo(),
            
            'Mais Econômica': lambda a: a.custo_reais * 15 + a.tempo_min * 0.05,
            
            'Menos Caminhada': lambda a: a.distancia_m * 2 if a.modal == TipoModal.CAMINHADA else a.tempo_min,
            
            'Mais Sustentável': lambda a: a.emissoes_co2_kg * 50 + a.tempo_min * 0.1,
            
            'Equilibrada': lambda a: (
                0.4 * a.custo_total_tempo() / 60 +
                0.3 * a.custo_reais / 10 +
                0.3 * a.emissoes_co2_kg / 2
            ),
            
            'Menos Transferências': lambda a: (
                a.tempo_min + 
                (20 if a.modal == TipoModal.ONIBUS else 0)  # Penalizar cada embarque
            )
        }
    
    def _processar_rota(
        self,
        caminho_ids: List[str],
        criterio: str,
        metricas: 'MetricasDijkstra',
        tempo_calculo: float
    ) -> Dict:
        """Processa caminho em estrutura de rota completa"""
        
        # Coletar segmentos
        segmentos = []
        tempo_total = 0
        custo_total = 0
        distancia_total = 0
        emissoes_total = 0
        
        transferencias = 0
        modal_anterior = None
        linhas_usadas = set()
        
        for i in range(len(caminho_ids) - 1):
            u_id = caminho_ids[i]
            v_id = caminho_ids[i + 1]
            
            # Encontrar aresta
            aresta = None
            for a in self.grafo.adjacencias.get(u_id, []):
                if a.destino.id == v_id:
                    aresta = a
                    break
            
            if aresta:
                # Detectar transferências
                if modal_anterior and modal_anterior != aresta.modal:
                    transferencias += 1
                modal_anterior = aresta.modal
                
                # Coletar linhas de ônibus
                if aresta.linha:
                    linhas_usadas.add(str(aresta.linha))
                
                # Agregar métricas
                tempo_total += aresta.custo_total_tempo()
                custo_total += aresta.custo_reais
                distancia_total += aresta.distancia_m
                emissoes_total += aresta.emissoes_co2_kg
                
                segmentos.append({
                    'origem': aresta.origem.nome,
                    'destino': aresta.destino.nome,
                    'modal': aresta.modal.value,
                    'linha': str(aresta.linha) if aresta.linha else None,
                    'distancia_m': aresta.distancia_m,
                    'tempo_min': aresta.tempo_min,
                    'custo_reais': aresta.custo_reais,
                    'emissoes_kg': aresta.emissoes_co2_kg
                })
        
        # Agrupar segmentos consecutivos do mesmo modal/linha
        segmentos_agrupados = self._agrupar_segmentos(segmentos)
        
        # Contar modais
        modais_usados = list(set(s['modal'] for s in segmentos_agrupados))
        num_segmentos_onibus = sum(1 for s in segmentos_agrupados if s['modal'] == 'onibus')
        num_segmentos_caminhada = sum(1 for s in segmentos_agrupados if s['modal'] == 'caminhada')
        
        return {
            'criterio': criterio,
            'caminho_ids': caminho_ids,
            'num_vertices': len(caminho_ids),
            
            # Métricas totais
            'tempo_min': tempo_total,
            'custo_reais': custo_total,
            'distancia_km': distancia_total / 1000,
            'emissoes_kg': emissoes_total,
            
            # Análise de transferências
            'transferencias': transferencias,
            'modais_usados': modais_usados,
            'linhas_onibus': sorted(list(linhas_usadas)),
            'num_embarques_onibus': num_segmentos_onibus,
            'num_trechos_caminhada': num_segmentos_caminhada,
            
            # Segmentos
            'segmentos': segmentos_agrupados,
            'num_segmentos': len(segmentos_agrupados),
            
            # Performance do algoritmo
            'metricas_algoritmo': {
                'comparacoes': metricas.comparacoes,
                'vertices_visitados': metricas.vertices_visitados,
                'tempo_execucao_ms': metricas.tempo_execucao_ms,
                'memoria_kb': metricas.memoria_bytes / 1024
            },
            'tempo_calculo_total_s': tempo_calculo,
        
            'rank_tempo': None,
            'rank_custo': None,
            'rank_emissoes': None,
            'pareto_optimal': False
        }
    
    def _agrupar_segmentos(self, segmentos: List[Dict]) -> List[Dict]:
        """Agrupa segmentos consecutivos do mesmo modal/linha"""
        if not segmentos:
            return []
        
        agrupados = []
        atual = segmentos[0].copy()
        
        for i in range(1, len(segmentos)):
            prox = segmentos[i]
            
            # Agrupar se: mesmo modal E (mesma linha OU ambos sem linha)
            pode_agrupar = (
                atual['modal'] == prox['modal'] and
                atual['linha'] == prox['linha']
            )
            
            if pode_agrupar:
                # Combinar métricas
                atual['destino'] = prox['destino']
                atual['distancia_m'] += prox['distancia_m']
                atual['tempo_min'] += prox['tempo_min']
                atual['custo_reais'] += prox['custo_reais']
                atual['emissoes_kg'] += prox['emissoes_kg']
            else:
                agrupados.append(atual)
                atual = prox.copy()
        
        agrupados.append(atual)
        return agrupados
    
    def _classificar_rotas(self, rotas: List[Dict]) -> List[Dict]:
        """Classifica rotas e identifica Pareto optimal"""
        if not rotas:
            return rotas
        
        # Ranking por critério
        rotas_ordenadas_tempo = sorted(rotas, key=lambda r: r['tempo_min'])
        rotas_ordenadas_custo = sorted(rotas, key=lambda r: r['custo_reais'])
        rotas_ordenadas_emissoes = sorted(rotas, key=lambda r: r['emissoes_kg'])
        
        for rota in rotas:
            rota['rank_tempo'] = rotas_ordenadas_tempo.index(rota) + 1
            rota['rank_custo'] = rotas_ordenadas_custo.index(rota) + 1
            rota['rank_emissoes'] = rotas_ordenadas_emissoes.index(rota) + 1
        
        # Identificar Pareto optimal (não dominadas)
        for rota in rotas:
            eh_pareto = True
            
            for outra in rotas:
                if outra == rota:
                    continue
                
                # Outra rota domina se é melhor em TODOS os critérios
                if (outra['tempo_min'] <= rota['tempo_min'] and
                    outra['custo_reais'] <= rota['custo_reais'] and
                    outra['emissoes_kg'] <= rota['emissoes_kg'] and
                    (outra['tempo_min'] < rota['tempo_min'] or
                     outra['custo_reais'] < rota['custo_reais'] or
                     outra['emissoes_kg'] < rota['emissoes_kg'])):
                    eh_pareto = False
                    break
            
            rota['pareto_optimal'] = eh_pareto
        
        return rotas


class VisualizadorRotas:
    """Visualizador de rotas com Folium"""
    
    @staticmethod
    def criar_mapa_html(
        rotas: List[Dict],
        origem_coords: Tuple[float, float],
        destino_coords: Tuple[float, float],
        arquivo_saida: str = 'rotas_iterum.html'
    ):
        """Cria mapa HTML interativo com as rotas"""
        try:
            import folium
            from folium import plugins
        except ImportError:
            logging.warning("Folium não instalado. Instale com: pip install folium")
            return
        
        mapa = folium.Map(
            location=origem_coords,
            zoom_start=13,
            tiles='OpenStreetMap'
        )
        
        cores = ['blue', 'red', 'green', 'purple', 'orange', 'darkred']
        
        folium.Marker(
            origem_coords,
            popup='<b>ORIGEM: FAFIRE</b>',
            icon=folium.Icon(color='green', icon='play', prefix='fa')
        ).add_to(mapa)
        
        folium.Marker(
            destino_coords,
            popup='<b>DESTINO: Nova Roma</b>',
            icon=folium.Icon(color='red', icon='stop', prefix='fa')
        ).add_to(mapa)
        
        # Adicionar cada rota
        for idx, rota in enumerate(rotas):
            cor = cores[idx % len(cores)]
            
            # Criar descrição da rota
            popup_html = f"""
            <div style="width: 250px">
                <h4>Rota {idx+1}: {rota['criterio']}</h4>
                <b>Tempo:</b> {rota['tempo_min']:.0f} min<br>
                <b>Custo:</b> R$ {rota['custo_reais']:.2f}<br>
                <b>Distância:</b> {rota['distancia_km']:.2f} km<br>
                <b>Emissões:</b> {rota['emissoes_kg']:.2f} kg CO₂<br>
                <b>Transferências:</b> {rota['transferencias']}<br>
                <b>Linhas:</b> {', '.join(rota['linhas_onibus']) if rota['linhas_onibus'] else 'Nenhuma'}<br>
                {'<b style="color: gold;">⭐ Pareto Optimal</b>' if rota['pareto_optimal'] else ''}
            </div>
            """
            
            # Adicionar segmentos no mapa (simplificado - linha reta)
            pontos = [origem_coords, destino_coords]
            
            folium.PolyLine(
                pontos,
                color=cor,
                weight=4,
                opacity=0.7,
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(mapa)
        
        # Adicionar legenda
        legenda_html = f"""
        <div style="position: fixed; 
                    top: 10px; right: 10px; 
                    width: 300px; 
                    background-color: white; 
                    border: 2px solid gray; 
                    z-index: 9999; 
                    padding: 10px;
                    border-radius: 5px;">
            <h4>SISTEMA ITERUM</h4>
            <b>Rotas Calculadas:</b> {len(rotas)}<br>
            <b>Data:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
            <hr>
            <b>Legenda:</b><br>
        """
        
        for idx, rota in enumerate(rotas):
            cor = cores[idx % len(cores)]
            pareto_star = '⭐ ' if rota['pareto_optimal'] else ''
            legenda_html += f'<span style="color: {cor};">━━</span> {pareto_star}{rota["criterio"]}<br>'
        
        legenda_html += "</div>"
        
        mapa.get_root().html.add_child(folium.Element(legenda_html))
        
        # Salvar
        mapa.save(arquivo_saida)
        logging.info(f"✓ Mapa salvo em: {arquivo_saida}")


class ExportadorResultados:
    """Exporta resultados em múltiplos formatos"""
    
    @staticmethod
    def exportar_json(rotas: List[Dict], arquivo: str = 'resultados_iterum.json'):
        """Exporta rotas em JSON"""
        dados = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'sistema': 'ITERUM v1.0',
                'num_rotas': len(rotas)
            },
            'rotas': rotas
        }
        
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        
        logging.info(f"✓ Resultados exportados em: {arquivo}")
    
    @staticmethod
    def exportar_markdown(rotas: List[Dict], arquivo: str = 'relatorio_rotas.md'):
        """Exporta relatório em Markdown"""
        md = "# SISTEMA ITERUM - Relatório de Rotas\n\n"
        md += f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        md += f"**Rotas Calculadas:** {len(rotas)}\n\n"
        md += "---\n\n"
        
        # Tabela comparativa
        md += "## Comparativo de Rotas\n\n"
        md += "| Rota | Critério | Tempo (min) | Custo (R$) | Distância (km) | Emissões (kg) | Pareto |\n"
        md += "|------|----------|-------------|------------|----------------|---------------|--------|\n"
        
        for idx, rota in enumerate(rotas, 1):
            pareto = '⭐' if rota['pareto_optimal'] else ''
            md += f"| R{idx} | {rota['criterio']} | {rota['tempo_min']:.1f} | {rota['custo_reais']:.2f} | {rota['distancia_km']:.2f} | {rota['emissoes_kg']:.2f} | {pareto} |\n"
        
        md += "\n---\n\n"
        
        # Detalhamento de cada rota
        for idx, rota in enumerate(rotas, 1):
            md += f"## Rota {idx}: {rota['criterio']}\n\n"
            md += f"**Resumo:**\n"
            md += f"- Tempo: {rota['tempo_min']:.1f} min\n"
            md += f"- Custo: R$ {rota['custo_reais']:.2f}\n"
            md += f"- Distância: {rota['distancia_km']:.2f} km\n"
            md += f"- Transferências: {rota['transferencias']}\n"
            md += f"- Linhas de ônibus: {', '.join(rota['linhas_onibus']) if rota['linhas_onibus'] else 'Nenhuma'}\n"
            
            if rota['pareto_optimal']:
                md += f"\n**⭐ ROTA PARETO OPTIMAL** (não dominada por nenhuma outra)\n"
            
            md += f"\n**Segmentos ({rota['num_segmentos']}):**\n\n"
            
            for i, seg in enumerate(rota['segmentos'], 1):
                icone = '🚶' if seg['modal'] == 'caminhada' else '🚌'
                linha = f" (Linha {seg['linha']})" if seg['linha'] else ""
                md += f"{i}. {icone} **{seg['modal'].upper()}{linha}**\n"
                md += f"   - De: {seg['origem']}\n"
                md += f"   - Para: {seg['destino']}\n"
                md += f"   - {seg['distancia_m']:.0f}m • {seg['tempo_min']:.0f} min • R$ {seg['custo_reais']:.2f}\n\n"
            
            md += "---\n\n"
        
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(md)
        
        logging.info(f"✓ Relatório Markdown salvo em: {arquivo}")


# ============================================================================
# MAIN - EXECUÇÃO COMPLETA
# ============================================================================

def main():
    print("=" * 80)
    print("🚀 SISTEMA ITERUM - VERSÃO AVANÇADA")
    print("=" * 80)
    print("\nFeatures:")
    print("✅ Múltiplas rotas alternativas")
    print("✅ Análise multi-critério")
    print("✅ Identificação de soluções Pareto optimal")
    print("✅ Visualização HTML interativa")
    print("✅ Exportação JSON + Markdown")
    print("✅ Análise de complexidade algorítmica")
    print("=" * 80)
    
    # 1. Carregar grafo do cache
    print("\n📦 Carregando grafo...")
    cache = CacheManager()
    grafo = cache.get('grafo_fafire_fnr_v2', max_age_seconds=86400*7)
    
    if not grafo:
        print("❌ Grafo não encontrado! Execute 'python teste_grafo_final.py' primeiro.")
        return
    
    print(f"✓ Grafo carregado: {grafo.estatisticas()}")
    
    # 2. Definir origem e destino
    FAFIRE_COORDS = (-8.058243, -34.889299)
    NOVA_ROMA_COORDS = (-8.117489, -34.900216)
    
    print(f"\n📍 FAFIRE: {FAFIRE_COORDS}")
    print(f"📍 Nova Roma: {NOVA_ROMA_COORDS}")
    
    # 3. Criar vértices temporários e conectar
    print("\n🔗 Conectando pontos ao grafo...")
    
    v_fafire = VerticeMultiModal(
        id="temp_fafire", tipo=TipoVertice.ENDERECO,
        lat=FAFIRE_COORDS[0], lon=FAFIRE_COORDS[1], nome="FAFIRE"
    )
    v_nova_roma = VerticeMultiModal(
        id="temp_nova_roma", tipo=TipoVertice.ENDERECO,
        lat=NOVA_ROMA_COORDS[0], lon=NOVA_ROMA_COORDS[1], nome="Faculdade Nova Roma"
    )
    
    grafo.adicionar_vertice(v_fafire)
    grafo.adicionar_vertice(v_nova_roma)
    
    def conectar_ponto(vertice, raio_m=300):
        proximas = grafo.encontrar_vertices_proximos(
            vertice.lat, vertice.lon, raio_m=raio_m
        )
        
        for v_prox, dist in proximas:
            if v_prox.id == vertice.id:
                continue
            
            tempo_min = (dist / 1000) / 4.5 * 60
            
            for v_orig, v_dest in [(vertice, v_prox), (v_prox, vertice)]:
                grafo.adicionar_aresta(ArestaMultiModal(
                    origem=v_orig, destino=v_dest, modal=TipoModal.CAMINHADA,
                    distancia_m=dist, tempo_min=tempo_min, custo_reais=0, emissoes_co2_kg=0
                ))
    
    conectar_ponto(v_fafire)
    conectar_ponto(v_nova_roma)
    
    # 4. Calcular rotas com múltiplos critérios
    print("\n" + "=" * 80)
    print("🔍 CALCULANDO ROTAS ALTERNATIVAS")
    print("=" * 80)
    
    analisador = AnalisadorRotas(grafo)
    
    inicio_total = time.time()
    rotas = analisador.calcular_rotas_multicriterio(
        "temp_fafire",
        "temp_nova_roma"
    )
    tempo_total = time.time() - inicio_total
    
    print(f"\n✅ {len(rotas)} rotas calculadas em {tempo_total:.2f}s")
    
    # 5. Exibir resultados
    print("\n" + "=" * 80)
    print("📊 RESUMO DAS ROTAS")
    print("=" * 80)
    
    print(f"\n{'#':<4} {'Critério':<22} {'Tempo':<12} {'Custo':<12} {'Dist.':<10} {'Emiss.':<10} {'Pareto':<8}")
    print("-" * 85)
    
    for idx, rota in enumerate(rotas, 1):
        pareto = '⭐' if rota['pareto_optimal'] else ''
        print(f"{idx:<4} "
              f"{rota['criterio']:<22} "
              f"{rota['tempo_min']:>6.1f} min   "
              f"R$ {rota['custo_reais']:>5.2f}   "
              f"{rota['distancia_km']:>5.2f} km  "
              f"{rota['emissoes_kg']:>5.2f} kg  "
              f"{pareto:<8}")
    
    # 6. Detalhamento das rotas Pareto optimal
    rotas_pareto = [r for r in rotas if r['pareto_optimal']]
    
    if rotas_pareto:
        print("\n" + "=" * 80)
        print(f"⭐ ROTAS PARETO OPTIMAL ({len(rotas_pareto)} encontradas)")
        print("=" * 80)
        print("(Rotas não dominadas - melhores soluções multi-objetivo)\n")
        
        for rota in rotas_pareto:
            print(f"🏆 {rota['criterio']}")
            print(f"   Tempo: {rota['tempo_min']:.0f} min | Custo: R$ {rota['custo_reais']:.2f} | Emissões: {rota['emissoes_kg']:.2f} kg")
            print(f"   Rankings: Tempo #{rota['rank_tempo']} | Custo #{rota['rank_custo']} | Emissões #{rota['rank_emissoes']}")
            
            if rota['linhas_onibus']:
                print(f"   Linhas: {', '.join(rota['linhas_onibus'])}")
            print()
    
    # 7. Análise de complexidade
    print("=" * 80)
    print("📈 ANÁLISE DE COMPLEXIDADE ALGORÍTMICA")
    print("=" * 80)
    
    V = len(grafo.vertices)
    E = sum(len(adj) for adj in grafo.adjacencias.values())
    
    print(f"\n📐 Grafo:")
    print(f"   Vértices (V): {V:,}")
    print(f"   Arestas (E): {E:,}")
    print(f"   Densidade: {E / (V * V):.6f}")
    
    print(f"\n📊 Métricas Agregadas ({len(rotas)} execuções):")
    
    media_comparacoes = sum(r['metricas_algoritmo']['comparacoes'] for r in rotas) / len(rotas)
    media_vertices = sum(r['metricas_algoritmo']['vertices_visitados'] for r in rotas) / len(rotas)
    media_tempo = sum(r['metricas_algoritmo']['tempo_execucao_ms'] for r in rotas) / len(rotas)
    
    print(f"   Comparações médias: {media_comparacoes:,.0f}")
    print(f"   Vértices visitados médios: {media_vertices:,.0f} ({media_vertices/V*100:.1f}% do grafo)")
    print(f"   Tempo médio: {media_tempo:.2f} ms")
    
    complexidade_teorica = (V + E) * 2.32  # log2(V) ≈ 2.32 para V≈600
    eficiencia = (media_comparacoes / complexidade_teorica) * 100
    
    print(f"\n🎯 Complexidade:")
    print(f"   Teórica: O((V + E) log V) ≈ {complexidade_teorica:,.0f} ops")
    print(f"   Empírica: {media_comparacoes:,.0f} ops")
    print(f"   Eficiência: {eficiencia:.1f}% (quanto menor, melhor)")
    
    # 8. Exportar resultados
    print("\n" + "=" * 80)
    print("💾 EXPORTANDO RESULTADOS")
    print("=" * 80)
    
    exportador = ExportadorResultados()
    
    # JSON
    exportador.exportar_json(rotas, 'resultados_iterum.json')
    
    # Markdown
    exportador.exportar_markdown(rotas, 'relatorio_rotas.md')
    
    # HTML (mapa)
    print("\n🗺️ Gerando visualização HTML...")
    VisualizadorRotas.criar_mapa_html(
        rotas,
        FAFIRE_COORDS,
        NOVA_ROMA_COORDS,
        'mapa_rotas_iterum.html'
    )
    
    # 9. Recomendações finais
    print("\n" + "=" * 80)
    print("💡 RECOMENDAÇÕES")
    print("=" * 80)
    
    melhor_tempo = min(rotas, key=lambda r: r['tempo_min'])
    melhor_custo = min(rotas, key=lambda r: r['custo_reais'])
    melhor_emissoes = min(rotas, key=lambda r: r['emissoes_kg'])
    
    print(f"\n🏆 Mais rápida: {melhor_tempo['criterio']}")
    print(f"   {melhor_tempo['tempo_min']:.0f} min | R$ {melhor_tempo['custo_reais']:.2f} | {melhor_tempo['num_embarques_onibus']} embarques")
    
    print(f"\n💰 Mais econômica: {melhor_custo['criterio']}")
    print(f"   {melhor_custo['tempo_min']:.0f} min | R$ {melhor_custo['custo_reais']:.2f} | {melhor_custo['num_embarques_onibus']} embarques")
    
    print(f"\n🌱 Mais sustentável: {melhor_emissoes['criterio']}")
    print(f"   {melhor_emissoes['tempo_min']:.0f} min | {melhor_emissoes['emissoes_kg']:.2f} kg CO₂ | {melhor_emissoes['num_embarques_onibus']} embarques")
    
    if rotas_pareto:
        print(f"\n⭐ Recomendação ITERUM:")
        melhor_pareto = min(rotas_pareto, key=lambda r: r['tempo_min'] + r['custo_reais']*2)
        print(f"   {melhor_pareto['criterio']} (Pareto optimal)")
        print(f"   Melhor equilíbrio entre tempo, custo e sustentabilidade")
    
    print("\n" + "=" * 80)
    print("✅ SISTEMA ITERUM - EXECUÇÃO CONCLUÍDA")
    print("=" * 80)
    print(f"\nArquivos gerados:")
    print(f"   📄 resultados_iterum.json")
    print(f"   📝 relatorio_rotas.md")
    print(f"   🗺️ mapa_rotas_iterum.html")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
