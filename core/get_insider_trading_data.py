#!/app/.venv/bin/python -u

import re
import time
import requests
import psycopg2
from bs4 import BeautifulSoup
from datetime import datetime
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',}

def clean_data(data):
    data = re.sub(r'\([^)]*\)|\$|,', '',str(data.strip()))    
    return data

def db_connection():
    try:
        conn = psycopg2.connect(
            dbname='postgres',
            user='postgres',
            password='******',
            host='34.95.20.90',
            port='5432'
        )
    except Exception as e:
        print("Error connecting to the database:")
        print(e)
        conn = None
    return conn

def query_db(sql):
    conn = db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()
        except Exception as e:
            print("Error executing database query:")
            print(e)
            result = None
        finally:
            conn.close()
    else:
        result = None
    return result

def insert_table(table_name, data):
    conn = db_connection()
    if conn:
        try:
            # Dynamic SQL insert statement, list of column values depends on list data length
            sql_insert = f"INSERT INTO {table_name} VALUES ({', '.join(['%s'] * len(data[0]))})"
            with conn.cursor() as cursor:
                if isinstance(data, list) and len(data) > 0:
                    cursor.executemany(sql_insert, data)
                else:
                    cursor.execute(sql_insert, data)
            conn.commit()
        except Exception as e:
            print("Error inserting data into the database:")
            print(e)
        finally:
            conn.close()


def get_latest_filings():
    try:
        print(f'\tFetching last saved data(html url) from Database')
        last_html = query_db('SELECT html_url FROM latest_filings ORDER BY accepted_datetime DESC LIMIT 1;')
        # If last html_url present in the table or empty table, result = Type list 
        if isinstance(last_html, list):
            # only 1 item, max should be returned
            if len(last_html) == 1:
                last_html = last_html[0][0]
            elif len(last_html) == 0:
                last_html = ''
        print(f'\tlast_html = {last_html}')
    except Exception as e:
        print("\t Error while fetching the latest filings:")
        print(e)
        last_html = None
    latest_filing_data = []
    if last_html is not None:
        all_data_fetched = False
        start = 0        
        print(f'\tall_data_fetched = {all_data_fetched}, start = {start}')
        print(f'\tFetching latest filings from')
        # Condition to fetch number of pages till last data (html) already saved
        #while not all_data_fetched and start < 160:
        while not all_data_fetched:
            sec_edgar_url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&&type=4&owner=only&count=40&start={start}'
            print(f'\t\tPage {int(start/40+1)}, {sec_edgar_url}')
            response = requests.get(sec_edgar_url, headers=headers)
            soup = BeautifulSoup(response.content, "html.parser")
            try:
                filings_table = soup.div.find_all('table',recursive=False)[1]
                filings_table = filings_table.find_all('tr')[1:]   
                # make pair of table rows, each table row pair belongs to one filing
                filings_table_row_pairs = list(zip(filings_table[::2], filings_table[1::2]))
                # print(f'\t\t Found {len(filings_table_row_pairs)} rows in page : {start+1}')
                for item in filings_table_row_pairs:
                    # item = filings_table_row_pairs[0]
                    description         = item[0].text.strip()
                    html                = 'https://www.sec.gov' + item[1].a['href']
                    Accepted_Date       = item[1].find_all('td')[3].text[:10]
                    Accepted_Time       = item[1].find_all('td')[3].text[10:]
                    Accepted_DateTime   = datetime.strptime(f'{Accepted_Date} {Accepted_Time}', '%Y-%m-%d %H:%M:%S')
                    Filing_Date         = item[1].find_all('td')[4].text
                    try:
                        File                = item[1].find_all('td')[5].text.split('\n')[0]
                        Film_No             = int(item[1].find_all('td')[5].text.split('\n')[1])
                    except:
                        File    = None
                        Film_No = None
                    if html != last_html:
                        print(f'\t\t\trow {filings_table_row_pairs.index(item)}:New Data,                 html = {html}')
                        latest_filing_data.append((html,description,Accepted_DateTime,Filing_Date,File,Film_No))
                    elif html == last_html:
                        print(f'\t\t\trow {filings_table_row_pairs.index(item)}:Reached last saved data,  html = {html}')                                
                        all_data_fetched = True
                        # print(f'\t\t\tall_data_fetched = {all_data_fetched}, start = {start}')
                        break
            except Exception as e:
                print(f'\t\tExcept block, Error in Fetching : {sec_edgar_url}')
                print(f'\t\t{e}')
                all_data_fetched = True
                print(f'\t\tall_data_fetched = {all_data_fetched}, start = {start}')
                print(f'\t\thtml = {html}, last_html = {last_html}')
            start += 40
            print(f'\t\tall_data_fetched = {all_data_fetched}, start = {start}')
    else:
        print('\t ELSE: Error fetching last saved html url from Database')           
    return latest_filing_data


