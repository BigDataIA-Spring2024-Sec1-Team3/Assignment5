# Description: This file contains the code to generate a knowledge base from a given CSV file. The knowledge base is used to generate question banks.
import streamlit as st
from backend import generate_knowledge_base as gen
import pandas as pd

def show_generate_knowledge_base():

    st.title("Generate Knowledge Base")

    st.write("This page is used to generate a knowledge base from a given CSV file. The knowledge base is used to generate question banks.")

    if 'df' not in st.session_state:
        st.session_state.df = pd.DataFrame()

    st.title("Query Data")
    df = pd.DataFrame()

    st.session_state.df = gen.fetch_data_from_snowflake()
    st.dataframe(st.session_state.df)

    # Apply filters only if the DataFrame is not empty
    if not st.session_state.df.empty:
        # Filtering UI
        st.title("Filter options:")
        selected_filters = {}
        column = 'topic_name'
        if column in st.session_state.df.columns:
            unique_values = pd.unique(st.session_state.df[column].astype(str))
            selected_values = st.multiselect(
                f"Filter {column} by:", options=unique_values, key=column)
            if selected_values:
                selected_filters[column] = selected_values
                # Apply filters to DataFrame if any filters are selected
                if selected_filters:
                    filtered_df = st.session_state.df.copy()
                    for column, values in selected_filters.items():
                        filtered_df = filtered_df[filtered_df[column].isin(
                            values)]
                        filtered_df = gen.filter_dataframe(filtered_df, values)
                        st.dataframe(filtered_df)

                if st.button("Generate Documents"):
                    final_df = gen.generate_technical_documents(filtered_df)
                    markdown_file_path = gen.generate_markdown_file(final_df)

                    # Read the generated markdown file
                    with open(markdown_file_path, 'r') as file:
                        markdown_content = file.read()

                    # Display success message with the path to the markdown file
                    st.success(
                        f"Markdown file generated and displayed below: {markdown_file_path}")

                    # Display markdown content
                    st.markdown(markdown_content, unsafe_allow_html=True)

                    # Provide a download link for the markdown file
                    with open(markdown_file_path, "rb") as file:
                        btn = st.download_button(
                            label="Download Markdown File",
                            data=file,
                            file_name="technical_documents_markdown.md",
                            mime="text/markdown"
                        )
                    st.title ("Storing the embedded data to Pinecone")
                    st.write("Based on the data above, we need to chunk and embed the data to store it in Pinecone. Click the button below to store the data.")
                    st.button("Store Data")

                    
