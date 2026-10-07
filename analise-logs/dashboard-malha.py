import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import numpy as np

# ==========================================
# CONFIG
# ==========================================
st.set_page_config(
    page_title="Análise Temporal PI",
    layout="wide"
)

st.title("📈 Análise Temporal do Controle de Pressão")

st.markdown("""
Dashboard para análise cronológica do controlador PI.

### Recursos:
- Timeline contínua entre arquivos
- Pressão vs Setpoint
- Duty aplicado
- Erro temporal
- Métricas de estabilidade
- Diagnóstico rápido
""")

# ==========================================
# UPLOAD
# ==========================================
arquivos = st.file_uploader(
    "📂 Envie um ou mais CSVs",
    type=["csv"],
    accept_multiple_files=True
)

if not arquivos:
    st.stop()

# ==========================================
# LEITURA
# ==========================================
dfs = []

for arq in arquivos:

    try:
        df_temp = pd.read_csv(arq)

        df_temp["Arquivo"] = arq.name

        dfs.append(df_temp)

    except Exception as e:
        st.error(f"Erro ao ler {arq.name}: {e}")

if not dfs:
    st.stop()

df = pd.concat(dfs, ignore_index=True)

# ==========================================
# VALIDAÇÃO
# ==========================================
colunas_necessarias = [
    "Tempo_ms",
    "Setpoint_bar",
    "PressaoMedia_bar",
    "Duty_Aplicado",
    "Erro_bar"
]

for col in colunas_necessarias:

    if col not in df.columns:
        st.error(f"Coluna ausente: {col}")
        st.stop()

# ==========================================
# LIMPEZA
# ==========================================
for col in colunas_necessarias:

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

df = df.dropna(subset=colunas_necessarias)

if df.empty:
    st.error("Nenhum dado válido após limpeza.")
    st.stop()

# ==========================================
# TIMELINE CONTÍNUA
# ==========================================
df = df.sort_values([
    "Arquivo",
    "Tempo_ms"
])

df["Tempo_rel_s"] = df.groupby("Arquivo")[
    "Tempo_ms"
].transform(
    lambda x: (x - x.iloc[0]) / 1000.0
)

duracoes = df.groupby("Arquivo")[
    "Tempo_rel_s"
].max()

offsets = duracoes.cumsum().shift(fill_value=0)

df = df.merge(
    offsets.rename("Offset_s"),
    on="Arquivo"
)

df["Tempo_s"] = (
    df["Tempo_rel_s"] +
    df["Offset_s"]
)

# ==========================================
# ERRO
# ==========================================
df["Erro_Abs"] = np.abs(df["Erro_bar"])

# ==========================================
# CONTROLES
# ==========================================
tempo_max = df["Tempo_s"].max()

if tempo_max <= 0 or np.isnan(tempo_max):
    st.error("Tempo inválido.")
    st.stop()

inicio, fim = st.slider(
    "Janela temporal (s)",
    0.0,
    float(tempo_max),
    (
        0.0,
        min(20.0, float(tempo_max))
    ),
    0.1
)

df_j = df[
    (df["Tempo_s"] >= inicio) &
    (df["Tempo_s"] <= fim)
]

if df_j.empty:
    st.warning("Nenhum dado na janela.")
    st.stop()

# ==========================================
# PRESSÃO VS SETPOINT
# ==========================================
st.subheader("📈 Pressão vs Setpoint")

fig1 = go.Figure()

fig1.add_trace(go.Scatter(
    x=df_j["Tempo_s"],
    y=df_j["Setpoint_bar"],
    name="Setpoint",
    line=dict(
        dash='dash',
        width=3
    )
))

for nome, g in df_j.groupby("Arquivo"):

    fig1.add_trace(go.Scatter(
        x=g["Tempo_s"],
        y=g["PressaoMedia_bar"],
        name=f"Pressão ({nome})"
    ))

fig1.update_layout(
    xaxis_title="Tempo (s)",
    yaxis_title="Pressão (bar)",
    hovermode="x unified"
)

st.plotly_chart(
    fig1,
    use_container_width=True
)

# ==========================================
# DUTY
# ==========================================
st.subheader("⚡ Duty Aplicado")

fig2 = go.Figure()

for nome, g in df_j.groupby("Arquivo"):

    fig2.add_trace(go.Scatter(
        x=g["Tempo_s"],
        y=g["Duty_Aplicado"],
        name=f"Duty ({nome})"
    ))

fig2.update_layout(
    xaxis_title="Tempo (s)",
    yaxis_title="PWM",
    hovermode="x unified"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

# ==========================================
# ERRO
# ==========================================
st.subheader("❗ Erro do Controle")

fig3 = go.Figure()

for nome, g in df_j.groupby("Arquivo"):

    fig3.add_trace(go.Scatter(
        x=g["Tempo_s"],
        y=g["Erro_bar"],
        name=f"Erro ({nome})"
    ))

fig3.add_hline(
    y=0,
    line_dash="dash",
    line_color="white"
)

fig3.update_layout(
    xaxis_title="Tempo (s)",
    yaxis_title="Erro (bar)",
    hovermode="x unified"
)

st.plotly_chart(
    fig3,
    use_container_width=True
)

# ==========================================
# MÉTRICAS
# ==========================================
st.subheader("📊 Métricas")

media = df_j["PressaoMedia_bar"].mean()

std = df_j["PressaoMedia_bar"].std()

erro_medio = df_j["Erro_Abs"].mean()

erro_max = df_j["Erro_Abs"].max()

overshoot = (
    df_j["PressaoMedia_bar"].max() -
    df_j["Setpoint_bar"].mean()
)

tempo_em_faixa = (
    df_j["Erro_Abs"] < 0.15
).mean() * 100

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Pressão Média",
    f"{media:.2f} bar"
)

c2.metric(
    "Desvio Padrão",
    f"{std:.3f}"
)

c3.metric(
    "Erro Médio",
    f"{erro_medio:.3f}"
)

c4.metric(
    "Erro Máximo",
    f"{erro_max:.3f}"
)

c5.metric(
    "Tempo em Faixa",
    f"{tempo_em_faixa:.1f}%"
)

# ==========================================
# DIAGNÓSTICO
# ==========================================
st.subheader("🧠 Diagnóstico")

if erro_medio < 0.1:

    st.success(
        "Controle excelente."
    )

elif erro_medio < 0.3:

    st.info(
        "Controle bom e estável."
    )

elif erro_medio < 0.6:

    st.warning(
        "Controle aceitável, mas pode melhorar."
    )

else:

    st.error(
        "Erro elevado. Reavaliar tuning PI."
    )

# ==========================================
# TABELA
# ==========================================
with st.expander("📄 Ver dados"):

    st.dataframe(df_j)