def get_filing_details(index_html_url : str):
    insider_trading_data = []
    index_response = requests.get(index_html_url, headers=headers)
    if index_response.status_code == 200:
        try:
            index_soup = BeautifulSoup(index_response.content, "html.parser")
            accepted_datetime = index_soup.find('div', class_="formGrouping").find_all('div', class_='info')[1].text
            index_table = index_soup.find('table')    
            form4_url = 'https://www.sec.gov' + index_table.a['href']
            print(f'\tform4_url = {form4_url}')   
            form4_response = requests.get(form4_url, headers=headers)
            if form4_response.status_code == 200:
                try:
                    form4_soup = BeautifulSoup(form4_response.content, "html.parser")
                    all_tables = form4_soup.body.find_all('table', recursive=False)
                    company_data = all_tables[1]
                    non_derivative_table = all_tables[2]
                    derivative_table = all_tables[3]       
                    company_data    = company_data.tr.find_all('td', recursive=False)
                    insider_name    = company_data[0].td.text
                    company_name    = company_data[1].a.text
                    ticker          = company_data[1].find_all('span')[1].text    
                    director        = company_data[2].find_all('td')[0].text
                    owner_10        = company_data[2].find_all('td')[2].text
                    officer         = company_data[2].find_all('td')[4].text
                    other           = company_data[2].find_all('td')[6].text
                    if officer or other:
                        title       = company_data[2].find_all('td')[8].text.strip()
                        if title == "See Remarks":
                            title   = all_tables[4].find('tr', string='Remarks:').next_sibling.next_sibling.text
                    elif director and owner_10:
                        title       = 'Director, 10% Owner'
                    elif director:
                        title       = 'Director'
                    elif owner_10:
                        title       = '10% Owner'                                                  
                    # Non-Derivative table
                    if non_derivative_table.tbody:
                        trade_type_mapping = {'A': 'Buy', 'D': 'Sale'}
                        security_table = non_derivative_table.tbody.find_all('tr')   
                        # row = security_table[0]
                        for row in security_table :
                            fill_date   = clean_data(row.find_all('td')[1].text)
                            if fill_date != '':
                                qty         = clean_data(row.find_all('td')[5].text.strip())
                                if qty == '':
                                    qty     = 0
                                else:
                                    qty     = float(qty)
                                trade_type  = trade_type_mapping.get(clean_data(row.find_all('td')[6].text.strip()), None)
                                price       = clean_data(row.find_all('td')[7].text.strip())  
                                if price == "":
                                    price   = 0
                                else:
                                    price   = float(price)
                                values      = round(qty * price)
                                insider_trading_data.append((fill_date,accepted_datetime,ticker,company_name,insider_name,title,trade_type,price,qty,values,form4_url))      
                    # Derivative Table
                    if derivative_table.tbody:
                        derivative_table = derivative_table.tbody.find_all('tr')
                        # row = derivative_table[0]
                        for row in derivative_table:
                            fill_date   = clean_data(row.find_all('td')[2].text.strip())
                            if fill_date != '':
                                trade_type  = 'Option Exercise'
                                qty         = clean_data(row.find_all('td')[6].text.strip())
                                if qty == '':
                                    qty = 0
                                else:
                                    qty = float(qty)
                                price       = clean_data(row.find_all('td')[12].text.strip())
                                if price != "":
                                    price   = float(price)
                                else:
                                    price   = 0                            
                                values      = round(qty * price)
                                insider_trading_data.append((fill_date,accepted_datetime,ticker,company_name,insider_name,title,trade_type,price,qty,values, form4_url))
                    print(f'\t\t{fill_date},{accepted_datetime},{ticker},{company_name},{insider_name},{title},{trade_type},{price},{qty},{values}')            
                    return insider_trading_data
                except Exception as e:
                    print(f"Error while fetching form4_url = {form4_url}:")
                    print(e)
            else:
                print(f'Error in request {form4_url}\n{form4_response.status_code} {form4_response.text}')
        except requests.exceptions.RequestException as re:
            print(f"Request Exception while fetching {index_html_url}:")
            print(re)
    return insider_trading_data


def main():
    print(f'\n\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} : Starting Main Function')
    latest_filing_data = get_latest_filings()
    if latest_filing_data:
        print(f'{len(latest_filing_data)} new latest_filing_data found ')
        print(f'Inserting latest_filings Data in Table latest_filing, {len(latest_filing_data)} rows')
        insert_table('latest_filings', latest_filing_data)
        html_urls = [item[0] for item in latest_filing_data]
        insider_trading_data = []
        print("Fetching Form4 Data")
        for position,html_url in enumerate(html_urls,start=1):    
            print(f'\t{position}/{len(html_urls)}') 
            insider_trading_data = get_filing_details(html_url)
            if insider_trading_data:
                print("\t\tInserting Form4 data into insider_trading table")
                insert_table('insider_trading', insider_trading_data) 
        print('Done')   
    else:
        print('No new data from latest filings since last saved')
        #print("Sleeping for 300 seconds (5 mins)")
    print("Sleeping for 300 seconds (5 mins)\n")
    time.sleep(300)

# truncate table insider_trading;
# truncate table latest_filings;
# 
# select * from insider_trading;
# select * from latest_filings;

if __name__ == '__main__':
    while True:
        main()
