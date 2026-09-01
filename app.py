"""
Interfaz Streamlit para el sistema de Scouting de Jugadores Parecidos.

Ejecutar con:
    streamlit run app.py --server.port 8502
"""

import json
from pathlib import Path
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="⚽ Scouting de Jugadores Parecidos",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8002"

# ── Estilos CSS (tema claro / minimalista) ───────────────────────────────────
st.markdown("""
<style>
    /* Fondo general */
    .stApp {
        background-color: #fafafa;
    }

    /* Tarjeta del jugador seleccionado */
    .player-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }
    .player-card h2 {
        margin: 0 0 0.25rem 0;
        color: #1a1a2e;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f5f5f7;
    }

    /* Leyenda */
    .legend-text {
        font-size: 0.84rem;
        color: #666;
        line-height: 1.6;
        background: #f0f2f6;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Cargar Catálogo de Jugadores ──────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_players_catalog():
    """Carga el catálogo de jugadores desde la API o archivo local."""
    try:
        resp = requests.get(f"{API_BASE}/api/catalog", timeout=5)
        if resp.status_code == 200:
            catalog = resp.json().get("catalog", [])
            if catalog:
                return catalog
    except Exception:
        pass

    # Fallback local
    local_path = Path(__file__).parent / "cache" / "players_catalog.json"
    if local_path.exists():
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Lista básica si aún no se ha generado el catálogo
    return [
        {"name": "Bukayo Saka", "team_name": "Arsenal FC", "league_name": "Premier League", "position": "Offence", "display_label": "Bukayo Saka (Arsenal FC - Premier League)"},
        {"name": "Arda Guler", "team_name": "Real Madrid CF", "league_name": "La Liga", "position": "Midfield", "display_label": "Arda Guler (Real Madrid CF - La Liga)"},
        {"name": "Jude Bellingham", "team_name": "Real Madrid CF", "league_name": "La Liga", "position": "Midfield", "display_label": "Jude Bellingham (Real Madrid CF - La Liga)"},
        {"name": "Lamine Yamal", "team_name": "FC Barcelona", "league_name": "La Liga", "position": "Offence", "display_label": "Lamine Yamal (FC Barcelona - La Liga)"},
        {"name": "Vinicius Junior", "team_name": "Real Madrid CF", "league_name": "La Liga", "position": "Offence", "display_label": "Vinicius Junior (Real Madrid CF - La Liga)"},
        {"name": "Kylian Mbappé", "team_name": "Real Madrid CF", "league_name": "La Liga", "position": "Offence", "display_label": "Kylian Mbappé (Real Madrid CF - La Liga)"},
        {"name": "Erling Haaland", "team_name": "Manchester City FC", "league_name": "Premier League", "position": "Offence", "display_label": "Erling Haaland (Manchester City FC - Premier League)"},
        {"name": "Pedri", "team_name": "FC Barcelona", "league_name": "La Liga", "position": "Midfield", "display_label": "Pedri (FC Barcelona - La Liga)"},
        {"name": "Cole Palmer", "team_name": "Chelsea FC", "league_name": "Premier League", "position": "Midfield", "display_label": "Cole Palmer (Chelsea FC - Premier League)"},
        {"name": "Mohamed Salah", "team_name": "Liverpool FC", "league_name": "Premier League", "position": "Offence", "display_label": "Mohamed Salah (Liverpool FC - Premier League)"},
        {"name": "Rodri", "team_name": "Manchester City FC", "league_name": "Premier League", "position": "Midfield", "display_label": "Rodri (Manchester City FC - Premier League)"},
    ]


catalog_players = load_players_catalog()

# Construir opciones ordenadas con jugadores estrella al principio
FEATURED_NAMES = [
    "Bukayo Saka", "Arda Guler", "Jude Bellingham", "Lamine Yamal",
    "Vinicius Junior", "Kylian Mbappé", "Erling Haaland", "Pedri",
    "Cole Palmer", "Mohamed Salah", "Rodri", "Kevin De Bruyne",
    "Florian Wirtz", "Jamal Musiala", "Lautaro Martínez", "Antoine Griezmann"
]

featured_opts = []
other_opts = []

player_map = {}
for p in catalog_players:
    label = p.get("display_label") or f"{p['name']} ({p.get('team_name', '')} - {p.get('league_name', '')})"
    player_map[label] = p
    
    # Comprobar si es un jugador destacado
    is_featured = any(feat.lower() in p["name"].lower() for feat in FEATURED_NAMES)
    if is_featured:
        featured_opts.append(label)
    else:
        other_opts.append(label)

featured_opts = sorted(list(set(featured_opts)))
other_opts = sorted(list(set(other_opts)))
all_player_options = featured_opts + other_opts


# ── SIDEBAR — Inputs en un FORMULARIO ────────────────────────────────────────
# El formulario garantiza que NO haya ningún procesamiento ni llamadas a la API
# mientras el usuario busca, selecciona jugadores o ajusta los filtros.
with st.sidebar:
    st.markdown("## ⚽ Scouting de Jugadores")
    st.markdown("Encuentra qué jugadores tienen el juego más parecido.")
    st.markdown("---")

    with st.form(key="scouting_form"):
        # Desplegable con buscador integrado
        selected_option = st.selectbox(
            "👤 Jugador a analizar",
            options=all_player_options,
            index=0 if all_player_options else None,
            help="Escribe el nombre del jugador (ej. Arda Guler, Saka, Pedri...) para filtrar la lista.",
        )

        st.markdown("---")

        # Posiciones
        POSITION_LABELS = {
            "DC": "Delantero Centro", "EI": "Extremo Izquierdo",
            "ED": "Extremo Derecho", "MI": "Mediocampista Izq.",
            "MD": "Mediocampista Der.", "MC": "Mediocentro",
            "MCD": "Mediocentro Def.", "MCO": "Mediocentro Ofens.",
            "DFC": "Defensa Central", "LI": "Lateral Izquierdo",
            "LD": "Lateral Derecho", "CAI": "Carrilero Izq.",
            "CAD": "Carrilero Der.",
        }

        positions = st.multiselect(
            "📍 Posiciones a analizar",
            options=list(POSITION_LABELS.keys()),
            format_func=lambda x: f"{x} — {POSITION_LABELS[x]}",
            default=["DC", "EI", "ED", "MI", "MD", "MC", "MCO"],
        )

        # Mínimo de minutos
        min_minutes = st.number_input(
            "⏱️ Mínimo de minutos jugados",
            min_value=0, max_value=4000, value=300, step=50,
            help="Filtra jugadores que hayan jugado al menos esta cantidad de minutos.",
        )

        # Mínimo de partidos
        min_matches = st.number_input(
            "📊 Mínimo de partidos jugados (últimos X partidos)",
            min_value=1, max_value=40, value=5, step=1,
            help="Filtra jugadores con al menos este número de partidos disputados.",
        )

        # Ligas
        league_options = ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]
        selected_leagues = st.multiselect(
            "🏆 Ligas a analizar",
            options=league_options,
            default=["La Liga", "Premier League"],
        )

        st.markdown("---")

        # Botón para ejecutar el scouting
        submit_button = st.form_submit_button(
            "🔍 Comenzar Scouting",
            type="primary",
            use_container_width=True,
        )

    # Estado de la API
    try:
        status_resp = requests.get(f"{API_BASE}/api/status", timeout=2)
        if status_resp.status_code == 200:
            remaining = status_resp.json().get("api_football_remaining", "?")
            st.caption(f"📡 Cuota API-Football restante hoy: **{remaining}**")
    except Exception:
        pass


# ── PROCESAMIENTO AL CLICAR EL BOTÓN ─────────────────────────────────────────
if submit_button:
    if not selected_option:
        st.warning("⚠️ Selecciona un jugador en el desplegable.")
    elif not positions:
        st.warning("⚠️ Selecciona al menos una posición.")
    elif not selected_leagues:
        st.warning("⚠️ Selecciona al menos una liga.")
    else:
        player_info = player_map.get(selected_option, {})
        player_name = player_info.get("name", selected_option.split("(")[0].strip())
        team_name = player_info.get("team_name")

        with st.spinner(f"🔄 Procesando datos de scouting para {player_name}... Por favor espera."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/scouting",
                    json={
                        "player_name": player_name,
                        "team_name": team_name,
                        "player_league": player_info.get("league_name"),
                        "positions": positions,
                        "leagues": selected_leagues,
                        "min_matches": int(min_matches),
                        "min_minutes": int(min_minutes),
                    },

                    timeout=180,
                )
                if resp.status_code == 200:
                    st.session_state["scouting_data"] = resp.json()
                else:
                    detail = resp.json().get("detail", "Error procesando scouting.")
                    st.error(f"❌ {detail}")
            except requests.ConnectionError:
                st.error("⚠️ No se pudo conectar con el servidor backend. Asegúrate de que FastAPI esté corriendo en el puerto 8002.")
            except Exception as e:
                st.error(f"❌ Error inesperado: {e}")


# ── MOSTRAR RESULTADOS ──────────────────────────────────────────────────────
if "scouting_data" not in st.session_state:
    st.markdown("## ⚽ Sistema de Scouting de Jugadores Parecidos")
    st.markdown("""
    Bienvenido al sistema de scouting avanzado por estilo de juego:
    
    1. **Selecciona un jugador** en el panel de la izquierda (ej. *Arda Guler*, *Bukayo Saka*, *Pedri*...).
    2. Ajusta las **posiciones**, **minutos jugados**, **partidos mínimos** y **ligas** deseadas.
    3. Haz clic en **Comenzar Scouting**.
    
    El sistema descargará los datos, calculará las métricas por 90 minutos, aplicará escalado MinMax, calculará la similitud del coseno y agrupará a los jugadores mediante K-Means con visualización PCA.
    """)
    st.stop()

data = st.session_state["scouting_data"]
sp = data["selected_player"]
similar = data["similar_players"]
clustering = data["clustering"]
comparison = data["comparison"]

# ═══════════════════════════════════════════════════════════════════════════════
# FILA SUPERIOR:  Jugador seleccionado (izq)  |  K-Means (der)
# ═══════════════════════════════════════════════════════════════════════════════
col_player, col_kmeans = st.columns([1, 1], gap="large")

# ── Tarjeta del jugador seleccionado ─────────────────────────────────────────
with col_player:
    st.markdown("### 🎯 Jugador Seleccionado")

    c_img, c_info = st.columns([1, 3])
    with c_img:
        photo_url = sp.get("photo", "")
        if photo_url:
            st.image(photo_url, width=95)
        elif sp.get("team_logo"):
            st.image(sp.get("team_logo"), width=95)
    with c_info:
        st.markdown(f"## {sp['name']}")
        st.markdown(
            f"**{sp.get('team_name', 'N/A')}** · {sp.get('league_name', 'N/A')}  \n"
            f"📍 Posición: **{sp.get('position', 'N/A')}** · 🌍 {sp.get('nationality', '')}"
        )

    # Stats del jugador seleccionado en tabla
    stats = sp["stats"]
    stats_df = pd.DataFrame([stats])
    st.dataframe(
        stats_df,
        hide_index=True,
        use_container_width=True,
    )

# ── Gráfico K-Means ─────────────────────────────────────────────────────────
with col_kmeans:
    st.markdown("### 📊 Clustering K-Means (PCA: PC1 vs PC2)")

    pca_df = pd.DataFrame(clustering["pca_data"])
    pca_df["cluster"] = "Cluster " + pca_df["cluster"].astype(str)

    fig_kmeans = px.scatter(
        pca_df,
        x="pc1",
        y="pc2",
        color="cluster",
        hover_name="name",
        labels={"pc1": "Componente Principal 1 (PC1)", "pc2": "Componente Principal 2 (PC2)", "cluster": "Grupo"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )

    # Destacar jugador seleccionado con un anillo rojo alrededor
    sel_pca = pca_df[pca_df["is_selected"]]
    if not sel_pca.empty:
        fig_kmeans.add_trace(go.Scatter(
            x=sel_pca["pc1"],
            y=sel_pca["pc2"],
            mode="markers",
            marker=dict(
                size=22,
                color="rgba(255, 0, 0, 0.15)",
                line=dict(width=3, color="red"),
                symbol="circle",
            ),
            name=f"🎯 {sp['name']} (Seleccionado)",
            showlegend=True,
            hoverinfo="name",
        ))

    fig_kmeans.update_layout(
        height=420,
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=40, r=20, t=10, b=60),
    )

    st.plotly_chart(fig_kmeans, use_container_width=True, key="kmeans_plot")

    ev = clustering.get("explained_variance", [])
    if len(ev) >= 2:
        st.caption(
            f"Varianza explicada: PC1 = {ev[0]:.1%}, PC2 = {ev[1]:.1%} · "
            f"K = {clustering['n_clusters']} clusters óptimos (Técnica del codo guardada en `outputs/`)"
        )

# ═══════════════════════════════════════════════════════════════════════════════
# FILA CENTRAL:  Top 10 jugadores similares
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(f"### 🏅 Top 10 Jugadores Más Parecidos a {sp['name']}  ·  _{data.get('total_players_analyzed', '?')} jugadores analizados_")

table_rows = []
for p in similar:
    row = {
        "#": p["rank"],
        "Jugador": p["name"],
        "Equipo": p["team_name"],
        "Liga": p["league_name"],
        "Similitud": f"{p['similarity']:.1%}",
    }
    row.update(p["stats"])
    table_rows.append(row)

table_df = pd.DataFrame(table_rows)

# Tabla scrollable con altura adecuada para 5 filas iniciales y scroll para 6-10
st.dataframe(
    table_df,
    hide_index=True,
    use_container_width=True,
    height=240,
)

# Leyenda
st.markdown(
    '<div class="legend-text">'
    '<b>PJ</b> = Partidos Jugados · <b>G</b> = Goles · <b>AS</b> = Asistencias · '
    '<b>PC</b> = Pases Completados · <b>%P</b> = % Acierto de Pases · <b>TR</b> = Tiros Realizados · <br>'
    '<b>RC</b> = Regates Completados · <b>ER</b> = Entradas Realizadas · <b>ID</b> = Intercepciones Defensivas · <b>AM</b> = Amarillas'
    '</div>',
    unsafe_allow_html=True,
)



# ═══════════════════════════════════════════════════════════════════════════════
# FILA INFERIOR:  8 gráficos de barras comparativos
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
top1_name = comparison.get("top1_name", "Top 1 Más Parecido")
st.markdown(f"### 📈 Comparativa de Métricas: {sp['name']} vs {top1_name} vs Promedio del Cluster")

STAT_LABELS = {
    "G": "Goles (por 90 min)",
    "AS": "Asistencias (Total)",
    "PC": "Pases Completados (por 90 min)",
    "TR": "Tiros (por 90 min)",
    "RC": "Regates (por 90 min)",
    "ER": "Entradas (por 90 min)",
    "ID": "Intercepciones (por 90 min)",
    "AM": "Amarillas (Total)",
}
STAT_KEYS = list(STAT_LABELS.keys())

BAR_COLORS = ["#2b5c8f", "#d95f02", "#7570b3"]
BAR_NAMES = [sp["name"][:18], top1_name[:18], "Media Cluster"]

# Grid 4 × 2
for row_start in range(0, 8, 4):
    cols = st.columns(4, gap="medium")
    for col_offset, col in enumerate(cols):
        idx = row_start + col_offset
        if idx >= len(STAT_KEYS):
            break
        key = STAT_KEYS[idx]
        label = STAT_LABELS[key]

        values = [
            comparison["selected"].get(key, 0),
            comparison["top1"].get(key, 0),
            comparison["cluster_avg"].get(key, 0),
        ]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=BAR_NAMES,
            y=values,
            marker_color=BAR_COLORS,
            text=[f"{v:.2f}" if isinstance(v, float) else str(v) for v in values],
            textposition="outside",
            textfont=dict(size=11),
        ))
        fig.update_layout(
            title=dict(text=label, font=dict(size=12, color="#333"), x=0.5),
            height=230,
            template="plotly_white",
            showlegend=False,
            margin=dict(l=15, r=15, t=35, b=15),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(0,0,0,0.06)",
                rangemode="tozero",
            ),
            xaxis=dict(tickfont=dict(size=10)),
        )

        with col:
            st.plotly_chart(fig, use_container_width=True, key=f"bar_{key}")
