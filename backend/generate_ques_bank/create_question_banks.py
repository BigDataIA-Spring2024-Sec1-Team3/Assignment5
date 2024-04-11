from openai import OpenAI
import os
import boto3
import json
import configparser
import snowflake.connector
import pandas as pd

def snowflake_connection():
    try:
        # Snowflake details
        config = configparser.ConfigParser()
        config.read('configuration.properties')
        
        user = config['SNOWFLAKE']['user']
        password = config['SNOWFLAKE']['password']
        account = config['SNOWFLAKE']['account']
        role = config['SNOWFLAKE']['role']
        warehouse = config['SNOWFLAKE']['warehouse']
        database = config['SNOWFLAKE']['database']
        schema = config['SNOWFLAKE']['schema']
        cfa_table = config['SNOWFLAKE']['cfa_table_name']

        conn = snowflake.connector.connect(
                    user=user,
                    password=password,
                    account=account,
                    warehouse=warehouse,
                    database=database,
                    schema=schema,
                    role=role
                    )
        
        return conn, cfa_table
    except Exception as e:
        print("Exception in snowflake_connection function: ",e)
        return 

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

def combining_text_files():
    ''' 
    function to 
        - extract sample QA text files stored in AWS S3
        - generate analysis of text files using OpenAI api
        - store the analysis into text file
        - upload the text file into S3 bucket
    '''
    try:
        s3_client, bucket_name, analysis_folder_name, txt_file_folder, question_sets_folder_name = aws_connection()
        
        paginator = s3_client.get_paginator('list_objects_v2')
        response_iterator = paginator.paginate(
            Bucket=bucket_name,
            Prefix=txt_file_folder
        )
        
        print("Response received from S3 bucket")
        
        # fetching files in pdf_folder
        for response in response_iterator:
            if 'Contents' in response:
                combined_text = ''
                for item in response['Contents']:
                    if str(item['Key']).endswith('.txt'):    

                        # Get the object containing the text file content
                        response = s3_client.get_object(Bucket=bucket_name, Key=item['Key'])

                        # Read the content of the object (text file) as a stream
                        text_stream = response['Body']

                        # Read the text from the stream
                        text = text_stream.read().decode('utf-8')
                        
                        combined_text += text                     
        
        print("Text combined from all text files")
        return combined_text

    except Exception as e:
        print("Exception in combining_text_files function", e)
        return ''
 
def analysis_of_combined_text_using_openai(combined_text):
    '''
    function to perform analysis on sample QA using openAI api
    '''
    try:
        openai_client = OpenAI(api_key=openai_connection())
        
        # removing extra spaces
        combined_text = combined_text.strip()
        
        # prompt to openai for generating analysis of sample QA
        prompt = f"Below is a Multiple Choice Questions set with 3 options and one correct answer. \nThere is an explanation for the correct answers.\nPerform a detailed analysis of the format.\n {combined_text}"
        
        print("generating response...")
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.5,
            # max_tokens=500,
        )
        
        print("response generated")

        # Extract and return the generated analysis from the response
        analysis = response.choices[0].message.content
        
        return analysis
    
    except Exception as e:
        print("Exception in analysis_of_combined_text_using_openai function", e)
        return ''
    
def uploading_analysis_file_to_aws(text):
    try:
        ''' 
        function to upload analyzed file into AWS S3
        '''
        
        s3_client, bucket_name, analysis_folder_name, txt_file_folder, question_sets_folder_name = aws_connection()
        
        # writing combined_text into txt file
        output_file_path = 'analysis_of_sample_qa.txt'
        
        with open(output_file_path, 'w', encoding="utf-8") as file:
            file.write(text)
        
        print("Text written into analysis_of_sample_qa.txt file")
        
        # Upload the file to S3
        output_file_key = analysis_folder_name + output_file_path
        response = s3_client.upload_file(output_file_path, bucket_name, output_file_key)
        
        # Delete the temporary downloaded file
        os.remove(output_file_path)
        
        print("analysis_of_sample_qa.txt uploaded into S3")

        return "Upload Successful"
        
    except Exception as e:
        print("Exception in uploading_analysis_file_to_aws function: ", e)
        return "Failed upload"

