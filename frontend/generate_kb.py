# Description: This file contains the code to generate a knowledge base from a given CSV file. The knowledge base is used to generate question banks.
import streamlit as st
import pandas as pd
import backend.generate_knowledge_base as gen
# import backend.generate_ques_bank.create_question_banks as create_question_banks
import configparser


def show_generate_knowledge_base():

    st.title("Generate Knowledge Base")

    st.write("This page is used to generate a knowledge base from a given set of topics.")
    
    topic_dropdown = st.selectbox("Select Topic: ",['Overview of Equity Securities','Market Organization and Structure','Security Market Indexes'])
    conn, cfa_table, md_table = gen.snowflake_connection()
    cur = conn.cursor()
    
    fetch_los_query = f"SELECT LEARNING_OUTCOME FROM {md_table} WHERE TOPIC_NAME='{topic_dropdown}';"
    # print(fetch_los_query)
    cur.execute(fetch_los_query)
    
    los_res = cur.fetchall()
    filtered_los = []
    for los in los_res:
        filtered_los.append(los[0])
    # print(filtered_los)
    
    los_dropdown = st.selectbox("Select Learning Outcome: ", filtered_los)
    
    button_submitted= st.button("Load knowledge base")
    
    if button_submitted:
        fetch_kb_query = f"SELECT TECHNICAL_DOCUMENT FROM {md_table} WHERE TOPIC_NAME='{topic_dropdown}' AND LEARNING_OUTCOME='{los_dropdown}';"
        cur.execute(fetch_kb_query)
        
        kb_res = cur.fetchall()
        
        markdown_content = f"# {topic_dropdown}\n\n"
        markdown_content += f"## Learning Outcome:\n {los_dropdown}\n"
        markdown_content += f"### Technical Document:\n {kb_res[0][0]}\n\n"
        
        st.write(markdown_content)
        
    
    
