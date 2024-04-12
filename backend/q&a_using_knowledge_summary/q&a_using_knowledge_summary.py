from langchain.chat_models import ChatOpenAI
from io import BytesIO, StringIO
import re
import boto3
import pandas as pd
import configparser
from langchain.vectorstores import Pinecone
from langchain_core.messages import HumanMessage, SystemMessage
import sys
import os
import storing_knowledge_embeddings_using_pinecone

config = configparser.ConfigParser()
config.read('configuration.properties')


def aws_connection():
    try:
        # s3 connection details
        aws_access_key = config['AWS']['access_key']
        aws_secret_key = config['AWS']['secret_key']
        bucket_name = config['AWS']['bucket']
        txt_file_folder = config['AWS']['txt_file_folder_name']
        analysis_folder_name = config['AWS']['analysis_folder_name']
        question_sets_folder_name = config['AWS']['question_folder_name']

        s3_boto3_client = boto3.client(
            's3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)

        return s3_boto3_client, bucket_name, analysis_folder_name, txt_file_folder, question_sets_folder_name

    except Exception as e:
        print("Exception in aws_connection function: ", e)
        return


def fetch_from_s3():

    s3_client, bucket_name, analysis_folder_name, txt_file_folder, question_sets_folder_name = aws_connection()

    key_path1 = question_sets_folder_name + 'qa_df_set_a_qa.csv'
    response1 = s3_client.get_object(Bucket=bucket_name, Key=key_path1)
    # Get the object containing the text file content
    key_path2 = question_sets_folder_name + 'qa_df_set_b_qa.csv'
    response2 = s3_client.get_object(Bucket=bucket_name, Key=key_path2)

    print("file received from S3 bucket")

    # fetching raw csv
    csv_obj_content1 = response1['Body'].read()
    csv_obj_content2 = response2['Body'].read()

    # file like object creation
    pdfFileObj1 = BytesIO(csv_obj_content1)
    pdfFileObj2 = BytesIO(csv_obj_content2)
    quest_ans_df1 = pd.read_csv(pdfFileObj1, sep="|")
    quest_ans_df2 = pd.read_csv(pdfFileObj2, sep="|")
    result_df = pd.concat([quest_ans_df1, quest_ans_df2], ignore_index=True)
    result_df.to_csv('./output/qa_df_set_a_b_qa.csv', index=False)

    return result_df


def generate_openai_response(query, context):

    api_key = config['OPENAI']['OPENAI_API_KEY']
    print("attempting to connect to openai")

    llm = ChatOpenAI(
        openai_api_key=api_key,
        model_name='gpt-3.5-turbo',
        temperature=0.0,
        max_tokens=2048,
        frequency_penalty=0.1,
        presence_penalty=0.1,
    )

    messages = [
        SystemMessage(content="You are an AI chat assistant based on the provided CONTEXT below. You will be provided with a question having multiple answer choices, out of which only one is correct. You have to answer the Question strictly from the CONTEXT. Ensure that your responses are solely derived from the CONTEXT provided, without being open-ended.\n\nCONTEXT:\n" + context),
        HumanMessage(content=query)
    ]

    response = llm.invoke(messages)
    response = response.content

    return response


def qa_using_ks():

    df = fetch_from_s3()
    df = df.drop(columns=['Unnamed: 0'], axis=1)
    new_df = df.copy()

    # Use a lambda function to apply 'generate_openai_response' to both 'question' and 'answer' columns
    new_df['openai_response'] = new_df.apply(lambda row: generate_openai_response(
        row['question'], storing_knowledge_embeddings_using_pinecone.similarity_search(row['question'])), axis=1)

    new_df.to_csv(
        './backend/output/qa_df_set_a_b_qa_with_openai_response.csv', index=False)

    return new_df


qa_using_ks()
