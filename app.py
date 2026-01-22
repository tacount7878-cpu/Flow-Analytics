import streamlit as st

from sunburst_utils import build_figure_from_gsheets


st.set_page_config(page_title="Flow-Analytics Sunburst", layout="wide")

st.title("Flow-Analytics｜資產配置（地區 → 個股）")

try:
    fig = build_figure_from_gsheets()
    st.plotly_chart(fig, use_container_width=True)
except Exception as error:
    st.error(f"Error: {error}")
    st.stop()
