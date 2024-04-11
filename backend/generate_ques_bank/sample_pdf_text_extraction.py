import configparser
import boto3
from PyPDF2 import PdfReader
import os

def aws_connection():
    try:
        # AWS details fetch
        config = configparser.ConfigParser()
        config.read('configuration.properties')
        
        # s3 connection details
        aws_access_key = config['AWS']['access_key']
        aws_secret_key = config['AWS']['secret_key']
        bucket_name = config['AWS']['bucket']
        pdf_files_folder = config['AWS']['pdf_files_folder_name']
        txt_file_folder = config['AWS']['txt_file_folder_name']
        
        s3_boto3_client = boto3.client('s3', aws_access_key_id= aws_access_key, aws_secret_access_key=aws_secret_key)
        
        return s3_boto3_client, bucket_name, pdf_files_folder, txt_file_folder
    
    except Exception as e:
        print("Exception in aws_connection function: ",e)
        return 

def pdf_txt_extraction():
    ''' 
    function to 
        - extract text from sample QA pdf files stored in AWS S3
        - store the text files back to S3
    '''
    try:
        s3_client, bucket_name, pdf_files_folder, txt_file_folder = aws_connection()

        paginator = s3_client.get_paginator('list_objects_v2')
        response_iterator = paginator.paginate(
            Bucket=bucket_name,
            Prefix=pdf_files_folder
        )
        
        # The pdf will be split and only section with Question and Answers will be taken for analysis
        split_at = "Answers to Sample Level"
        
        # fetching files in pdf_folder
        for response in response_iterator:
            if 'Contents' in response:
                for item in response['Contents']:
                    if str(item['Key']).endswith('.pdf'):    
                        
                        # Download the PDF file from S3
                        input_file_path = str(item['Key']).split('/')[-1]
                        s3_client.download_file(bucket_name, item['Key'], input_file_path)
                        
                        # Extract text from the downloaded PDF file
                        text = ''
                        with open(input_file_path, 'rb') as file:
                            reader = PdfReader(file)
                            for page_num in range(len(reader.pages)):
                                page = reader.pages[page_num]
                                text += page.extract_text()
                        
                        text = text.split(split_at)[1]
                        
                        # Delete the temporary downloaded file (pdf)
                        os.remove(input_file_path)

                        # writing file to s3 bucket
                        file_name_wo_extension = input_file_path.strip('.pdf')
                        output_file_path = file_name_wo_extension+'.txt'
                        with open(output_file_path, 'w', encoding="utf-8") as file:
                            file.write(text)
                        
                        # Upload the file to S3
                        output_file_key = txt_file_folder + output_file_path
                        response = s3_client.upload_file(output_file_path, bucket_name, output_file_key)
                        
                        # Delete the temporary downloaded file (txt)
                        os.remove(output_file_path)

            return response

    except Exception as e:
        print("Exception in pdf_txt_extraction function: ",e)
        return

if __name__ == "__main__": 
    pdf_txt_extraction()
