from asyncore import read
import os
from langchain.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import configparser
from operator import ge, le
'''
import snowflake.connector
'''
import pandas as pd


config = configparser.RawConfigParser()
config.read('./configuration.properties')

# Function to fetch data from Snowflake


def fetch_data_from_snowflake():
    '''

    user = config['SNOWFLAKE']['Username'],
    password = config['SNOWFLAKE']['Password'],
    account = config['SNOWFLAKE']['Account'],
    warehouse = config['SNOWFLAKE']['Warehouse'],
    database = config['SNOWFLAKE']['Database'],
    schema = config['SNOWFLAKE']['Schema']

    # Create a connection string
    connection_string = f'snowflake://{user}:{password}@{account}/' \
        f'?warehouse={warehouse}&database={database}&schema={schema}'

    # Create an engine for Snowflake Connection
    engine = create_engine(connection_string)
    print("Engine created for snowflake sqlalchemy")

    with engine.connect() as conn:

        sql = "SELECT * FROM CFA_WEBSITE_DATA"
        result = conn.execute(sql)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    '''
    df = pd.read_csv('./data/input/scraped_data.csv', sep='\t')

    return df


def filter_dataframe(df, topic_names):
    '''
    # Filter the dataframe for the specified topic names
    topic_names = [
    "Overview of Equity Securities",
    "Market Organization and Structure",
    "Security Market Indexes"
    ]
    '''

    filtered_df = df[df['topic_name'].isin(topic_names)]

    # Remove the specified line from learning outcomes and expand into separate rows
    expanded_list_cleaned = []
    for index, row in filtered_df.iterrows():
        learning_outcomes = row['learning_outcome'].replace(
            "The member should be able to:", "").split(";")
        for outcome in learning_outcomes:
            cleaned_outcome = outcome.strip()
            if cleaned_outcome:  # Ensure the outcome is not empty
                expanded_list_cleaned.append({
                    "topic_name": row['topic_name'],
                    "learning_outcome": cleaned_outcome,
                    "summary": row['summary']
                })

    # Recreate the expanded dataframe without the unnecessary line
    new_df = pd.DataFrame(expanded_list_cleaned)
    return new_df


def query_openai_for_technical_document(learning_outcome, summary, api_key):

    # completion llm
    llm = ChatOpenAI(
        openai_api_key=api_key,
        model_name='gpt-3.5-turbo',
        temperature=0.0,
        max_tokens=2048,
        frequency_penalty=0.1,
        presence_penalty=0.1,
    )

    messages = [
        SystemMessage(content="You are provided a SUMMARY below. Your goal is to provide a technical note that relates to the LEARNING OUTCOME. Include tables, figures and equations, ONLY if present in the CONTEXT. Ensure that you stickly stay within the CONTEXT and use no outside information. Answer in less than 300 words. No heading is needed. \LEARNING OUTCOMES:\n" + learning_outcome + "\n\nSUMMARY:\n" + summary + "\n\n"),
    ]

    response = llm.invoke(messages)
    response = response.content

    return response

# Function to query OpenAI and update the dataframe


def generate_technical_documents(df):

    api_key = config['OPENAI']['OPENAI_API_KEY']
    print(api_key)

    # Append a blank "Technical Document" column
    df["technical_document"] = ""

    for index, row in df.iterrows():

        # Query OpenAI for each row and update the 'Technical Document' column
        df.at[index, 'technical_document'] = query_openai_for_technical_document(
            learning_outcome=row['learning_outcome'],
            summary=row['summary'],
            api_key=api_key
        )
    '''
    try:
        # Write the data to Snowflake
        conn = snowflake.connector.connect(
            user=config['SNOWFLAKE']['Username'],
            password=config['SNOWFLAKE']['Password'],
            account=config['SNOWFLAKE']['Account'],
            warehouse=config['SNOWFLAKE']['Warehouse'],
            database=config['SNOWFLAKE']['Database'],
            schema=config['SNOWFLAKE']['Schema']
        )
        filtered_table_name = config['SNOWFLAKE']['Filtered_Table_Name']

        cur = conn.cursor()

        # Create the table if it does not exist
        create_table_sql = f"CREATE OR REPLACE TABLE {filtered_table_name} (topic_name VARCHAR, learning_outcome VARCHAR, summary VARCHAR, technical_document VARCHAR)"
        cur.execute(create_table_sql)

        insert_data_sql = f"INSERT INTO {filtered_table_name} (topic_name, learning_outcome, summary, technical_document) VALUES (%s, %s, %s, %s)"

        # Iterate through the DataFrame and insert each row
        for index, row in df.iterrows():
            # Parameters to insert for each row
            data_tuple = (row['topic_name'],
                          row['learning_outcome'], row['summary'], row['technical_document'])
            # Execute the insert command with the parameters
            cur.execute(insert_data_sql, data_tuple)

    except Exception as e:
        print(e)

    '''

    df = df.drop(columns=['summary'])
    df.to_csv('./data/output/technical_documents1.csv', index=False)

    return df


def generate_markdown_file(df):
    # Grouping the data by topic_name and creating the markdown content
    markdown_content = ""
    for topic_name, group in df.groupby("topic_name"):
        markdown_content += f"# {topic_name}\n\n"
        for _, row in group.iterrows():
            markdown_content += f"## Learning Outcome:\n {row['learning_outcome']}\n"
            markdown_content += f"## Technical Document:\n {row['technical_document']}\n\n"

    # Saving the markdown content to a .txt file
    markdown_file_path = './data/output/technical_documents_markdown1.md'
    with open(markdown_file_path, 'w') as file:
        file.write(markdown_content)

    return markdown_file_path
