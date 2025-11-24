# dashboard_visual.py (CORRIGIDO E COMPLETO)
"""
SISTEMA ITERUM - DASHBOARD VISUAL INTERATIVO
=============================================

Cria um dashboard HTML completo com:
✅ Mapa interativo com todas as rotas
✅ Gráficos de comparação (tempo, custo, emissões)
✅ Tabela interativa de rotas
✅ Análise Pareto visual
✅ Detalhamento de cada rota
✅ Estatísticas do algoritmo
"""

import json
import os
from datetime import datetime
from typing import Tuple


class DashboardVisualIterum:
    """Gerador de dashboard HTML interativo"""
    
    def __init__(self):
        self.rotas = []
        self.origem_coords = None
        self.destino_coords = None
        self.origem_nome = ""
        self.destino_nome = ""
    
    def carregar_dados(self, arquivo_json: str = 'resultados_iterum.json'):
        """Carrega dados do JSON gerado"""
        if not os.path.exists(arquivo_json):
            print(f"❌ Arquivo {arquivo_json} não encontrado!")
            return None
        
        with open(arquivo_json, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            self.rotas = dados['rotas']
        
        print(f"✅ {len(self.rotas)} rotas carregadas")
        return self
    
    def definir_origem_destino(
        self,
        origem_coords: Tuple[float, float],
        destino_coords: Tuple[float, float],
        origem_nome: str = "FAFIRE",
        destino_nome: str = "Faculdade Nova Roma"
    ):
        """Define coordenadas de origem e destino"""
        self.origem_coords = origem_coords
        self.destino_coords = destino_coords
        self.origem_nome = origem_nome
        self.destino_nome = destino_nome
        return self
    
    def gerar_dashboard(self, arquivo_saida: str = 'dashboard_iterum.html'):
        """Gera dashboard HTML completo"""
        
        html = self._gerar_html_base()
        
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ Dashboard gerado: {arquivo_saida}")
        return arquivo_saida
    
    def _gerar_html_base(self) -> str:
        """Gera HTML completo do dashboard"""
        
        # Preparar dados
        rotas_json = json.dumps(self.rotas, ensure_ascii=False, indent=2)
        origem_coords_json = json.dumps(list(self.origem_coords))
        destino_coords_json = json.dumps(list(self.destino_coords))
        
        # Estatísticas
        num_rotas = len(self.rotas)
        num_pareto = sum(1 for r in self.rotas if r.get('pareto_optimal', False))
        menor_tempo = min(r['tempo_min'] for r in self.rotas) if self.rotas else 0
        menor_custo = min(r['custo_reais'] for r in self.rotas) if self.rotas else 0
        
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ITERUM Dashboard - Análise de Rotas</title>
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" 
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" 
          crossorigin=""/>
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
    
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            text-align: center;
        }}
        
        h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        
        .card h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .stat-card {{
            text-align: center;
            padding: 20px;
        }}
        
        .stat-value {{
            font-size: 3em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 1.1em;
        }}
        
        #map {{
            height: 600px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 20px 0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        
        th {{
            background: #667eea;
            color: white;
            font-weight: bold;
        }}
        
        tr:hover {{
            background: #f5f5f5;
        }}
        
        .pareto-badge {{
            background: gold;
            color: #333;
            padding: 4px 8px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        
        .route-btn {{
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .route-btn:hover {{
            background: #5568d3;
            transform: translateY(-2px);
        }}
        
        .route-detail {{
            display: none;
            margin-top: 15px;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 10px;
        }}
        
        .route-detail.active {{
            display: block;
        }}
        
        .segment {{
            padding: 15px;
            margin: 10px 0;
            background: white;
            border-left: 4px solid #667eea;
            border-radius: 5px;
        }}
        
        .segment-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .segment-icon {{
            font-size: 1.5em;
        }}
        
        .segment-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 10px;
            font-size: 0.9em;
            color: #666;
        }}
        
        .legend {{
            background: white;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 5px 0;
        }}
        
        .legend-color {{
            width: 30px;
            height: 4px;
            border-radius: 2px;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1><i class="fas fa-route"></i> SISTEMA ITERUM</h1>
            <p class="subtitle">Análise Multi-Modal de Rotas Urbanas - Recife/PE</p>
            <p style="margin-top: 10px; color: #999;">
                <i class="far fa-calendar"></i> {datetime.now().strftime('%d/%m/%Y %H:%M')}
            </p>
        </header>
        
        <!-- Estatísticas Rápidas -->
        <div class="grid">
            <div class="card stat-card">
                <i class="fas fa-route" style="font-size: 2em; color: #667eea;"></i>
                <div class="stat-value">{num_rotas}</div>
                <div class="stat-label">Rotas Calculadas</div>
            </div>
            
            <div class="card stat-card">
                <i class="fas fa-star" style="font-size: 2em; color: gold;"></i>
                <div class="stat-value">{num_pareto}</div>
                <div class="stat-label">Pareto Optimal</div>
            </div>
            
            <div class="card stat-card">
                <i class="fas fa-clock" style="font-size: 2em; color: #667eea;"></i>
                <div class="stat-value">{menor_tempo:.0f}</div>
                <div class="stat-label">Menor Tempo (min)</div>
            </div>
            
            <div class="card stat-card">
                <i class="fas fa-dollar-sign" style="font-size: 2em; color: #667eea;"></i>
                <div class="stat-value">{menor_custo:.2f}</div>
                <div class="stat-label">Menor Custo (R$)</div>
            </div>
        </div>
        
        <!-- Mapa -->
        <div class="card">
            <h2><i class="fas fa-map-marked-alt"></i> Visualização de Rotas</h2>
            <div id="map"></div>
            <div class="legend">
                <h3>Legenda</h3>
                <div id="legend-items"></div>
            </div>
        </div>
        
        <!-- Gráficos -->
        <div class="grid">
            <div class="card">
                <h2><i class="fas fa-chart-bar"></i> Comparação de Tempo</h2>
                <div class="chart-container">
                    <canvas id="tempoChart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <h2><i class="fas fa-chart-pie"></i> Comparação de Custo</h2>
                <div class="chart-container">
                    <canvas id="custoChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2><i class="fas fa-chart-line"></i> Análise Multi-Critério</h2>
            <div class="chart-container">
                <canvas id="multiChart"></canvas>
            </div>
        </div>
        
        <!-- Tabela de Rotas -->
        <div class="card">
            <h2><i class="fas fa-table"></i> Rotas Detalhadas</h2>
            <table id="routesTable">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Critério</th>
                        <th>Tempo</th>
                        <th>Custo</th>
                        <th>Distância</th>
                        <th>Emissões</th>
                        <th>Pareto</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody id="routesTableBody"></tbody>
            </table>
            
            <div id="routeDetails"></div>
        </div>
        
        <footer class="footer">
            <p><strong>SISTEMA ITERUM</strong> - Otimização de Rotas Multi-Modais</p>
            <p>Desenvolvido para análise acadêmica de mobilidade urbana</p>
        </footer>
    </div>
    
    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
            crossorigin=""></script>
    
    <script>
        console.log('🚀 Iniciando ITERUM Dashboard...');
        
        // Dados das rotas
        const rotas = {rotas_json};
        const origemCoords = {origem_coords_json};
        const destinoCoords = {destino_coords_json};
        
        console.log(`✅ ${{rotas.length}} rotas carregadas`);
        
        // Cores para as rotas
        const cores = ['#3388ff', '#ff3333', '#33ff33', '#ff33ff', '#ffaa00', '#00ffff'];
        
        // ===== MAPA =====
        console.log('🗺️ Criando mapa...');
        const map = L.map('map').setView(origemCoords, 13);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        // Marcador de origem
        L.marker(origemCoords).addTo(map)
            .bindPopup('<b>{self.origem_nome}</b>')
            .openPopup();
        
        // Marcador de destino
        L.marker(destinoCoords).addTo(map)
            .bindPopup('<b>{self.destino_nome}</b>');
        
        // Adicionar rotas (linhas retas - simplificado)
        rotas.forEach((rota, idx) => {{
            const cor = cores[idx % cores.length];
            
            const pontos = [origemCoords, destinoCoords];
            
            const popupContent = `
                <div style="max-width: 250px;">
                    <h3 style="color: ${{cor}};">Rota ${{idx + 1}}: ${{rota.criterio}}</h3>
                    <p><strong>Tempo:</strong> ${{rota.tempo_min.toFixed(0)}} min</p>
                    <p><strong>Custo:</strong> R$ ${{rota.custo_reais.toFixed(2)}}</p>
                    <p><strong>Distância:</strong> ${{rota.distancia_km.toFixed(2)}} km</p>
                    <p><strong>Emissões:</strong> ${{rota.emissoes_kg.toFixed(2)}} kg CO₂</p>
                    ${{rota.pareto_optimal ? '<p style="color: gold; font-weight: bold;">⭐ Pareto Optimal</p>' : ''}}
                </div>
            `;
            
            L.polyline(pontos, {{
                color: cor,
                weight: 4,
                opacity: 0.7
            }}).addTo(map).bindPopup(popupContent);
            
            // Adicionar à legenda
            document.getElementById('legend-items').innerHTML += `
                <div class="legend-item">
                    <div class="legend-color" style="background: ${{cor}};"></div>
                    <span>${{rota.pareto_optimal ? '⭐ ' : ''}}Rota ${{idx + 1}}: ${{rota.criterio}}</span>
                </div>
            `;
        }});
        
        console.log('✅ Mapa criado');
        
        // ===== GRÁFICOS =====
        console.log('📊 Criando gráficos...');
        
        // Gráfico de Tempo
        new Chart(document.getElementById('tempoChart'), {{
            type: 'bar',
            data: {{
                labels: rotas.map((r, i) => `R${{i+1}}`),
                datasets: [{{
                    label: 'Tempo (min)',
                    data: rotas.map(r => r.tempo_min),
                    backgroundColor: cores,
                    borderColor: cores,
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});
        
        // Gráfico de Custo
        new Chart(document.getElementById('custoChart'), {{
            type: 'doughnut',
            data: {{
                labels: rotas.map((r, i) => `R${{i+1}}: ${{r.criterio}}`),
                datasets: [{{
                    data: rotas.map(r => r.custo_reais),
                    backgroundColor: cores
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false
            }}
        }});
        
        // Gráfico Multi-Critério (Radar)
        new Chart(document.getElementById('multiChart'), {{
            type: 'radar',
            data: {{
                labels: ['Tempo', 'Custo', 'Distância', 'Emissões', 'Transferências'],
                datasets: rotas.slice(0, 4).map((rota, idx) => ({{
                    label: `R${{idx+1}}: ${{rota.criterio}}`,
                    data: [
                        rota.tempo_min / 100,
                        rota.custo_reais / 10,
                        rota.distancia_km,
                        rota.emissoes_kg * 10,
                        rota.transferencias
                    ],
                    backgroundColor: cores[idx] + '33',
                    borderColor: cores[idx],
                    borderWidth: 2
                }})))
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    r: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
        
        console.log('✅ Gráficos criados');
        
        // ===== TABELA =====
        console.log('📋 Criando tabela...');
        const tableBody = document.getElementById('routesTableBody');
        
        rotas.forEach((rota, idx) => {{
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${{idx + 1}}</td>
                <td>${{rota.criterio}}</td>
                <td>${{rota.tempo_min.toFixed(1)}} min</td>
                <td>R$ ${{rota.custo_reais.toFixed(2)}}</td>
                <td>${{rota.distancia_km.toFixed(2)}} km</td>
                <td>${{rota.emissoes_kg.toFixed(2)}} kg</td>
                <td>${{rota.pareto_optimal ? '<span class="pareto-badge">⭐ Pareto</span>' : '-'}}</td>
                <td><button class="route-btn" onclick="toggleRouteDetail(${{idx}})"><i class="fas fa-eye"></i> Ver</button></td>
            `;
            tableBody.appendChild(row);
            
            // Criar detalhes da rota
            const detailDiv = document.createElement('div');
            detailDiv.id = `route-detail-${{idx}}`;
            detailDiv.className = 'route-detail';
            
            let segmentosHtml = '';
            rota.segmentos.forEach((seg, i) => {{
                const icon = seg.modal === 'caminhada' ? '🚶' : '🚌';
                const linha = seg.linha ? ` (Linha ${{seg.linha}})` : '';
                
                segmentosHtml += `
                    <div class="segment">
                        <div class="segment-header">
                            <span class="segment-icon">${{icon}}</span>
                            <span>${{seg.modal.toUpperCase()}}${{linha}}</span>
                        </div>
                        <div><strong>De:</strong> ${{seg.origem}}</div>
                        <div><strong>Para:</strong> ${{seg.destino}}</div>
                        <div class="segment-details">
                            <div><i class="fas fa-arrows-alt-h"></i> ${{seg.distancia_m.toFixed(0)}}m</div>
                            <div><i class="fas fa-clock"></i> ${{seg.tempo_min.toFixed(0)}} min</div>
                            <div><i class="fas fa-dollar-sign"></i> R$ ${{seg.custo_reais.toFixed(2)}}</div>
                        </div>
                    </div>
                `;
            }});
            
            detailDiv.innerHTML = `
                <h3>Detalhamento - Rota ${{idx + 1}}</h3>
                <p><strong>Linhas de ônibus:</strong> ${{rota.linhas_onibus.join(', ') || 'Nenhuma'}}</p>
                <p><strong>Total de segmentos:</strong> ${{rota.num_segmentos}}</p>
                ${{segmentosHtml}}
            `;
            
            document.getElementById('routeDetails').appendChild(detailDiv);
        }});
        
        console.log('✅ Tabela criada');
        
        function toggleRouteDetail(idx) {{
            const detail = document.getElementById(`route-detail-${{idx}}`);
            const isActive = detail.classList.contains('active');
            
            // Fechar todos
            document.querySelectorAll('.route-detail').forEach(d => d.classList.remove('active'));
            
            // Abrir se estava fechado
            if (!isActive) {{
                detail.classList.add('active');
                detail.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
            }}
        }}
        
        console.log('🎉 Dashboard completo!');
    </script>
</body>
</html>
"""


# ===== USO =====

if __name__ == "__main__":
    print("=" * 80)
    print("🎨 GERANDO DASHBOARD VISUAL ITERUM")
    print("=" * 80)
    
    FAFIRE_COORDS = (-8.058243, -34.889299)
    NOVA_ROMA_COORDS = (-8.117489, -34.900216)
    
    dashboard = DashboardVisualIterum()
    
    if dashboard.carregar_dados('resultados_iterum.json'):
        dashboard.definir_origem_destino(
            FAFIRE_COORDS,
            NOVA_ROMA_COORDS,
            "FAFIRE (Av. Conde da Boa Vista, 921)",
            "Faculdade Nova Roma (Rua Padre Carapuceiro, 590)"
        )
        
        arquivo = dashboard.gerar_dashboard('dashboard_iterum.html')
        
        print("\n✅ Dashboard gerado com sucesso!")
        print(f"\n📂 Arquivo: {arquivo}")
        print(f"\n🌐 Abra no navegador:")
        print(f"   {os.path.abspath(arquivo)}")
    else:
        print("\n❌ Erro: Execute 'python iterum_avancado.py' primeiro.")
    
    print("\n" + "=" * 80)
