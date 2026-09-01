"""
Data Football Scout — Sistema de Identificación de Perfiles y Jugadores Similares.
Interfaz profesional de scouting avanzado basada en Machine Learning.
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
    page_title="Data Football Scout | Scouting & Similarity Engine",
    page_icon="https://crests.football-data.org/PL.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8002"

# ── Logotipos Oficiales de Competiciones ─────────────────────────────────────
LEAGUE_LOGOS = {
    "La Liga": "https://media.api-sports.io/football/leagues/140.png",
    "Premier League": "https://media.api-sports.io/football/leagues/39.png",
    "Bundesliga": "https://media.api-sports.io/football/leagues/78.png",
    "Serie A": "https://media.api-sports.io/football/leagues/135.png",
    "Ligue 1": "https://media.api-sports.io/football/leagues/61.png",
}

# ── Banderas de Países ──────────────────────────────────────────────────────
COUNTRY_FLAG_CODES = {
    "spain": "es", "espana": "es", "england": "gb-eng", "inglaterra": "gb-eng",
    "france": "fr", "francia": "fr", "germany": "de", "alemania": "de",
    "italy": "it", "italia": "it", "brazil": "br", "brasil": "br",
    "argentina": "ar", "portugal": "pt", "netherlands": "nl", "holanda": "nl",
    "belgium": "be", "belgica": "be", "croatia": "hr", "croacia": "hr",
    "turkey": "tr", "turquia": "tr", "norway": "no", "noruega": "no",
    "poland": "pl", "polonia": "pl", "uruguay": "uy", "colombia": "co",
    "ecuador": "ec", "senegal": "sn", "morocco": "ma", "marruecos": "ma",
    "nigeria": "ng", "ghana": "gh", "japan": "jp", "japon": "jp",
    "south korea": "kr", "corea del sur": "kr", "united states": "us", "usa": "us",
    "denmark": "dk", "dinamarca": "dk", "sweden": "se", "suecia": "se",
    "switzerland": "ch", "suiza": "ch", "austria": "at", "scotland": "gb-sct",
    "wales": "gb-wls", "serbia": "rs", "georgia": "ge", "ukraine": "ua",
    "ucrania": "ua", "cameroon": "cm", "camerun": "cm", "ivory coast": "ci",
    "costa de marfil": "ci", "egypt": "eg", "egipto": "eg", "algeria": "dz",
    "chile": "cl", "paraguay": "py", "venezuela": "ve", "peru": "pe"
}


def get_country_flag_url(nationality: str) -> str:
    """Devuelve la URL de la bandera correspondiente a la nacionalidad."""
    if not nationality:
        return ""
    clean_nat = nationality.lower().strip()
    code = COUNTRY_FLAG_CODES.get(clean_nat)
    if code:
        return f"https://flagcdn.com/w40/{code}.png"
    return ""


# ── Estilos CSS Profesionales ────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }

    /* Top Brand Bar */
    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.8rem 1.4rem;
        background: #0f172a;
        color: white;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
    }
    .brand-title {
        font-size: 1.15rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #f8fafc;
    }
    .brand-subtitle {
        font-size: 0.78rem;
        color: #94a3b8;
        font-weight: 500;
        margin-top: 2px;
    }
    .leagues-banner {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .league-logo-img {
        height: 26px;
        width: auto;
        object-fit: contain;
        background: white;
        border-radius: 4px;
        padding: 2px 4px;
    }

    /* Player Profile Card */
    .player-profile-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        margin-bottom: 1.25rem;
    }
    .player-main-header {
        display: flex;
        align-items: center;
        gap: 1.2rem;
        margin-bottom: 1.2rem;
    }
    .player-photo-container {
        position: relative;
        width: 82px;
        height: 82px;
        border-radius: 50%;
        overflow: hidden;
        border: 2px solid #e2e8f0;
        background: #f1f5f9;
        flex-shrink: 0;
    }
    .player-photo-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .player-identity {
        flex-grow: 1;
    }
    .player-name-title {
        font-size: 1.45rem;
        font-weight: 800;
        color: #0f172a;
        margin: 0;
        line-height: 1.2;
    }
    .player-meta-badges {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 6px;
        flex-wrap: wrap;
    }
    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 3px 9px;
        border-radius: 6px;
        background: #f1f5f9;
        color: #334155;
        border: 1px solid #e2e8f0;
    }
    .badge-pill img {
        height: 14px;
        width: auto;
        object-fit: contain;
    }

    /* Stat Badges Grid */
    .stat-badge-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        margin-top: 0.8rem;
    }
    .stat-badge-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 8px 6px;
        text-align: center;
    }
    .stat-badge-label {
        font-size: 0.68rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .stat-badge-val {
        font-size: 1.1rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 2px;
    }

    /* Section Headers */
    .section-title-wrap {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.8rem;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid #e2e8f0;
    }
    .section-title {
        font-size: 1rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #0f172a;
        margin: 0;
    }
    .section-tag {
        font-size: 0.74rem;
        color: #64748b;
        font-weight: 600;
    }

    /* Glossary Card */
    .glossary-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-size: 0.75rem;
        color: #64748b;
        line-height: 1.6;
        margin-top: 0.5rem;
    }
    .glossary-card b {
        color: #0f172a;
    }

    /* Sidebar Tweaks */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)


# ── Cargar Catálogo de Jugadores ──────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_players_catalog():
    """Carga el catálogo de jugadores desde la API o archivo local."""
    try:
        resp = requests.get(f"{API_BASE}/api/catalog", timeout=4)
        if resp.status_code == 200:
            catalog = resp.json().get("catalog", [])
            if catalog:
                return catalog
    except Exception:
        pass

    local_path = Path(__file__).parent / "cache" / "players_catalog.json"
    if local_path.exists():
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return []


catalog_players = load_players_catalog()

# Jugadores destacados al principio del selector
FEATURED_NAMES = [
    "Bukayo Saka", "Arda Guler", "Cole Palmer", "Vinicius Junior",
    "Kylian Mbappé", "Jude Bellingham", "Lamine Yamal", "Pedri",
    "Erling Haaland", "Mohamed Salah", "Rodri", "Florian Wirtz",
    "Jamal Musiala", "Lautaro Martínez", "Antoine Griezmann", "Aimar Oroz"
]

featured_opts = []
other_opts = []
player_map = {}

for p in catalog_players:
    p_name = p.get("name", "")
    t_name = p.get("team_name", "")
    l_name = p.get("league_name", "")
    label = f"{p_name} — {t_name} ({l_name})"
    player_map[label] = p

    is_featured = any(feat.lower() in p_name.lower() for feat in FEATURED_NAMES)
    if is_featured:
        featured_opts.append(label)
    else:
        other_opts.append(label)

featured_opts = sorted(list(set(featured_opts)))
other_opts = sorted(list(set(other_opts)))
all_player_options = featured_opts + other_opts


# ── HEADER SUPERIOR DE LA APLICACIÓN ─────────────────────────────────────────
st.markdown("""
<div class="brand-header">
    <div>
        <div class="brand-title">Data Football Scout</div>
        <div class="brand-subtitle">Motor de Similitud Vectorial y Clasificación de Perfiles de Juego</div>
    </div>
    <div class="leagues-banner">
        <img class="league-logo-img" src="https://media.api-sports.io/football/leagues/39.png" alt="Premier League" title="Premier League">
        <img class="league-logo-img" src="https://media.api-sports.io/football/leagues/140.png" alt="La Liga" title="La Liga">
        <img class="league-logo-img" src="https://media.api-sports.io/football/leagues/78.png" alt="Bundesliga" title="Bundesliga">
        <img class="league-logo-img" src="https://media.api-sports.io/football/leagues/135.png" alt="Serie A" title="Serie A">
        <img class="league-logo-img" src="https://media.api-sports.io/football/leagues/61.png" alt="Ligue 1" title="Ligue 1">
    </div>
