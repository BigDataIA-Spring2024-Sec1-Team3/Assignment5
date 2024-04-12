import streamlit as st
import pandas as pd


def show_generate_question_banks():

    st.title("Generate Question Banks")

    st.write("This page is used to generate question banks from a knowledge base. The question banks are used to train the RAG model to answer questions based on the knowledge base.")

    st.header("Set A")

    data1 = pd.read_csv(
        'backend/generate_ques_bank/qa_df_set_a_qa.csv', sep='|')
    data1 = data1.drop(columns=['Unnamed: 0'], axis=1)
    st.dataframe(data1)

    st.header("Set B")
    data2 = pd.read_csv(
        'backend/generate_ques_bank/qa_df_set_b_qa.csv', sep='|')
    data2 = data2.drop(columns=['Unnamed: 0'], axis=1)
    st.dataframe(data2)
