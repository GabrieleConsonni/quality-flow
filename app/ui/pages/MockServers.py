import streamlit as st

from mock_servers.components.mock_servers_component import render_mock_servers_component

st.subheader("Mock Servers")
st.caption("Configure API and queue mock triggers with async operations.")
st.divider()

render_mock_servers_component()
