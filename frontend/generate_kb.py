# Description: This file contains the code to generate a knowledge base from a given CSV file. The knowledge base is used to generate question banks.
import streamlit as st
import pandas as pd
import backend.generate_knowledge_base as gen
import configparser


def show_generate_knowledge_base():

    st.title("Generate Knowledge Base")

    st.write("This page is used to generate a knowledge base from a given CSV file. The knowledge base is used to generate question banks.")

    if 'df' not in st.session_state:
        st.session_state.df = pd.DataFrame()

    st.title("Queried Data")
    df = pd.DataFrame()

    st.session_state.df = gen.fetch_data_from_snowflake()
    st.dataframe(st.session_state.df)

    st.title("Show Documents")
    st.write("Follwing are the technical documents.")
    # Load Markdown file
    with open('backend/output/technical_documents_markdown.md', 'r', encoding='utf-8') as file:
        markdown_content = file.read()

    # Display the Markdown in the app
    st.markdown(markdown_content)