def generate_ques_ans(combined_summary_text, set_name, num_questions, max_):
    '''function to 
        - fetch analyzed file from S3
        - generate Questions and Answers using the sample format with openai API
        
        function takes generated question bank text and generates pipe separated CSV with below columns.
        - Question
        - Answer   
    '''
    try:
        s3_client, bucket_name, analysis_folder_name, txt_file_folder, question_sets_folder_name = aws_connection()
        openai_client = OpenAI(api_key=openai_connection())
        
        # Get the object containing the text file content
        key_path = analysis_folder_name+'analysis_of_sample_qa.txt'
        response = s3_client.get_object(Bucket=bucket_name, Key=key_path)
        
        print("Analyzed file received from S3 bucket")
        
        # Read the content of the object (text file)
        analyzed_text = response['Body'].read().decode('utf-8')                     
        
        qa_df = pd.DataFrame(columns=['question','answer'])
        
        print("generating question bank...")
        total_ques = num_questions
        
        while len(qa_df) < total_ques:
            
            print("Total remaining Questions: ",num_questions)
            
            prompt = f'''
            Following is the analysis and format for generating Multiple Choice Questions Set. \n{analyzed_text}\n 
            Using the above format strictly, generate a multiple choice question bank containing strictly {max_} question(s), each with 4 options.\n
            I also need one correct choice answer along with an explanation of why choice is correct and why other choices are wrong.\n
            Each question should be numbered and must have following 4 sections strictly: -- Question, -- Options, -- Correct Answer, -- Explanation.\n
            Separate each question with ===
            Refer below summary to generate the question bank\n {combined_summary_text}.'''
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0
            )
            
            print("Question bank generated")

            # Extract and return the generated analysis from the response
            question_bank_text = response.choices[0].message.content  
            question_bank_list = question_bank_text.split("===")
            
            for ques in question_bank_list:
                split_parts = ques.split("Correct Answer")
                question_options = split_parts[0].strip().replace("|"," ").replace("\n"," ")
                answer_explanation = split_parts[1].strip().replace("|"," ").replace("\n"," ")
                
                qa_df.loc[len(qa_df)] = [question_options, answer_explanation]
                
            num_questions-= max_  
        
        print("Dataframe generated.")
        
        output_csv_file = f'qa_df_{set_name}.csv'
        qa_df.to_csv(output_csv_file, header=True, index=True, sep = '|')

        print("Dataframe loaded into CSV.")
       
        return output_csv_file
    
    except Exception as e:
        print("Exception in generate_ques_ans function", e)
        return ''

def fetch_summary_from_snowflake(topics):
    '''
    function to fetch summaries of given topics and combining it
    '''
    try:
        conn, cfa_table_name = snowflake_connection()
        
        combined_summary_text=""
        fetch_summary_query = f"SELECT SUMMARY FROM {cfa_table_name} WHERE TOPIC_NAME IN ({topics});"
        
        # Create a cursor
        cur = conn.cursor()
        
        # Execute query to fetch rows from the Snowflake table
        cur.execute(fetch_summary_query)
        
        # Fetch all rows and combine summaries
        summaries = cur.fetchall()
        # summaries = cur.fetchone()
        for summary in summaries:
            combined_summary_text += summary[0]
            # combined_summary_text += summary
        
        return combined_summary_text

    except Exception as e:
        print("Exception in fetch_summary_from_snowflake function", e)
        return ''
    
def upload_data_to_aws(output_csv_file):
    '''
    function takes csv file of Question bank and uploads to AWS S3
    '''
    try:
        s3_client, bucket_name, analysis_folder_name, txt_file_folder, question_sets_folder_name = aws_connection()
        
        # Loading into AWS
        output_file_key = question_sets_folder_name + output_csv_file
        response = s3_client.upload_file(output_csv_file, bucket_name, output_file_key)
        
        print("Data loaded into AWS S3 bucket")
        
        return "Successful"
        
    except Exception as e:
        print("Exception in upload_data_to_snowflake function: ",e)
        return "Failed"

if __name__ == "__main__":
    # function to combine the sample text files with QA 
    combined_text = combining_text_files()
    
    # generating analysis on the sample text files
    analyzed_text = analysis_of_combined_text_using_openai(combined_text) 
    
    # uploading analyzed file into S3   
    res = uploading_analysis_file_to_aws(analyzed_text)
    
    # Fetching summary for topics assigned
    topics = "'Overview of Equity Securities','Market Organization and Structure','Security Market Indexes'"
    combined_summary_text = fetch_summary_from_snowflake(topics)
    
    # generating set a
    output_csv_file_a = generate_ques_ans(combined_summary_text, 'set_b_qa', num_questions=50, max_ = 5)
    
    response = upload_data_to_aws(output_csv_file_a)
    
    # generating set a
    output_csv_file_b = generate_ques_ans(combined_summary_text, 'set_b_qa', num_questions=50, max_ = 5)
    
    response = upload_data_to_aws(output_csv_file_b)