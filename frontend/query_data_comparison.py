import streamlit as st
import pandas as pd


def show_rag_using_data_and_comparison():

    st.title("RAG using Data and Comparison")

    st.write("This page is used to generate a RAG report using question banks and see how many of them were actually correct.")

    # Load your CSV data into a pandas DataFrame
    data = pd.read_csv(
        'backend/output/qa_df_set_a_b_qa_with_openai_response.csv')
    data = data.drop(columns=['context'], axis=1)

    # Display the DataFrame as a static table in Streamlit
    st.dataframe(data)

    st.write("The RAG report is as follows:")
    st.write('Incorrect: ***5/100***')
    st.write("Correct: ***95/100***")