</div>
""", unsafe_allow_html=True)


# ── SIDEBAR — Panel de Configuración y Filtros ────────────────────────────────
with st.sidebar:
    st.markdown("#### Configuración de Búsqueda")
    st.caption("Filtra y localiza futbolistas con patrones de rendimiento similares.")

    with st.form(key="scouting_form"):
        selected_option = st.selectbox(
            "Jugador Objetivo",
            options=all_player_options,
            index=0 if all_player_options else None,
            help="Escribe el nombre del jugador para filtrar la lista instantáneamente.",
        )

        st.markdown("---")

        POSITION_LABELS = {
            "DC": "Delantero Centro", "EI": "Extremo Izquierdo",
            "ED": "Extremo Derecho", "MI": "Interior Izquierdo",
            "MD": "Interior Derecho", "MC": "Mediocentro",
            "MCD": "Pivote Defensivo", "MCO": "Mediapunta",
            "DFC": "Defensa Central", "LI": "Lateral Izquierdo",
            "LD": "Lateral Derecho", "CAI": "Carrilero Izquierdo",
            "CAD": "Carrilero Derecho",
        }

        positions = st.multiselect(
            "Demarcaciones a Comparar",
            options=list(POSITION_LABELS.keys()),
            format_func=lambda x: f"{x} ({POSITION_LABELS[x]})",
            default=["DC", "EI", "ED", "MI", "MD", "MC", "MCO"],
        )

        min_minutes = st.number_input(
            "Umbral Mínimo de Minutos",
            min_value=0, max_value=4000, value=300, step=50,
            help="Filtra jugadores que hayan disputado al menos este volumen de minutos.",
        )

        min_matches = st.number_input(
            "Mínimo de Partidos Jugados",
            min_value=1, max_value=40, value=5, step=1,
            help="Mínimo de partidos oficiales disputados en la temporada.",
        )

        league_options = ["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"]
        selected_leagues = st.multiselect(
            "Competiciones a Incluir",
            options=league_options,
            default=["La Liga", "Premier League"],
        )

        st.markdown("---")

        submit_button = st.form_submit_button(
            "Calcular Similitud",
            type="primary",
            use_container_width=True,
        )

    try:
        status_resp = requests.get(f"{API_BASE}/api/status", timeout=2)
        if status_resp.status_code == 200:
            remaining = status_resp.json().get("api_football_remaining", "?")
            st.caption(f"Cuota API-Football restante hoy: **{remaining}**")
    except Exception:
        pass


# ── PROCESAMIENTO AL CLICAR EL BOTÓN ─────────────────────────────────────────
if submit_button:
    if not selected_option:
        st.warning("Selecciona un jugador en el desplegable.")
    elif not positions:
        st.warning("Selecciona al menos una demarcación para el filtro.")
    elif not selected_leagues:
        st.warning("Selecciona al menos una competición para la búsqueda.")
    else:
        player_info = player_map.get(selected_option, {})
        player_name = player_info.get("name", selected_option.split("—")[0].strip())
        team_name = player_info.get("team_name")
        player_league = player_info.get("league_name")

        with st.spinner(f"Analizando métricas y calculando similitud vectorial para {player_name}..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/scouting",
                    json={
                        "player_name": player_name,
                        "team_name": team_name,
                        "player_league": player_league,
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
                    detail = resp.json().get("detail", "Error procesando el informe de scouting.")
                    st.error(detail)
            except requests.ConnectionError:
                st.error("Error de conexión con el backend. Comprueba que FastAPI esté en ejecución en el puerto 8002.")
            except Exception as e:
                st.error(f"Error inesperado: {e}")


# ── ESTADO INICIAL (SIN RESULTADOS) ──────────────────────────────────────────
if "scouting_data" not in st.session_state:
    st.markdown("""
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 2rem; margin-top: 1rem;">
        <h3 style="margin-top: 0; color: #0f172a; font-weight: 800;">Panel de Análisis de Rendimiento</h3>
        <p style="color: #475569; font-size: 0.92rem; line-height: 1.6;">
            Esta herramienta evalúa futbolistas basándose en un vector de características multidimensional normalizado cada 90 minutos de juego efectivo.
        </p>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.2rem; margin-top: 1.5rem;">
            <div style="background: #f8fafc; padding: 1.2rem; border-radius: 8px; border: 1px solid #e2e8f0;">
                <div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">1. Selección de Perfil</div>
                <div style="font-size: 0.82rem; color: #64748b;">Escoge el futbolista de referencia en el panel lateral y define las ligas a explorar.</div>
            </div>
            <div style="background: #f8fafc; padding: 1.2rem; border-radius: 8px; border: 1px solid #e2e8f0;">
                <div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">2. Similitud Vectorial</div>
                <div style="font-size: 0.82rem; color: #64748b;">El motor normaliza métricas per-90 con MinMaxScaler y calcula la Similitud del Coseno.</div>
            </div>
            <div style="background: #f8fafc; padding: 1.2rem; border-radius: 8px; border: 1px solid #e2e8f0;">
                <div style="font-weight: 700; color: #0f172a; margin-bottom: 4px;">3. Clustering Táctico</div>
                <div style="font-size: 0.82rem; color: #64748b;">Agrupación mediante K-Means y proyección espacial reducida con PCA 2D interactivo.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── RENDERIZADO DE RESULTADOS ────────────────────────────────────────────────
