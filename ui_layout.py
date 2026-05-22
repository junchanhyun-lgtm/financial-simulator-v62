import streamlit as st

from config import PAGE_TITLE, MAIN_TITLE, UPDATE_MESSAGE


def render_page_layout():
    st.set_page_config(layout="wide", page_title=PAGE_TITLE)

    st.markdown(
        """
        <style>
        :root {
            --app-bg: #f5f7fb;
            --surface: #ffffff;
            --surface-soft: #f8fafc;
            --line: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --navy: #1e293b;
            --blue: #2563eb;
            --green: #16a34a;
            --amber: #d97706;
            --red: #dc2626;
            --shadow-soft: 0 10px 28px rgba(15, 23, 42, 0.08);
            --shadow-card: 0 5px 18px rgba(15, 23, 42, 0.06);
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.09), transparent 34rem),
                linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
        }

        [data-testid="stHeader"] {
            background: rgba(248, 250, 252, 0.78);
            backdrop-filter: blur(10px);
        }

        .main .block-container {
            padding-top: 1.4rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }

        h1, h2, h3, h4, h5 {
            color: var(--text-main);
            letter-spacing: -0.02em;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: rgba(148, 163, 184, 0.28) !important;
            box-shadow: var(--shadow-card);
            background: rgba(255, 255, 255, 0.84);
            border-radius: 18px;
        }

        [data-testid="stMetric"] {
            border: 1px solid rgba(226, 232, 240, 0.92);
            border-radius: 18px;
            padding: 18px 18px 16px 18px;
            box-shadow: var(--shadow-card);
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        }

        [data-testid="stMetricLabel"] {
            color: var(--text-muted);
            font-weight: 700;
        }

        [data-testid="stMetricValue"] {
            color: var(--text-main);
            font-size: 2.0rem !important;
            font-weight: 800;
            letter-spacing: -0.04em;
        }

        [data-testid="stMetricDelta"] {
            font-weight: 700;
        }

        div.stAlert > div {
            border-radius: 14px;
            border-width: 1px;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        }

        div[data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
            box-shadow: 0 5px 16px rgba(15, 23, 42, 0.04);
        }

        button[kind="tab"] {
            border-radius: 999px !important;
            padding: 0.35rem 1.0rem !important;
            font-weight: 700 !important;
        }

        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.35rem;
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(226, 232, 240, 0.92);
            border-radius: 999px;
            padding: 0.35rem;
            box-shadow: 0 5px 18px rgba(15, 23, 42, 0.05);
        }

        .app-header-card {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 52%, #334155 100%);
            color: #f8fafc;
            border-radius: 26px;
            padding: 28px 32px;
            margin-bottom: 18px;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.18);
            border: 1px solid rgba(255, 255, 255, 0.12);
        }

        .app-header-card .title {
            font-size: 2.0rem;
            font-weight: 850;
            letter-spacing: -0.045em;
            margin-bottom: 8px;
        }

        .app-header-card .subtitle {
            color: #cbd5e1;
            font-size: 0.98rem;
            line-height: 1.65;
        }

        .result-hero {
            background:
                linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.96)),
                radial-gradient(circle at top right, rgba(37, 99, 235, 0.50), transparent 28rem);
            color: #f8fafc;
            border-radius: 28px;
            padding: 28px 32px;
            margin: 14px 0 18px 0;
            box-shadow: 0 20px 46px rgba(15, 23, 42, 0.20);
            border: 1px solid rgba(255, 255, 255, 0.12);
        }

        .result-hero-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 18px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }

        .result-hero-title {
            font-size: 1.62rem;
            font-weight: 850;
            letter-spacing: -0.04em;
            margin-bottom: 7px;
        }

        .result-hero-subtitle {
            color: #cbd5e1;
            font-size: 0.96rem;
            line-height: 1.65;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 118px;
            border-radius: 999px;
            padding: 8px 14px;
            font-size: 0.88rem;
            font-weight: 800;
            border: 1px solid rgba(255, 255, 255, 0.18);
        }

        .status-success { background: rgba(22, 163, 74, 0.18); color: #bbf7d0; }
        .status-warning { background: rgba(217, 119, 6, 0.20); color: #fde68a; }
        .status-danger { background: rgba(220, 38, 38, 0.20); color: #fecaca; }
        .status-neutral { background: rgba(148, 163, 184, 0.18); color: #e2e8f0; }

        .kpi-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid rgba(226, 232, 240, 0.96);
            border-radius: 22px;
            padding: 20px 20px 18px 20px;
            box-shadow: var(--shadow-card);
            min-height: 132px;
        }

        .kpi-label {
            color: #64748b;
            font-size: 0.88rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            margin-bottom: 8px;
        }

        .kpi-value {
            color: #0f172a;
            font-size: 2.08rem;
            font-weight: 900;
            letter-spacing: -0.055em;
            line-height: 1.05;
            margin-bottom: 8px;
        }

        .kpi-subtitle {
            color: #64748b;
            font-size: 0.88rem;
            line-height: 1.45;
        }

        .kpi-card.success { border-top: 4px solid var(--green); }
        .kpi-card.warning { border-top: 4px solid var(--amber); }
        .kpi-card.danger { border-top: 4px solid var(--red); }
        .kpi-card.accent { border-top: 4px solid var(--blue); }
        .kpi-card.neutral { border-top: 4px solid #64748b; }

        .section-card {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(226, 232, 240, 0.94);
            border-radius: 22px;
            padding: 20px 22px;
            margin: 10px 0 18px 0;
            box-shadow: var(--shadow-card);
        }

        .section-title {
            font-size: 1.10rem;
            font-weight: 850;
            color: #0f172a;
            letter-spacing: -0.03em;
            margin: 0 0 4px 0;
        }

        .section-subtitle {
            color: #64748b;
            font-size: 0.91rem;
            line-height: 1.6;
            margin-bottom: 12px;
        }

        .risk-pill {
            display: inline-block;
            border-radius: 999px;
            padding: 5px 10px;
            font-weight: 800;
            font-size: 0.80rem;
            background: #eef2ff;
            color: #3730a3;
        }

        .fine-print {
            color: #64748b;
            font-size: 0.85rem;
            line-height: 1.6;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="app-header-card">
            <div class="title">{MAIN_TITLE}</div>
            <div class="subtitle">{UPDATE_MESSAGE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
