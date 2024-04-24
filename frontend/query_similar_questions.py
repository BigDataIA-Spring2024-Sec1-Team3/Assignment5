import streamlit as st
import backend.compare_questions as cq
import pandas as pd
import matplotlib.pyplot as plt

def show_rag_using_similar_questions():

    st.title("Question Answering System with Vector Database")

    st.markdown("""
    This page is used to generate answers to questions from Set B using a vector database. The system employs the Retrieval-Augmented Generation (RAG) model to search for similar questions in Set A, and then utilizes GPT-4 to generate answers based on the retrieved questions' answers. Instead of providing direct answers, the system references similar questions and their answers from Set A to infer responses for questions in Set B. The accuracy of the answers is evaluated against the correct answers determined in the process.
    """)
    
    try:
        # Button to trigger backend function
        if st.button("Run Question Answering System"):
            
            s3_client, bucket_name, part3_filename, part3_folder = cq.aws_connection()
            response = s3_client.get_object(Bucket=bucket_name, Key=part3_folder+part3_filename)
       
            report_df = pd.read_csv(response['Body'], sep='|')
            counts = report_df["Match"].value_counts()
            
            # Create pie chartfig
            fig, ax = plt.subplots() 
            ax.pie(counts, labels=['Correct','Incorrect'], autopct='%1.1f%%', startangle=90, explode=(0, 0.1)) 
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
            
            # Display pie chart in Streamlitst
            st.write("Ratio of correct and incorrect answers")
            st.write("Correct answers: ", counts[1]) 
            st.write("Incorrect answers: ", counts[0]) 
            st.pyplot(fig)

    except Exception as e:
        st.error(f"An error occurred: {e}")