data = st.session_state["scouting_data"]
sp = data["selected_player"]
similar = data["similar_players"]
clustering = data["clustering"]
comparison = data["comparison"]

league_logo_url = LEAGUE_LOGOS.get(sp.get("league_name", ""), "")
flag_url = get_country_flag_url(sp.get("nationality", ""))
team_crest_url = sp.get("team_logo", "")
player_photo_url = sp.get("photo", "")


# ═══════════════════════════════════════════════════════════════════════════════
# FILA SUPERIOR:  Ficha del Jugador Seleccionado  |  K-Means PCA 2D
# ═══════════════════════════════════════════════════════════════════════════════
col_player, col_kmeans = st.columns([1, 1], gap="large")

with col_player:
    st.markdown("""
    <div class="section-title-wrap">
        <h4 class="section-title">Perfil del Jugador Seleccionado</h4>
        <span class="section-tag">Objetivo de Scouting</span>
    </div>
    """, unsafe_allow_html=True)

    league_img_html = f'<img src="{league_logo_url}" alt="League">' if league_logo_url else ""
    crest_img_html = f'<img src="{team_crest_url}" alt="Club">' if team_crest_url else ""
    flag_img_html = f'<img src="{flag_url}" alt="Country">' if flag_url else ""
    photo_src = player_photo_url if player_photo_url else "https://media.api-sports.io/football/players/placeholder.png"

    st.markdown(f"""
    <div class="player-profile-card">
        <div class="player-main-header">
            <div class="player-photo-container">
                <img class="player-photo-img" src="{photo_src}" alt="{sp['name']}">
            </div>
            <div class="player-identity">
                <h2 class="player-name-title">{sp['name']}</h2>
                <div class="player-meta-badges">
                    <span class="badge-pill">{crest_img_html} {sp.get('team_name', 'N/A')}</span>
                    <span class="badge-pill">{league_img_html} {sp.get('league_name', 'N/A')}</span>
                    <span class="badge-pill">{flag_img_html} {sp.get('nationality', 'N/A')}</span>
                    <span class="badge-pill" style="background: #e0f2fe; color: #0369a1; border-color: #bae6fd;">{sp.get('position', 'N/A')}</span>
                </div>
            </div>
        </div>
        <div class="stat-badge-grid">
            <div class="stat-badge-box">
                <div class="stat-badge-label">PJ</div>
                <div class="stat-badge-val">{sp['stats']['PJ']}</div>
            </div>
            <div class="stat-badge-box">
                <div class="stat-badge-label">Goles</div>
                <div class="stat-badge-val">{sp['stats']['G']}</div>
            </div>
            <div class="stat-badge-box">
                <div class="stat-badge-label">Asistencias</div>
                <div class="stat-badge-val">{sp['stats']['AS']}</div>
            </div>
            <div class="stat-badge-box">
                <div class="stat-badge-label">Pases Tot.</div>
                <div class="stat-badge-val">{sp['stats']['PC']}</div>
            </div>
            <div class="stat-badge-box">
                <div class="stat-badge-label">% Acierto</div>
                <div class="stat-badge-val">{sp['stats']['%P']:.0%}</div>
            </div>
            <div class="stat-badge-box">
                <div class="stat-badge-label">Tiros</div>
                <div class="stat-badge-val">{sp['stats']['TR']}</div>
            </div>
            <div class="stat-badge-box">
                <div class="stat-badge-label">Regates</div>
                <div class="stat-badge-val">{sp['stats']['RC']}</div>
            </div>
            <div class="stat-badge-box">
                <div class="stat-badge-label">Entradas</div>
                <div class="stat-badge-val">{sp['stats']['ER']}</div>
            </div>
            <div class="stat-badge-box">
                <div class="stat-badge-label">Intercepciones</div>
                <div class="stat-badge-val">{sp['stats']['ID']}</div>
            </div>
            <div class="stat-badge-box">
                <div class="stat-badge-label">Amarillas</div>
                <div class="stat-badge-val">{sp['stats']['AM']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


with col_kmeans:
    st.markdown("""
    <div class="section-title-wrap">
        <h4 class="section-title">Espacio Vectorial PCA & Clustering K-Means</h4>
        <span class="section-tag">Proyección 2D</span>
    </div>
    """, unsafe_allow_html=True)

    pca_df = pd.DataFrame(clustering["pca_data"])
    pca_df["cluster_label"] = "Cluster " + pca_df["cluster"].astype(str)

    fig_kmeans = px.scatter(
        pca_df,
        x="pc1",
        y="pc2",
        color="cluster_label",
        hover_name="name",
        labels={
            "pc1": "Componente Principal 1 (PC1)",
            "pc2": "Componente Principal 2 (PC2)",
            "cluster_label": "Grupo Táctico"
        },
        color_discrete_sequence=["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"],
    )

    sel_pca = pca_df[pca_df["is_selected"]]
    if not sel_pca.empty:
        fig_kmeans.add_trace(go.Scatter(
            x=sel_pca["pc1"],
            y=sel_pca["pc2"],
            mode="markers+text",
            marker=dict(
                size=24,
                color="rgba(220, 38, 38, 0.12)",
                line=dict(width=2.5, color="#dc2626"),
                symbol="circle",
            ),
            text=[f"  {sp['name']}"],
            textposition="top right",
            textfont=dict(size=12, color="#0f172a", family="Inter"),
            name=f"Objetivo: {sp['name']}",
            showlegend=True,
            hoverinfo="name",
        ))

    fig_kmeans.update_layout(
        height=380,
        template="plotly_white",
        font=dict(family="Inter", size=11, color="#475569"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.28,
            xanchor="center",
            x=0.5,
            font=dict(size=10),
        ),
        margin=dict(l=35, r=20, t=15, b=50),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=True, zerolinecolor="#e2e8f0"),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=True, zerolinecolor="#e2e8f0"),
    )

    st.plotly_chart(fig_kmeans, use_container_width=True, key="kmeans_plot")

    ev = clustering.get("explained_variance", [])
    if len(ev) >= 2:
        st.caption(
            f"Varianza explicada acumulada: PC1 = {ev[0]:.1%}, PC2 = {ev[1]:.1%} · "
            f"K = {clustering['n_clusters']} clusters óptimos detectados por método del codo."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FILA CENTRAL:  Top 10 Jugadores Más Parecidos (st.dataframe con Column Config)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
total_analyzed = data.get("total_players_analyzed", len(similar))
st.markdown(f"""
<div class="section-title-wrap">
    <h4 class="section-title">Top 10 Jugadores de Perfil Más Parecido</h4>
    <span class="section-tag">{total_analyzed} futbolistas analizados en el universo de datos</span>
</div>
""", unsafe_allow_html=True)

# Construir DataFrame estructurado para la tabla interactiva
table_data = []
for p in similar:
    st_data = p.get("stats", {})
    table_data.append({
        "#": f"#{p['rank']}",
        "Foto": p.get("photo") or "https://media.api-sports.io/football/players/placeholder.png",
        "Futbolista": p["name"],
        "Escudo": p.get("team_logo") or "",
        "Club": p.get("team_name", ""),
        "Competición": p.get("league_name", ""),
        "Similitud": float(p["similarity"]),
        "PJ": int(st_data.get("PJ", 0)),
        "G": int(st_data.get("G", 0)),
        "AS": int(st_data.get("AS", 0)),
        "PC": int(st_data.get("PC", 0)),
        "%P": float(st_data.get("%P", 0)),
        "TR": int(st_data.get("TR", 0)),
        "RC": int(st_data.get("RC", 0)),
        "ER": int(st_data.get("ER", 0)),
        "ID": int(st_data.get("ID", 0)),
        "AM": int(st_data.get("AM", 0)),
    })

df_similar_table = pd.DataFrame(table_data)

st.dataframe(
    df_similar_table,
    column_config={
        "#": st.column_config.TextColumn("Rank", width="small"),
        "Foto": st.column_config.ImageColumn("Foto", width="small"),
        "Futbolista": st.column_config.TextColumn("Futbolista", width="medium"),
        "Escudo": st.column_config.ImageColumn("Escudo", width="small"),
        "Club": st.column_config.TextColumn("Club", width="medium"),
        "Competición": st.column_config.TextColumn("Competición", width="small"),
        "Similitud": st.column_config.ProgressColumn(
            "Similitud",
            format="%.1f%%",
            min_value=0.0,
            max_value=1.0,
            width="medium",
        ),
        "PJ": st.column_config.NumberColumn("PJ", format="%d"),
        "G": st.column_config.NumberColumn("Goles", format="%d"),
        "AS": st.column_config.NumberColumn("Asist.", format="%d"),
        "PC": st.column_config.NumberColumn("Pases", format="%d"),
        "%P": st.column_config.NumberColumn("% Acierto", format="%.0f%%"),
        "TR": st.column_config.NumberColumn("Tiros", format="%d"),
        "RC": st.column_config.NumberColumn("Regates", format="%d"),
        "ER": st.column_config.NumberColumn("Entradas", format="%d"),
        "ID": st.column_config.NumberColumn("Interc.", format="%d"),
        "AM": st.column_config.NumberColumn("Amarillas", format="%d"),
    },
    hide_index=True,
    use_container_width=True,
    height=280,
)

# Glosario sobrio
st.markdown("""
<div class="glossary-card">
    <b>Glosario de variables:</b> <b>PJ</b> = Partidos Jugados · <b>G</b> = Goles · <b>AS</b> = Asistencias · 
    <b>PC</b> = Pases Completados · <b>%P</b> = % Acierto de Pases · <b>TR</b> = Tiros Intentados · 
    <b>RC</b> = Regates Completados · <b>ER</b> = Entradas Realizadas · <b>ID</b> = Intercepciones Defensivas · <b>AM</b> = Tarjetas Amarillas
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FILA INFERIOR:  8 Gráficos de Barras Comparativos (Opta Benchmark Style)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
top1_name = comparison.get("top1_name", "Top 1")
st.markdown(f"""
<div class="section-title-wrap">
    <h4 class="section-title">Benchmark de Rendimiento Relativo</h4>
    <span class="section-tag">{sp['name']} vs {top1_name} vs Promedio de Cluster</span>
</div>
""", unsafe_allow_html=True)

STAT_LABELS = {
    "G": "Goles (por 90 min)",
    "AS": "Asistencias (Total)",
    "PC": "Pases Completados (por 90 min)",
    "TR": "Tiros (por 90 min)",
    "RC": "Regates (por 90 min)",
    "ER": "Entradas (por 90 min)",
    "ID": "Intercepciones (por 90 min)",
    "AM": "Tarjetas Amarillas (Total)",
}
STAT_KEYS = list(STAT_LABELS.keys())

BAR_COLORS = ["#0f172a", "#0d9488", "#94a3b8"]
BAR_NAMES = [sp["name"][:16], top1_name[:16], "Media Cluster"]

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
            marker=dict(
                color=BAR_COLORS,
                line=dict(width=1, color="rgba(0,0,0,0.06)"),
            ),
            text=[f"{v:.2f}" if isinstance(v, float) else str(v) for v in values],
            textposition="outside",
            textfont=dict(size=11, family="Inter", color="#0f172a"),
            cliponaxis=False,
        ))

        fig.update_layout(
            title=dict(
                text=label,
                font=dict(size=12, family="Inter", color="#334155"),
                x=0.5,
                y=0.92,
            ),
            height=210,
            template="plotly_white",
            showlegend=False,
            font=dict(family="Inter"),
            margin=dict(l=15, r=15, t=35, b=20),
            yaxis=dict(
                showgrid=True,
                gridcolor="#f1f5f9",
                rangemode="tozero",
                tickfont=dict(size=9, color="#64748b"),
            ),
            xaxis=dict(
                tickfont=dict(size=10, color="#1e293b", family="Inter"),
            ),
        )

        with col:
            st.plotly_chart(fig, use_container_width=True, key=f"bar_{key}")
