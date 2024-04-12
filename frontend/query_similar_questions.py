import streamlit as st


def show_rag_using_similar_questions():

    st.title("Question Answering System with Vector Database")

    st.markdown("""
    This page is used to generate answers to questions from Set B using a vector database. The system employs the Retrieval-Augmented Generation (RAG) model to search for similar questions in Set A, and then utilizes GPT-4 to generate answers based on the retrieved questions' answers. Instead of providing direct answers, the system references similar questions and their answers from Set A to infer responses for questions in Set B. The accuracy of the answers is evaluated against the correct answers determined in the process.
    """)

    try:
        # Button to trigger backend function
        if st.button("Run Question Answering System"):
            # Run the backend function
            correct_answers = compare_questions.main()

            # Display the result
            st.write(
                f"Number of correctly guessed answers from Set B: {correct_answers}")

    except Exception as e:
        st.error(f"An error occurred: {e}")
