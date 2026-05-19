import streamlit as st

from config import PAGE_TITLE, MAIN_TITLE, UPDATE_MESSAGE


def render_page_layout():
    st.set_page_config(layout="wide", page_title=PAGE_TITLE)

    st.markdown(
        """
        <style>
        [data-testid="stMetric"] {
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            background-color: #ffffff;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
            font-weight: 700;
        }

        div.stAlert > div {
            border-radius: 10px;
        }

        .yolo-box {
            background-color: #f0fdf4;
            border: 2px solid #22c55e;
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            margin-bottom: 20px;
        }

        .yolo-title {
            color: #166534;
            font-size: 1.4rem;
            font-weight: 700;
            margin: 0;
        }

        .yolo-value {
            color: #15803d;
            font-size: 2.2rem;
            font-weight: 800;
            margin: 10px 0 0 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title(MAIN_TITLE)
    st.info(UPDATE_MESSAGE)
    st.markdown("---")