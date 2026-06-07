import streamlit as st

from database_datasources.components.database_datasources_container import (
    render_database_datasources_container,
)

st.subheader("Datasets")
st.caption("Configure datasets from database connections.")
st.divider()

render_database_datasources_container()


