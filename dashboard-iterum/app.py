import streamlit as st
import pandas as pd
import json

# Configuração básica da página
st.set_page_config(page_title="Dashboard Iterum", layout="wide")

st.title("🚍 Dashboard de Rotas - ITERUM")
st.write("Carregue o arquivo JSON gerado pelo sistema para visualizar as rotas em formato de dashboard.")

# 1) Upload do arquivo JSON
uploaded_file = st.file_uploader(
    "Envie o arquivo resultados_iterum.json",
    type=["json"]
)

if uploaded_file is None:
    st.info("⬆️ Use o botão acima para selecionar o arquivo .json do seu computador.")
    st.stop()

# 2) Ler o conteúdo do JSON
data = json.load(uploaded_file)

metadata = data.get("metadata", {})
rotas = data.get("rotas", [])

if not rotas:
    st.error("Nenhuma rota encontrada no JSON.")
    st.stop()

# 3) DataFrame com visão geral das rotas
cols_rotas = [
    "criterio",
    "tempo_min",
    "custo_reais",
    "distancia_km",
    "emissoes_kg",
    "transferencias",
    "num_embarques_onibus",
    "num_trechos_caminhada",
    "rank_tempo",
    "rank_custo",
    "rank_emissoes",
    "pareto_optimal",
]

df_rotas = pd.DataFrame([
    {col: rota.get(col) for col in cols_rotas}
    for rota in rotas
])

# 4) DataFrame com os segmentos (trechos) de cada rota
segmentos_rows = []
for rota in rotas:
    criterio = rota.get("criterio")
    for seg in rota.get("segmentos", []):
        row = seg.copy()
        row["criterio"] = criterio
        segmentos_rows.append(row)

df_segmentos = pd.DataFrame(segmentos_rows)

# ======= SIDEBAR =======
st.sidebar.header("Informações gerais")
st.sidebar.write(f"**Sistema:** {metadata.get('sistema', '-')}")
st.sidebar.write(f"**Timestamp:** {metadata.get('timestamp', '-')}")
st.sidebar.write(f"**Nº de rotas:** {metadata.get('num_rotas', len(rotas))}")

# ======= VISÃO GERAL =======
st.subheader("📋 Rotas comparadas")

st.dataframe(
    df_rotas.style.format({
        "tempo_min": "{:.1f}",
        "custo_reais": "R$ {:.2f}",
        "distancia_km": "{:.2f}",
        "emissoes_kg": "{:.3f}",
    }),
    use_container_width=True,
)

# ======= KPIs / DESTAQUES =======
st.subheader("🏆 Destaques")

col1, col2, col3 = st.columns(3)

rota_melhor_tempo = df_rotas.sort_values("rank_tempo").iloc[0]
col1.metric(
    "Mais Rápida",
    f"{rota_melhor_tempo['tempo_min']:.1f} min",
    f"Critério: {rota_melhor_tempo['criterio']}",
)

rota_melhor_custo = df_rotas.sort_values("rank_custo").iloc[0]
col2.metric(
    "Mais Econômica",
    f"R$ {rota_melhor_custo['custo_reais']:.2f}",
    f"Critério: {rota_melhor_custo['criterio']}",
)

rota_melhor_emissao = df_rotas.sort_values("rank_emissoes").iloc[0]
col3.metric(
    "Mais Sustentável",
    f"{rota_melhor_emissao['emissoes_kg']:.3f} kg CO₂",
    f"Critério: {rota_melhor_emissao['criterio']}",
)

# ======= GRÁFICO DE COMPARAÇÃO =======
st.subheader("📊 Comparação entre rotas")

metrica = st.selectbox(
    "Escolha a métrica para comparar",
    ["tempo_min", "custo_reais", "distancia_km", "emissoes_kg", "transferencias"],
    format_func=lambda x: {
        "tempo_min": "Tempo (min)",
        "custo_reais": "Custo (R$)",
        "distancia_km": "Distância (km)",
        "emissoes_kg": "Emissões (kg CO₂)",
        "transferencias": "Nº de transferências",
    }.get(x, x),
)

df_plot = df_rotas.set_index("criterio")[[metrica]]
st.bar_chart(df_plot)

# ======= DETALHE DE UMA ROTA =======
st.subheader("🔎 Detalhes de uma rota específica")

criterio_escolhido = st.selectbox(
    "Selecione a rota (critério)",
    df_rotas["criterio"].unique(),
)

df_rota_escolhida = df_rotas[df_rotas["criterio"] == criterio_escolhido]
df_segmentos_escolhida = df_segmentos[df_segmentos["criterio"] == criterio_escolhido]

st.markdown(f"### Rota: **{criterio_escolhido}**")

col_a, col_b, col_c, col_d = st.columns(4)

r = df_rota_escolhida.iloc[0]

col_a.metric("Tempo total (min)", f"{r['tempo_min']:.1f}")
col_b.metric("Custo total (R$)", f"{r['custo_reais']:.2f}")
col_c.metric("Distância (km)", f"{r['distancia_km']:.2f}")
col_d.metric("Emissões (kg CO₂)", f"{r['emissoes_kg']:.3f}")

st.markdown("#### Segmentos da rota (trechos)")

if not df_segmentos_escolhida.empty:
    st.dataframe(
        df_segmentos_escolhida[
            ["origem", "destino", "modal", "linha",
             "distancia_m", "tempo_min", "custo_reais", "emissoes_kg"]
        ].style.format({
            "distancia_m": "{:.1f}",
            "tempo_min": "{:.2f}",
            "custo_reais": "R$ {:.2f}",
            "emissoes_kg": "{:.4f}",
        }),
        use_container_width=True,
    )
else:
    st.info("Nenhum segmento encontrado para essa rota.")
