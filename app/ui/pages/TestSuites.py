import streamlit as st

from test_suites.components.test_suites_component import render_test_suites_page


st.subheader("Test Suites :material/experiment:")
st.caption("Create and manage test suites to group test cases and organize your testing efforts.")
st.divider()

render_test_suites_page()
