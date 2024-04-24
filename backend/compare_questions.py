from openai import OpenAI
import configparser
from pinecone import Pinecone
import csv
import pandas as pd
import boto3
import os

def openai_connection():
    try:
        # OpenAI details fetch
        config = configparser.ConfigParser()
        config.read('./configuration.properties')
        
        openai_api_key = config['OPENAI']['api_key']

        return openai_api_key
        
    except Exception as e:
        print("Exception in openai_connection function: ",e)
        return 
    
def pinecone_connection():
    try:
        # OpenAI details fetch
        config = configparser.ConfigParser()
        config.read('./configuration.properties')
        
        pinecone_api_key = config['PINECONE']['pinecone_api_key']
        index_name = config['PINECONE']['index']

        return pinecone_api_key, index_name
        
    except Exception as e:
        print("Exception in openai_connection function: ",e)
        return  
    
def fetch_question_answer(qa_id, set_a_file):
    with open(set_a_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='|')
        for i, row in enumerate(reader):
            if i == int(qa_id):
                return row['question'], row['answer']
    return None, None

def aws_connection():
    try:
        # AWS details fetch
        config = configparser.ConfigParser()
        config.read('backend/configuration.properties')
        
        # s3 connection details
        aws_access_key = config['AWS']['access_key']
        aws_secret_key = config['AWS']['secret_key']
        bucket_name = config['AWS']['bucket']
        part3_filename = config['AWS']['part3_filename']
        part3_folder = config['AWS']['part3_folder']
        
        s3_boto3_client = boto3.client('s3', aws_access_key_id= aws_access_key, aws_secret_access_key=aws_secret_key)
        
        return s3_boto3_client, bucket_name, part3_filename, part3_folder
    
    except Exception as e:
        print("Exception in aws_connection function: ",e)
        return 

def compare_SetA_SetB():
    try:
        openai_client = OpenAI(api_key=openai_connection())
        pinecone_api_key,index_name = pinecone_connection()
        pinecone = Pinecone(api_key=pinecone_api_key)
        index = pinecone.Index(name=index_name)

        # Load CSV files for Set A and Set B
        set_a_file = "./generate_ques_bank/qa_df_set_a_qa.csv"
        set_b_file = "./generate_ques_bank/qa_df_set_b_qa.csv"
        
        correct=0
        
        s3_client, bucket_name, part3_filename, part3_folder = aws_connection()
        
        with open(set_b_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='|')
            
            part3_report= pd.DataFrame(columns=['Question', 'GPT Explanation', 'GPT Answer', 'KB Answer', 'Match'])
            
            
            for row in reader:
                question = row["question"]
                answer = row["answer"]
                embedded_question = openai_client.embeddings.create(
                    input=question, 
                    model = 'text-embedding-ada-002',
                ).data[0].embedding
                xc = index.query(vector=embedded_question, top_k=3, include_metadata=True, namespace='question')
                
                context = ''

                for match in xc["matches"]:
                    qa_id = match['metadata']['qa_id']
                    question, answer = fetch_question_answer(qa_id, set_a_file)
                    if question and answer:
                        # Append question and answer to context with desired format
                        
                        context += f"Question: {question}\nAnswer: {answer}\n\n"
                        context = context.replace("1. Question:", "")
                        context = context.replace("Answer: :", "Answer:")

                prompt= f'''
                You are provided with a multiple choice question with 4 options out of which one is right. You are also also provided with 3 similar questions with their respective correct answers, which you need to use as reference to answer the question provided. Give me the correct answer choice with explanation justifying why you chose that answer. 
                Reference Questions with Answers:
                {context}
                Your question to answer:
                {question}
                I need your response strictly in the following format and no other extra field or text should be present in your response.\n
                Answer:
                Explanation:
                '''

                formatted_answer = answer.split()[1][0]

                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo-0125",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    temperature=0.1
                )    
                
                gpt_response = response.choices[0].message.content
                formatted_gpt_response = gpt_response.split()[1][0]

                explanation = gpt_response.split("Explanation:")[1].strip()
                match =0
                if formatted_gpt_response == formatted_answer:
                    correct += 1
                    match=1
                    
                    
                part3_report.loc[len(part3_report.index)]= [question, explanation, formatted_gpt_response, formatted_answer, match]
                
            part3_report.to_csv(part3_filename, index=True, header=True, sep="|")
                
            # Upload the file to S3
            response = s3_client.upload_file(part3_filename, bucket_name, part3_folder+part3_filename)
                
            # Delete the temporary downloaded file
            os.remove(part3_filename)
            
            return correct
        
        

    except Exception as e:
        print("Exception: ",e)
        return "failed"
    
def main():
    correctAnswers= compare_SetA_SetB()
    print("Number of correctly guessed answers from Set B: ",correctAnswers)
    