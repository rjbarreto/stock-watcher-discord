"""
Ricardo Barreto



This application consists in creating a bot user on discord to display stock market data. 

It uses discord.py, a Python wrapper for the Discord API to deal with the Discord integration.

To fetch market data, yfinance (an open-source tool that uses Yahoo's publicly available APIs) is used.

Every day that the market opens, there is a scheduled message at a specific time that indicates the top and bottom performing stocks from the previous working day. 

The application informs the users when the market doesn't open (weekend and/or holidays).

The list of S&P500 tickers and the days that the market is closed are retrieved from certain webpages through the pandas module. 

Numpy is used on the scheduled message's stock selection. 

"""
import discord
import config
from datetime import datetime, timedelta
import asyncio
import yfinance as yf
import pandas as pd
import numpy as np
from collections import defaultdict


# discord integration
intents = discord.Intents.default()
intents.message_content = True # access to messages content

client = discord.Client(intents=intents)


# time of the scheduled messages
hour = 14
minute = 00

# number of top and bottom results displayed on the scheduled messages
number_results = 5

# conversion from month name to month number
months = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6, 'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12}


def send_market_scheduled_messages():

    """
    Returns the N best and worst performing stocks from the previous time time the stock market was open.

    The number of results displayed is chosen by the the value of the global variable "number_results".
    On error return "An error occurred.".
    If today is a weekend returns "It's the weekend, the market is closed.".
    If today is a holiday the return value is "Today is a holiday, the market is closed.".
    """

    try:
        # get start and end dates of the market data
        today = datetime.today()




        # get days the market is closed (holidays)
        url_holidays_list = 'https://www.nyse.com/markets/hours-calendars'

        holidays_list = pd.read_html(url_holidays_list)[0][str(today.year)]


        holidays = defaultdict(list)
        for dates in holidays_list:

            holidays[months[(dates.split(',')[1]).split()[0]]].append(int((dates.split(',')[1]).split()[1].strip('*'))) # ex: {"January": [2, 16], ...}




        # check if stock market is open today
        if today.day in holidays[today.month]:  # today is a holiday - stock market is closed

            return "Today is a holiday, the market is closed."


        if today.weekday() in (5, 6): # its the weekend - stock market is closed. 5 = saturday, 6 = sunday

            return "It's the weekend, the market is closed.




        # check when was the last time the market was open
        while 1:
            aux = (today - timedelta(days=1))

            if aux.weekday() in (5, 6): # stock market was closed yesterday (weekend) - want data from the previous day
                today = aux
                continue

            if aux.day in  holidays[aux.month]: # stock market was closed yesterday (holiday) - want data from previous day
                today = aux
                continue

            break
        
        end_date = today.strftime('%Y-%m-%d') # day after the market was last open
        start_date = (today - timedelta(days=1)).strftime('%Y-%m-%d') # day the market was last open




        # get list of S&P500 tickers 
        url_sp500_list = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'

        sp500_list = pd.read_html(url_sp500_list)[0]['Symbol'].tolist()
        #sp500_list = ['AAPL', 'MSFT', 'MMM', 'AES', 'TSLA', 'AFL'] # small test

        number_tickers = len(sp500_list)
        

        # replace '.' to '-' on tickers
        for i, ticker in enumerate(sp500_list):
            if '.' in ticker:
                sp500_list[i] = ticker.replace('.', '-')



        
        """ 
        Download S&P500 data
        
        Array of size [1, 2*len(sp500_list)]. 
        First len(sp500_list) values correspond to the open price and the remaining to the adjusted close price.
        The values on the array are given in alphabetic order (ticker names) and not in the same order as sp500_list hence sorting the list is needed. 
        """
        stock_data = yf.download(sp500_list, start = start_date, end = end_date)[['Open', 'Adj Close']].to_numpy()
       
        sp500_list.sort()


        print(start_date)
        print(end_date)

        # calculate stocks change in percentage
        percentages = np.empty((2, len(sp500_list)))

        for i, ticker in enumerate(sp500_list):
            
            close_price = stock_data[0][i + number_tickers] # value at close time
            open_price = stock_data[0][i] # value at open time
            percentages[0][i] = (close_price - open_price) * 100 / open_price # change in percentage
            percentages[1][i] = close_price # current value




        # get the N best performing stocks
        best_idx = np.argpartition(percentages[0], -number_results)[-number_results:]
        best_elements = percentages[0][best_idx]
        best_elements_price = percentages[1][best_idx]
        best_tickers = []
        for i in best_idx:
            best_tickers.append(sp500_list[i])
        best_idx = np.argsort(best_elements)[::-1]


        # get the N worst performing stocks
        worst_idx =  np.argpartition(percentages[0], number_results)[:number_results]
        worst_elements = percentages[0][worst_idx]
        worst_elements_price = percentages[1][worst_idx]
        worst_tickers = []
        for i in worst_idx:
            worst_tickers.append(sp500_list[i])
        worst_idx = np.argsort(worst_elements)




        # get results
        result = str(start_date) + "'s " + str(number_results) + " best performing stocks:\n"

        for i in best_idx:
            result = result + str(best_tickers[i]) + ' $' + str(round(best_elements_price[i], 2)) + "  " + str(round(best_elements[i], 2)) + '%\n'
        

        result = result + "\n" + str(start_date) + "'s " + str(number_results) + " worst performing stocks:\n"
        for i in worst_idx:
            result = result + str(worst_tickers[i]) + ' $' + str(round(worst_elements_price[i], 2)) + "  " + str(round(worst_elements[i], 2)) + '%\n'

        #print(result)
        return result

    except:
        return f"An error occurred. Market data not available for {start_date}." 








async def schedule_daily_message():

    """ 
    Sends scheduled messages to a specific discord channel. 

    Message content is given by function send_market_scheduled_messages().
    Message schedule is given by global variables "hour" and "minute".    
    """

    while True:
        now = datetime.now()

        if now.hour < hour or (now.hour == hour and now.minute < minute): # the scheduled time for the message is later in the day
            then = datetime.now()
        else: # scheduled message will be set for tomorrow
            then = now + timedelta(days=1)
        
        then = then.replace(hour=hour, minute=minute)

        # set timer and wait
        wait_time = (then-now).total_seconds()
        await asyncio.sleep(wait_time)

        # send message
        channel = client.get_channel(config.channel_id)

        await channel.send(send_market_scheduled_messages())


@client.event
async def on_ready():

    """ Message log to indicate the Discord bot is ready"""
    print(f"{client.user.name}: We are live!!")
    await schedule_daily_message()


@client.event
async def on_message(message):
    
    # ignore own messages
    if message.author == client.user:
        return

    # testing purposes
    if message.content.startswith("$hello"):
        await message.channel.send("hello");

client.run(config.token)
