# salvar_grafo_cache.py
from models.grafo_multimodal import GrafoMultiModal
from utils.cache import CacheManager
import pickle

print("Carregando grafo construído...")

# Se você já tem o grafo na memória, use ele
# Caso contrário, reconstrua (mas só uma vez)

# OPÇÃO 1: Salvar o grafo atual em pickle diretamente
grafo_atual = None  # Cole aqui a referência ao grafo se tiver

# OPÇÃO 2: Usar o CacheManager
cache = CacheManager()

# Como você já construiu o grafo, vamos salvar manualmente
# Execute o teste_grafo.py novamente MAS modifique para salvar:

print("""
INSTRUÇÕES:
1. Modifique seu teste_grafo.py
2. Adicione ANTES da linha "print('✓ Grafo construído com sucesso!')":

   # Salvar no cache
   from utils.cache import CacheManager
   cache = CacheManager()
   cache.set('grafo_fafire_fnr_completo', grafo)
   print("💾 Grafo salvo no cache!")

3. Na próxima vez, carregue assim:
   
   cache = CacheManager()
   grafo = cache.get('grafo_fafire_fnr_completo', max_age_seconds=86400*7)
   
   if grafo:
       print("✓ Carregado do cache em 2 segundos!")
   else:
       print("Reconstruindo grafo...")
""")
