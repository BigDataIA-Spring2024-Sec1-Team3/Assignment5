from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from snowflake.connector.pandas_tools import pd_writer
import snowflake.connector
import configparser

def scrape_internal_reading(driver, url_extension):
    # Load summary page
    driver.get(url_extension)
    time.sleep(2)

    # Get page source for summary page
    extended_page_source = driver.page_source
    ext_parsed_content = BeautifulSoup(extended_page_source, 'html.parser')

    # Extract topic name
    topic_name = ext_parsed_content.find('h1', class_='article-title').get_text()

    # Extract year
    try:
        year = ext_parsed_content.find('span', class_="content-utility-curriculum").get_text().strip()[:4]
    except Exception as e:
        print("Exception occurred during year extraction:", e)
        year = None

    # Extract level
    try:
        level = ext_parsed_content.find('span', class_="content-utility-topic").get_text().strip().strip("Level")
    except Exception as e:
        print("Exception occurred during level extraction:", e)
        level = None

    # Extract PDF link
    pdf_link=None
    
    try:
        pdf_section = ext_parsed_content.find('section', class_="primary-asset login-required")
        if pdf_section:
            for child_tag in pdf_section.find_all('a'):
                child_tag_text = child_tag.get_text()
                if child_tag_text == "Download the full reading (PDF)":
                    pdf_link = "https://www.cfainstitute.org" + child_tag['href']
        else:
            raise Exception("No PDF section available")
    except Exception as e:
        print("Exception occurred during PDF extraction:", e)
        pdf_link = None

    introduction = None
    learning_outcome = None
    summary = None
    
    # checking headings of Introduction, learning outcomes and summary
    for heading in ext_parsed_content.find_all('h2', class_="article-section"):
        heading_text = heading.get_text()
        
        # Extract introduction
        if(heading_text=='Introduction' or heading_text=='Overview'):
            try:
                introduction_section = heading.find_parent('section')
                intro_list=[]
                if introduction_section:
                    for child_tag in introduction_section.find_all('p'):
                        cleaned_string = re.sub(r'\s+', ' ', child_tag.get_text(strip=True)) 
                        intro_list.append(cleaned_string) 
                    introduction = " ".join(intro_list)
                else:
                    introduction=None
            except Exception as e:
                introduction=None
                print("Exception occurred during introduction extraction: ",e)
        
        # Extract learning outcome
        if(heading_text=="Learning Outcomes"):
            try:
                learning_outcome_section = heading.findNext('section')
                if learning_outcome_section:
                    learning_outcome_list = []
                    for child_tag in learning_outcome_section:
                        cleaned_string = re.sub(r'\s+', ' ', child_tag.get_text(strip=True))
                        learning_outcome_list.append(cleaned_string)
                    learning_outcome = " ".join(learning_outcome_list)
                else:
                    learning_outcome=None
            except Exception as e:
                learning_outcome=None
                print("Exception occurred during learning_outcome extraction: ",e)
            
        # Extract summary
        if(heading_text=='Summary'):
            try:
                summary_section = heading.findNext('div')
                if summary_section:
                    summary_list=[]
                    for child_tag in summary_section:
                        cleaned_string = re.sub(r'\s+', ' ', child_tag.get_text(strip=True))
                        summary_list.append(cleaned_string)
                    summary = " ".join(summary_list)
                else:
                    summary=None
            except Exception as e:
                summary=None
                print("Exception occurred during summary extraction: ",e)
            
    # print("Intro: ",introduction[:4], "lo: ",learning_outcome[:4], "summary: ", summary )
    
    return {'topic_name': topic_name, 'year': year, 'level': level, 'introduction': introduction,
            'learning_outcome': learning_outcome, 'summary':summary, 'summary_page_link': url_extension, 'pdf_file_Link': pdf_link}
    

def scrape_front_page_readings(base_url, pages):
    
    # Set up the Selenium webdrivers
    front_page_driver = webdriver.Chrome()
    internal_driver = webdriver.Chrome()

    # Initialize DataFrame to store scraped data
    cfa_readings_df = pd.DataFrame(columns=['topic_name', 'year', 'level', 'introduction', 'learning_outcome', 'summary', 'summary_page_link', 'pdf_file_Link'])

    # Iterate through pages
    for i in range(pages):

        print(f"Scraping page {i}")

        # Construct URL for pagination
        url = f"{base_url}#first={i}0&sort=%40refreadingcurriculumyear%20descending"

        # Load page
        front_page_driver.get(url)

        # Wait for dynamic content to load
        time.sleep(2)

        # Get page source
        page_source = front_page_driver.page_source

        # Parse content
        parsed_content = BeautifulSoup(page_source, 'html.parser')

        # Iterate through each div containing reading details
        for div in parsed_content.find_all('div', attrs={"class": "coveo-list-layout CoveoResult"}):
            try:
                # Extract summary page URL
                url_extension = div.find('a', class_='CoveoResultLink')["href"]

                # Scrape reading details
                reading_data = scrape_internal_reading(internal_driver, url_extension)

                # Add data to DataFrame
                cfa_readings_df.loc[len(cfa_readings_df)] = reading_data

            except Exception as e:
                print("Exception occurred during scraping:", e)

    # Close the Selenium webdrivers
    front_page_driver.quit()
    internal_driver.quit()

    return cfa_readings_df


def upload_to_snowflake(cfa_readings_df):
    try:
        # Upload to Snowflake
        config = configparser.ConfigParser()
        config.read('configuration.properties')
        
        user = config['SNOWFLAKE']['user']
        password = config['SNOWFLAKE']['password']
        account = config['SNOWFLAKE']['account']
        role = config['SNOWFLAKE']['role']
        warehouse = config['SNOWFLAKE']['warehouse']
        database = config['SNOWFLAKE']['database']
        schema = config['SNOWFLAKE']['schema']
        table = config['SNOWFLAKE']['cfa_website_table_name']
        stage = config['SNOWFLAKE']['stage']
        file_format = config['SNOWFLAKE']['ff']

        conn = snowflake.connector.connect(
                    user=user,
                    password=password,
                    account=account,
                    warehouse=warehouse,
                    database=database,
                    schema=schema,
                    role=role
                    )

        cfa_readings_df.to_csv('scraped_data.csv', sep='\t', index=False)

        # Put command to upload CSV file to Snowflake stage
        conn.cursor().execute(f"PUT 'file://scraped_data.csv' @{stage}")

        # Copy data from stage to table
        load_query=f"COPY INTO {database}.{schema}.{table} FROM @{stage}/scraped_data.csv FILE_FORMAT = (FORMAT_NAME = {file_format})"
        conn.cursor().execute(load_query)
        conn.close()
    
        return "Successful"    
    except Exception as e:
        print("Exception: ", e)
        
if __name__ == "__main__": 
    # Define base URL and other constants
    base_url = "https://www.cfainstitute.org/en/membership/professional-development/refresher-readings"
    pages = 23

    # Scrape reading details
    cfa_readings_df = scrape_front_page_readings(base_url, pages)
    
    print(cfa_readings_df.head())
    
    res = upload_to_snowflake(cfa_readings_df)
    print(res)