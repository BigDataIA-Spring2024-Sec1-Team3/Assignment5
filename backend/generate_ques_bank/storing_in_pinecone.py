import boto3
import json
import configparser
from io import BytesIO, StringIO
import pandas as pd
from openai import OpenAI
from pinecone import Pinecone

def aws_connection():
    try:
        # AWS details fetch
        config = configparser.ConfigParser()
        config.read('configuration.properties')
        
        # s3 connection details
        aws_access_key = config['AWS']['access_key']
        aws_secret_key = config['AWS']['secret_key']
        bucket_name = config['AWS']['bucket']
        txt_file_folder = config['AWS']['txt_file_folder_name']
        analysis_folder_name = config['AWS']['analysis_folder_name']
        question_sets_folder_name = config['AWS']['question_folder_name']
        
        s3_boto3_client = boto3.client('s3', aws_access_key_id= aws_access_key, aws_secret_access_key=aws_secret_key)
        
        return s3_boto3_client, bucket_name, analysis_folder_name, txt_file_folder, question_sets_folder_name
    
    except Exception as e:
        print("Exception in aws_connection function: ",e)
        return 
  
def openai_connection():
    try:
        # OpenAI details fetch
        config = configparser.ConfigParser()
        config.read('configuration.properties')
        
        openai_api_key = config['OPENAI']['api_key']

        return openai_api_key
        
    except Exception as e:
        print("Exception in openai_connection function: ",e)
        return 
    
def pinecone_connection():
    try:
        # OpenAI details fetch
        config = configparser.ConfigParser()
        config.read('configuration.properties')
        
        pinecone_api_key = config['PINECONE']['pinecone_api_key']
        index_name = config['PINECONE']['index']

        return pinecone_api_key, index_name
        
    except Exception as e:
        print("Exception in openai_connection function: ",e)
        return  

def storing_pinecone():
    '''
    function to store set a in pinecone
    '''
    try:
        # aws
        s3_client, bucket_name, analysis_folder_name, txt_file_folder, question_sets_folder_name = aws_connection()
        
        # openai
        key = openai_connection()
        openai_client = OpenAI(api_key=key)
        
        # Pinecone
        pinecone_api_key, index_name = pinecone_connection()
        pinecone = Pinecone(api_key=pinecone_api_key)
        index = pinecone.Index(name=index_name)
        
        # Get the object containing the text file content
        key_path = question_sets_folder_name + 'qa_df_set_a_qa.csv'
        response = s3_client.get_object(Bucket=bucket_name, Key=key_path)
        
        print("file received from S3 bucket")
        
        # fetching raw csv
        csv_obj_content = response['Body'].read()
        
        # csv data into pandas dataframe
        pdfFileObj = BytesIO(csv_obj_content)
        quest_ans_df = pd.read_csv(pdfFileObj, sep="|")  
        print(quest_ans_df)
        
        embedded_data_questions = []
        embedded_data_answers = []
        
        # iterating over pandas dataframe
        print("Generating embeddings..")
        for _, row in quest_ans_df.iterrows():
            _id = str(row['Unnamed: 0'])
            ques = row['question']
            ans = row['answer']
            
            # embedding question
            embedded_question= openai_client.embeddings.create(
                    input=ques,
                    model = 'text-embedding-ada-002',
                ).data[0].embedding

            print(f"Embedded question for {_id}")
            
            temp_ques = {
                "id": _id,
                "values": embedded_question,
                "metadata":{
                    "qa_id": _id,
                    "file_name": 'qa_df_set_b_qa.csv',
                    "filed": "question"
                }
            }
           
            # embedding answer   
            embedded_answers = openai_client.embeddings.create(
                    input=ans,
                    model = 'text-embedding-ada-002',
                ).data[0].embedding
            
            print(f"Embedded answer for {_id}")
            
            temp_answer = {
                "id": _id,
                "values": embedded_answers,
                "metadata":{
                    "qa_id": _id,
                    "file_name": 'qa_df_set_b_qa.csv',
                    "filed": "answer"
                }
            }

            # embedding question and answer separately
            embedded_data_questions.append(temp_ques)
            embedded_data_answers.append(temp_answer)
        
        print("Embeddings generated for questions and answers")
        
        # upserting the embeddings to pinecone namespace
        index.upsert(embedded_data_questions, namespace='question')
        index.upsert(embedded_data_answers, namespace='answer')              
        
        return "successful"
    
    except Exception as e:
        print("Exception in storing_pinecone() function: ",e)
        return "failed"
    
if __name__ == "__main__":
    # function to store data into pinecone
    res = storing_pinecone()
    

    