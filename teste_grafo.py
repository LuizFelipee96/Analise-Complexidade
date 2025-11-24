# teste_grafo_final.py
from parsers.gtfs_parser import GTFSParser
from models.grafo_multimodal import GrafoMultiModal
from utils.cache import CacheManager
import time

print("=" * 80)
print("TESTE: CONSTRUÇÃO DO GRAFO MULTI-MODAL")
print("=" * 80)

# Usar cache
cache = CacheManager()
cache_key = 'grafo_fafire_fnr_v2'

grafo = cache.get(cache_key, max_age_seconds=86400*7)  # 7 dias

if grafo:
    print("\n✓ Grafo carregado do CACHE (instantâneo!)")
else:
    print("\n📦 Construindo grafo (primeira vez, ~11 min)...")
    
    grafo = GrafoMultiModal()
    parser = GTFSParser('./data/gtfs/')
    parser.carregar_dados()
    
    bbox_fafire_fnr = (-8.130, -34.920, -8.050, -34.880)
    
    inicio = time.time()
    parser.popular_grafo(grafo, regiao_bbox=bbox_fafire_fnr)
    tempo_construcao = time.time() - inicio
    
    # SALVAR NO CACHE
    cache.set(cache_key, grafo)
    print(f"\n💾 Grafo salvo no cache! (levou {tempo_construcao:.1f}s)")

# Estatísticas
print("\n" + "=" * 80)
print("ESTATÍSTICAS DO GRAFO")
print("=" * 80)

stats = grafo.estatisticas()
print(f"\n📊 Resumo:")
print(f"   Vértices: {stats['total_vertices']:,}")
print(f"   Arestas: {stats['total_arestas']:,}")

print(f"\n🚏 Tipos de Vértices:")
for tipo, count in stats['tipos_vertices'].items():
    print(f"   {tipo}: {count:,}")

print(f"\n🚌 Modais Disponíveis:")
for modal, count in stats['modais'].items():
    print(f"   {modal}: {count:,} conexões")

# Paradas próximas
print("\n" + "=" * 80)
print("PARADAS PRÓXIMAS AOS PONTOS DE INTERESSE")
print("=" * 80)

FAFIRE = (-8.058243, -34.889299)
NOVA_ROMA = (-8.117489, -34.900216)

print(f"\n📍 FAFIRE: {FAFIRE}")
proximas_fafire = grafo.encontrar_vertices_proximos(
    FAFIRE[0], FAFIRE[1], 
    raio_m=500
)
print(f"   Paradas num raio de 500m: {len(proximas_fafire)}")
for vertice, dist in proximas_fafire[:5]:
    print(f"   - {vertice.nome} ({dist:.0f}m)")
    if vertice.linhas_onibus:
        # CORREÇÃO: Converter para string
        linhas_str = [str(linha) for linha in vertice.linhas_onibus[:5]]
        print(f"     Linhas: {', '.join(linhas_str)}")

print(f"\n📍 NOVA ROMA: {NOVA_ROMA}")
proximas_fnr = grafo.encontrar_vertices_proximos(
    NOVA_ROMA[0], NOVA_ROMA[1],
    raio_m=500
)
print(f"   Paradas num raio de 500m: {len(proximas_fnr)}")
for vertice, dist in proximas_fnr[:5]:
    print(f"   - {vertice.nome} ({dist:.0f}m)")
    if vertice.linhas_onibus:
        linhas_str = [str(linha) for linha in vertice.linhas_onibus[:5]]
        print(f"     Linhas: {', '.join(linhas_str)}")

print("\n" + "=" * 80)
print("✓ TESTE CONCLUÍDO!")
print("=" * 80)
