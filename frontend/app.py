
import re
import streamlit as st
import generate_kb
import generate_qb
import query_similar_questions
import query_data_comparison
# Main app logic starts here
PAGES = {
    "Generate Knowledge Base": generate_kb,
    "Generate Question Banks": generate_qb,
    "RAG Using Similar Questions": query_similar_questions,
    "RAG Using Data and Comparison": query_data_comparison,
}

st.sidebar.title('Navigation')
selection = st.sidebar.radio("Go to", list(PAGES.keys()))
if selection:
    page = PAGES[selection]
    page_function = getattr(
        page, 'show_' + selection.lower().replace(' ', '_'))
    page_function()
