# U.S. SECURITIES AND EXCHANGE COMMISSION (SEC) 
### Latest EDGAR Company filings data scraping


This is Python & Django based repository.
This program fetches latest insider company filing details from US SEC website.

get_insider_trading_data.py script fetches all latest insider company filings (Form Type =4).
Python script fetches each filings Form 4  and scrapes data using BeautifulSoup and store the result into a Postgres DB runnung on Google Cloud.

A Django application displays data from the Postgres Database.
