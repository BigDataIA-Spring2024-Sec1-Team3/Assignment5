from cgitb import text
from uuid import uuid4
from tqdm.auto import tqdm
import time
from pinecone import PodSpec
from pinecone import Pinecone
from json import load
from langchain.embeddings.openai import OpenAIEmbeddings
import configparser
import os
import tiktoken
from langchain_community.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from io import BytesIO, StringIO
import re
import boto3
import pandas as pd
import configparser
from langchain.vectorstores import Pinecone
from langchain_core.messages import HumanMessage, SystemMessage


config = configparser.RawConfigParser()
config.read('./configuration.properties')
api_key = config['PINECONE']['PINECONE_API_KEY']
environment = config['PINECONE']['PINECONE_ENVIRONMENT']
OPENAI_API_KEY = config['OPENAI']['OPENAI_API_KEY']


def load_data():
    loader1 = CSVLoader('./backend/output/technical_documents.csv')
    doc = loader1.load()
    # Assuming `documents` is a list of Document objects
    list_of_dictionaries = [
        {
            'page_content': docs.page_content,
            'metadata': {
                'source': docs.metadata['source'],
                'row': docs.metadata['row']
            }
        } for docs in doc
    ]
    return list_of_dictionaries


def placeholder_for_storing_knowledge_embeddings_using_pinecone():

    tiktoken.encoding_for_model('gpt-3.5-turbo')
    tokenizer = tiktoken.get_encoding('cl100k_base')
    text = "This is a test text to check the length of the text"

    # create the length function
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    tiktoken_len = len(tokens)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=150,
        chunk_overlap=20,
        length_function=tiktoken_len,
        separators=["\n", ":", "", "\n\n"]
    )

    model_name = 'text-embedding-ada-002'

    embed = OpenAIEmbeddings(
        model=model_name,
        openai_api_key=OPENAI_API_KEY
    )


def chunk_and_embed_data():
    # load data
    list_of_dictionaries = load_data()

    # configure client
    pc = Pinecone(api_key=api_key)
    spec = PodSpec(environment=environment)
    index_name = 'assigmment4'

    if index_name in pc.list_indexes().names():
        pc.delete_index(index_name)

    # we create a new index
    pc.create_index(
        index_name,
        dimension=1536,  # dimensionality of text-embedding-ada-002
        metric='cosine',
        spec=spec
    )

    # wait for index to be initialized
    while not pc.describe_index(index_name).status['ready']:
        time.sleep(1)

    index = pc.Index(index_name)
    # wait a moment for connection
    time.sleep(1)

    batch_limit = 100

    texts = []
    metadatas = []

    for i, record in enumerate(tqdm(list_of_dictionaries)):
        # first get metadata fields for this record
        metadata = {
            'source': record['metadata']['source'],
            'id': record['metadata']['row']
        }
        # now we create chunks from the record text
        record_texts = placeholder_for_storing_knowledge_embeddings_using_pinecone.text_splitter.split_text(
            record['page_content'])
        # create individual metadata dicts for each chunk
        record_metadatas = [{
            "chunk": j, "text": text, **metadata
        } for j, text in enumerate(record_texts)]
        # append these to current batches
        texts.extend(record_texts)
        metadatas.extend(record_metadatas)
        # if we have reached the batch_limit we can add texts
        if len(texts) >= batch_limit:
            ids = [str(uuid4()) for _ in range(len(texts))]
            embeds = placeholder_for_storing_knowledge_embeddings_using_pinecone.embed.embed_documents(
                texts)
            index.upsert(vectors=zip(ids, embeds, metadatas))
            texts = []
            metadatas = []

    if len(texts) > 0:
        ids = [str(uuid4()) for _ in range(len(texts))]
        embeds = placeholder_for_storing_knowledge_embeddings_using_pinecone.embed.embed_documents(
            texts)
        index.upsert(vectors=zip(ids, embeds, metadatas))
        print(index.describe_index_stats())


def similarity_search(query):

    text_field = "text"  # the metadata field that contains our text
    index = "assigmment4"  # the name of the index we created
    embed = OpenAIEmbeddings(
        model='text-embedding-ada-002',
        openai_api_key=OPENAI_API_KEY
    )

    # initialize the vector store object
    vectorstore = Pinecone(
        index, embed.embed_query, text_field
    )

    response = vectorstore.similarity_search(
        query,  # our search query
        k=3  # return 3 most relevant docs
    )

    return response


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
        row['question'], similarity_search(row['question'])), axis=1)

    new_df.to_csv(
        './backend/output/qa_df_set_a_b_qa_with_openai_response.csv', index=False)

    return new_df


qa_using_ks()
