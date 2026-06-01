import html
from datetime import datetime

import streamlit as st


def esc(v):
    return html.escape(str(v or ""))


def load_styles():
    st.markdown(
        """
        <style>
        :root{
            --navy:#0f172a;
            --navy-2:#172554;
            --blue:#2563eb;
            --cyan:#0891b2;
            --green:#059669;
            --amber:#d97706;
            --red:#dc2626;
            --bg:#f5f8fc;
            --card:#ffffff;
            --line:#dbe4ef;
            --text:#111827;
            --muted:#64748b;
            --shadow:0 16px 42px rgba(15,23,42,.09);
            --soft-shadow:0 8px 22px rgba(15,23,42,.055);
        }

        html, body, [data-testid="stAppViewContainer"]{
            background:
                linear-gradient(180deg, rgba(248,250,252,.98) 0%, rgba(236,244,255,.96) 100%),
                radial-gradient(circle at 80% 0%, rgba(37,99,235,.12), transparent 28%);
        }

        .block-container{
            padding-top:1.25rem;
            padding-bottom:2.5rem;
            max-width:1320px;
        }

        h1{
            font-weight:900!important;
            letter-spacing:0!important;
            color:var(--text);
            margin-bottom:.2rem!important;
        }

        h2,h3{
            letter-spacing:0!important;
            color:var(--text);
        }

        .page-subtitle{
            color:var(--muted);
            font-size:1.02rem;
            margin-bottom:1.1rem;
        }

        .top-hero{
            position:relative;
            overflow:hidden;
            background:
                radial-gradient(circle at 88% 12%,rgba(34,211,238,.42),transparent 30%),
                linear-gradient(135deg,#0f172a 0%,#1d4ed8 60%,#0ea5e9 100%);
            border:1px solid rgba(255,255,255,.32);
            border-radius:8px;
            padding:1.55rem 1.65rem;
            margin:.45rem 0 1.15rem 0;
            color:white;
            box-shadow:0 22px 48px rgba(37,99,235,.22);
        }

        .top-hero:after{
            content:"";
            position:absolute;
            inset:auto -40px -70px auto;
            width:260px;
            height:160px;
            background:rgba(255,255,255,.12);
            transform:rotate(-12deg);
            border-radius:8px;
        }

        .top-hero h2{
            color:white;
            margin:0 0 .35rem 0;
            font-size:1.5rem;
            font-weight:900;
        }

        .top-hero p{
            color:#e0f2fe;
            max-width:900px;
            margin:0;
            line-height:1.55;
            position:relative;
            z-index:1;
        }

        .kpi-card{
            background:rgba(255,255,255,.96);
            border:1px solid var(--line);
            border-radius:8px;
            padding:1rem 1.05rem;
            min-height:126px;
            box-shadow:var(--shadow);
            display:flex;
            flex-direction:column;
            justify-content:space-between;
            transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease;
        }

        .kpi-card:hover{
            transform:translateY(-2px);
            box-shadow:0 18px 45px rgba(15,23,42,.12);
            border-color:#bfdbfe;
        }

        .kpi-top{
            display:flex;
            justify-content:space-between;
            gap:.8rem;
            align-items:flex-start;
        }

        .kpi-icon{
            height:40px;
            width:40px;
            border-radius:8px;
            display:grid;
            place-items:center;
            background:#eff6ff;
            color:#1d4ed8;
            font-size:1.12rem;
            border:1px solid #dbeafe;
            flex:0 0 auto;
        }

        .kpi-label{
            font-size:.76rem;
            color:var(--muted);
            font-weight:850;
            text-transform:uppercase;
            letter-spacing:.055em;
            margin-bottom:.36rem;
        }

        .kpi-value{
            color:var(--text);
            font-size:2rem;
            font-weight:900;
            line-height:1.05;
        }

        .kpi-help{
            color:var(--muted);
            font-size:.86rem;
            margin-top:.45rem;
        }

        .panel{
            background:rgba(255,255,255,.96);
            border:1px solid var(--line);
            border-radius:8px;
            padding:1.1rem;
            box-shadow:var(--soft-shadow);
            margin-bottom:1rem;
        }

        .panel-title{
            font-size:1.03rem;
            font-weight:850;
            color:var(--text);
            margin-bottom:.25rem;
        }

        .panel-caption{
            color:var(--muted);
            font-size:.9rem;
            margin-bottom:.85rem;
        }

        .badge{
            display:inline-flex;
            align-items:center;
            padding:.32rem .68rem;
            border-radius:999px;
            font-size:.78rem;
            font-weight:850;
            border:1px solid transparent;
            margin:.12rem .2rem .12rem 0;
            white-space:nowrap;
        }

        .badge-new{background:#eff6ff;color:#1d4ed8;border-color:#bfdbfe}
        .badge-review{background:#fff7ed;color:#c2410c;border-color:#fed7aa}
        .badge-answered{background:#ecfdf5;color:#047857;border-color:#a7f3d0}
        .badge-escalated{background:#fee2e2;color:#b91c1c;border-color:#fecaca}
        .badge-closed{background:#f1f5f9;color:#334155;border-color:#cbd5e1}
        .badge-low{background:#dcfce7;color:#166534;border-color:#bbf7d0}
        .badge-medium{background:#fef9c3;color:#854d0e;border-color:#fde68a}
        .badge-high{background:#ffedd5;color:#9a3412;border-color:#fed7aa}
        .badge-critical{background:#fee2e2;color:#991b1b;border-color:#fecaca}
        .badge-info{background:#dbeafe;color:#1e40af;border-color:#bfdbfe}
        .badge-neutral{background:#f1f5f9;color:#334155;border-color:#e2e8f0}
        .badge-negative{background:#fee2e2;color:#991b1b;border-color:#fecaca}
        .badge-positive{background:#dcfce7;color:#166534;border-color:#bbf7d0}

        .case-card{
            background:white;
            border:1px solid var(--line);
            border-radius:8px;
            padding:1rem 1.05rem;
            margin-bottom:.7rem;
            box-shadow:var(--soft-shadow);
            transition:transform .14s ease, border-color .14s ease;
        }

        .case-card:hover{
            transform:translateY(-1px);
            border-color:#bfdbfe;
        }

        .case-title{
            font-weight:850;
            color:var(--text);
            font-size:1rem;
            margin-bottom:.35rem;
        }

        .muted{color:var(--muted);font-size:.88rem;}

        .analysis-grid{
            display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));
            gap:.9rem;
            margin:1rem 0;
        }

        .analysis-card{
            background:#f8fafc;
            border:1px solid #e2e8f0;
            border-radius:8px;
            padding:1rem;
        }

        .analysis-label{
            color:#64748b;
            font-size:.76rem;
            text-transform:uppercase;
            font-weight:850;
            letter-spacing:.05em;
            margin-bottom:.35rem;
        }

        .analysis-value{
            font-size:1.12rem;
            font-weight:850;
            color:#0f172a;
        }

        .response-panel{
            display:grid;
            grid-template-columns:1.05fr 1.35fr .95fr;
            gap:1rem;
            align-items:stretch;
        }

        .response-box{
            background:linear-gradient(180deg,#fff 0%,#f8fbff 100%);
            border:1px solid #bfdbfe;
            border-left:5px solid #2563eb;
            border-radius:8px;
            padding:1.05rem 1.1rem;
            white-space:pre-wrap;
            line-height:1.6;
            color:#0f172a;
            min-height:230px;
        }

        .doc-card{
            background:#fff;
            border:1px solid #e2e8f0;
            border-radius:8px;
            padding:.9rem 1rem;
            margin-bottom:.7rem;
            box-shadow:0 7px 18px rgba(15,23,42,.04);
        }

        .doc-title{
            font-weight:850;
            color:#0f172a;
            margin-bottom:.25rem;
        }

        .alert-success,.alert-warn,.alert-error{
            padding:.85rem 1rem;
            border-radius:8px;
            font-weight:700;
            margin:.7rem 0;
        }
        .alert-success{background:#ecfdf5;border:1px solid #a7f3d0;color:#065f46;}
        .alert-warn{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;}
        .alert-error{background:#fef2f2;border:1px solid #fecaca;color:#991b1b;}

        div[data-testid="stDataFrame"]{
            border:1px solid var(--line);
            border-radius:8px;
            overflow:hidden;
            box-shadow:var(--soft-shadow);
        }

        .stButton>button{
            border-radius:8px;
            font-weight:800;
            border:1px solid #cbd5e1;
            padding:.58rem 1rem;
            transition:transform .12s ease, box-shadow .12s ease;
        }

        .stButton>button:hover{
            transform:translateY(-1px);
            box-shadow:0 8px 18px rgba(15,23,42,.10);
        }

        .stButton>button[kind="primary"]{
            background:linear-gradient(135deg,#2563eb,#1d4ed8);
            border-color:#1d4ed8;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stSelectbox"] div,
        div[data-testid="stDateInput"] input{
            border-radius:8px!important;
        }

        section[data-testid="stSidebar"]{
            background:linear-gradient(180deg,#0f172a 0%,#111827 45%,#172554 100%)!important;
            border-right:1px solid rgba(255,255,255,.08)!important;
        }

        section[data-testid="stSidebar"] *{color:#f8fafc!important;}

        section[data-testid="stSidebar"] > div{padding-top:.45rem!important;}

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"]::before{
            content:"SmartClaim AI";
            display:block;
            color:#ffffff;
            font-size:1.08rem;
            font-weight:900;
            padding:.9rem 1rem .15rem 1rem;
            letter-spacing:0;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"]::after{
            content:"Clasificador y gestor de reclamos";
            display:block;
            color:#93c5fd;
            font-size:.75rem;
            font-weight:650;
            padding:0 1rem .9rem 1rem;
            margin-bottom:.5rem;
            border-bottom:1px solid rgba(255,255,255,.10);
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul{
            padding-left:.65rem!important;
            padding-right:.65rem!important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li{
            margin-bottom:.22rem!important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a{
            color:#dbeafe!important;
            text-decoration:none!important;
            border-radius:8px!important;
            padding:.58rem .8rem!important;
            margin:.08rem 0!important;
            transition:all .16s ease-in-out!important;
            font-size:.94rem!important;
            font-weight:750!important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover{
            background:rgba(37,99,235,.22)!important;
            transform:translateX(3px);
            color:#ffffff!important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"]{
            background:linear-gradient(135deg,#2563eb,#1d4ed8)!important;
            color:#ffffff!important;
            font-weight:900!important;
            box-shadow:0 8px 18px rgba(37,99,235,.25);
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span,
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a p{
            color:inherit!important;
            font-weight:inherit!important;
            font-size:.94rem!important;
        }

        .sidebar-sync{
            color:#bfdbfe;
            font-size:.76rem;
            line-height:1.35;
            padding:.25rem .1rem .6rem .1rem;
        }

        @media(max-width:1000px){
            .analysis-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
            .response-panel{grid-template-columns:1fr;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown(
            f'<div class="sidebar-sync">Vista cargada: {datetime.now().strftime("%H:%M:%S")}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Actualizar pantalla", use_container_width=True):
            st.rerun()


def hero(title, subtitle):
    st.markdown(f'<div class="top-hero"><h2>{esc(title)}</h2><p>{esc(subtitle)}</p></div>', unsafe_allow_html=True)


def kpi(label, value, help_text="", icon="●"):
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-top"><div><div class="kpi-label">{esc(label)}</div>'
        f'<div class="kpi-value">{esc(value)}</div></div><div class="kpi-icon">{esc(icon)}</div></div>'
        f'<div class="kpi-help">{esc(help_text)}</div></div>',
        unsafe_allow_html=True,
    )


def panel_start(title=None, caption=None):
    t = f'<div class="panel-title">{esc(title)}</div>' if title else ""
    c = f'<div class="panel-caption">{esc(caption)}</div>' if caption else ""
    st.markdown(f'<div class="panel">{t}{c}', unsafe_allow_html=True)


def panel_end():
    st.markdown("</div>", unsafe_allow_html=True)


def badge(text, kind="neutral"):
    return f'<span class="badge badge-{kind}">{esc(text)}</span>'


def priority_badge(priority):
    return badge(
        priority,
        {
            "Baja": "low",
            "Media": "medium",
            "Alta": "high",
            "Crítica": "critical",
            "Critica": "critical",
            "Sin prioridad": "neutral",
        }.get(priority, "neutral"),
    )


def status_badge(status):
    return badge(
        status,
        {
            "Nuevo": "new",
            "Analizado por IA": "info",
            "En revisión": "review",
            "En revision": "review",
            "Respondido": "answered",
            "Escalado": "escalated",
            "Cerrado": "closed",
        }.get(status, "neutral"),
    )


def sentiment_badge(sentiment):
    return badge(sentiment, {"NEGATIVO": "negative", "POSITIVO": "positive", "NEUTRO": "neutral"}.get(sentiment, "neutral"))


def alert(message, kind="success"):
    css = {"success": "alert-success", "warn": "alert-warn", "error": "alert-error"}.get(kind, "alert-success")
    st.markdown(f'<div class="{css}">{esc(message)}</div>', unsafe_allow_html=True)


def analysis_grid(items):
    cards = "".join(
        f'<div class="analysis-card"><div class="analysis-label">{esc(a)}</div><div class="analysis-value">{esc(b)}</div></div>'
        for a, b in items
    )
    st.markdown(f'<div class="analysis-grid">{cards}</div>', unsafe_allow_html=True)
