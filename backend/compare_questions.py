from openai import OpenAI
import configparser
from pinecone import Pinecone
import csv

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
        
        with open(set_b_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='|')
            
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
                You are provided with a multiple choice question with 4 options out of which one is right. You are also also provided with 3 similar questions with their respective correct answers, which you need to use as reference to answer the question provided. Give me the correct answer choice with explanation justifying why you chose that answer. I need your response strictly in the following format and no other extra field or text should be present in your response.\n
                Answer:
                Explanation:
                Reference Questions with Answers:
                {context}
                Your question to answer:
                {question}'''

                formatted_answer = answer.split()[1][0]

                response = openai_client.chat.completions.create(
                    model="gpt-4",
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
                if formatted_gpt_response == formatted_answer:
                    correct += 1
                
            return correct
        
        

    except Exception as e:
        print("Exception: ",e)
        return "failed"
    
def main():
    correctAnswers= compare_SetA_SetB()
    print("Number of correctly guessed answers from Set B: ",correctAnswers)
    
main()