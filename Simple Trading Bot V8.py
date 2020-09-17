# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'

# %%
#Use lower of 0.25 or min/max dif to minimize stop loss


# %%
import math
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import yfinance as yf
import datetime as dt
from pandas.tseries.offsets import BDay
import traceback

# %%
def main (currentDay, stockDataCurrentDay, stockDataPreviousDay, startingBalance, dailyMaxLoss):

    #stockDataLiveSimModified, baseTradeSummary, farFromMovAvgTradeSummary, allTradeSummary, currentBalance

    '''(date, DataFrame, DataFrame, int, int) --> (dataframe, float)

    Argument Names:
        currentDay: the date over which the bot is simulating
        stockDataCurrentDay: current day stock's data from Yahoo Finance (should 1 minute interval data)
        stockDataPreviousDay: previous day stock's data from Yahoo Finance (should 1 minute interval data)
        startingBalance: the balance at the start of the day
        dailyMaxLoss: the maximum amount of money the bot is allowed to lose today

    Returns:
        stockDataLiveSimModified: current day stock's data as seen from Yahoo Finance along with derived numbers (SMA, EMA, RSI)
        baseTradeSummary: summary of base trade algorithms results
        farFromMovAvgTradeSummary: summary of far from moving average trade results
        allTradeSummary: summary of all trade results
        currentBalance: current balance at the end of the day

    Performs trades based on base trade and far from moving trade algorithm and outputs DataFrame with summary of trades results
    '''


    #initially currentBalance is set to starting balance
    currentBalance = startingBalance
    brokerFee = 1 #assuming that my # of shares bought will be small so fee will be $1
    # currentTradeStatus = "Nothing"
    whichPriceToCheck = "Adj Close"
    allTradeSummary = pd.DataFrame ()

    #Variables for Base Trade
    timeDurForCheck = 1 #we are using 1 minute interval data for checking
    baseTradeCheckDurationInMin = 30 #we want to check for base trade signal every 30 minutes
    #price in the interval to check for base trade can’t vary more than 0.5% of the price (for price, we are deciding to check the Adj Close price of the first data point)
    baseTradePriceVarMaxPrcntg = 0.5
    baseTradeProfitTargetPerShare = 0.25
    baseTradeLossTargetPerShare = 0.25
    baseTradeSummary = pd.DataFrame ()

    #variables for far from moving average trade
    farFromMovAvgCriticalPriceDif = 1.50
    farFromMovAvgProfitTargetPerShare = 0.50
    farFromMovAvgTradeSummary = pd.DataFrame ()

    #dataframes for containing the stock data extracted from server
    stockDataLiveSim = pd.DataFrame ()
    stockData1Row = pd.DataFrame ()
    stockDataLiveSimModified = pd.DataFrame ()

    #RSI calculation for previous day
    rsiPeriod = 14
    colTitleRsi = "RSI{0}".format (rsiPeriod)
    stockDataLiveSimModified [colTitleRsi] = float ("nan") #initiailzing the RSI column
    stockDataRsiPreviousDay = rsiPreviousDay (stockDataPreviousDay,14,"Adj Close") #dataframe containing previous day RSI; only the last row's "Avg Loss" and "Avg Gain" values will be used
    print (stockDataRsiPreviousDay.tail())
    
    #feed the data to new frame 1 row at a time
    for i in range (0,stockDataCurrentDay.shape[0],1):
        #contains all the data up to latest time
        stockDataLiveSim = stockDataCurrentDay.head (i+1)
        #temporary dataframe holding only last row of dataframe
        stockData1Row= stockDataLiveSim.tail (1)
        #modifying 1 row dataframe
        # stockData1Row.reset_index (inplace = True) #first index always = 0
        stockData1Row ["DateOnly"] = pd.Timestamp.date (stockData1Row.loc [i,"Datetime"])
        stockData1Row ["TimeOnly"] = pd.Timestamp.time (stockData1Row.loc [i,"Datetime"])
        # stockData1Row.index = [i]

        #another dataframe containing all the data upto latest minute
        if i == 0:
            stockDataLiveSimModified = stockData1Row
        else:
            stockDataLiveSimModified = stockDataLiveSimModified.append (stockData1Row)

        #Get 9, 15, 65, 200 SMA and EMA
        for smaEmaPeriod in [9,15,65,200]:
            #print (stockDataLiveSimModified.head ())
            currentSmaColTitle, currentSmaVal, currentEmaColTitle, currentEmaVal = smaEma (stockDataPreviousDay,stockDataLiveSimModified,smaEmaPeriod, "Adj Close")
            stockDataLiveSimModified.loc [stockDataLiveSimModified.index[-1], currentSmaColTitle] = currentSmaVal
            stockDataLiveSimModified.loc [stockDataLiveSimModified.index[-1], currentEmaColTitle] = currentEmaVal
  
        #get RSI value for latest minute
        if i == 0:
            previousAvgGain = float (stockDataRsiPreviousDay.tail (1) ["AvgGain"])
            previousAvgLoss = float (stockDataRsiPreviousDay.tail (1) ["AvgLoss"])
            priceChange = float (stockDataLiveSimModified.tail (1) ["Adj Close"]) - float (stockDataRsiPreviousDay.tail (1) ["Adj Close"])
            currentAvgGain, currentAvgLoss, currentRsi = rsi (priceChange, "Adj Close", rsiPeriod, previousAvgGain, previousAvgLoss)
        else:
            previousAvgGain = currentAvgGain
            previousAvgLoss = currentAvgLoss
            priceChange = float (stockDataLiveSimModified.loc [stockDataLiveSimModified.index[-1],"Adj Close"] - stockDataLiveSimModified.loc [stockDataLiveSimModified.index[-2],"Adj Close"])
            currentAvgGain, currentAvgLoss, currentRsi = rsi (priceChange, "Adj Close", rsiPeriod, previousAvgGain, previousAvgLoss)
        #set values of RSI in main dataframe
        stockDataLiveSimModified.loc [i, colTitleRsi] = currentRsi

        #get column order so we can set the main frame columns in original order (yahoo finance data, sma/ema, rsi)
        if i ==0:
            originalColOrder = stockDataLiveSimModified.columns #will be used to reset column order when appending new minute data fucks it up

        #run base trade test
            #we need 30 minute of data (base check duration) to check for base + additional minute of data to see if base has been broken or not
        if stockDataLiveSimModified.shape [0] >= (baseTradeCheckDurationInMin + timeDurForCheck):
            #base trade summary
            dfTradeSummaryTemp = baseTradeSignal (stockDataLiveSimModified.tail (baseTradeCheckDurationInMin + timeDurForCheck), 
                                     whichPriceToCheck,baseTradePriceVarMaxPrcntg,baseTradeProfitTargetPerShare,baseTradeLossTargetPerShare)
            if baseTradeSummary.shape [0] == 0:
                baseTradeSummary = dfTradeSummaryTemp
            else:
                baseTradeSummary = baseTradeSummary.append (dfTradeSummaryTemp)
            print (baseTradeSummary)

        #Far from moving average trade; for simlicity's sake, we will start running it when we have two data points for the present day
            #Theoretically we could run the test with the first data point of today but that would meaning storing previous day data including SMA, EMA, RSI
        if stockDataLiveSimModified.shape [0] >=2:
            lastPrice = float (stockDataLiveSimModified.loc[i-1,whichPriceToCheck])
            currentPrice = float (stockDataLiveSimModified.loc[i,whichPriceToCheck])
            ##listOfLastEma
            #first gets the list of columns with ema in title
            colTitleWithEma = [emaColumn for emaColumn in stockDataLiveSimModified.columns if emaColumn.__contains__ ("EMA")]
            #get the list of ema in a list
            listOfLastEma = stockDataLiveSimModified.loc [i,colTitleWithEma].tolist ()
            currentRsi = float (stockDataLiveSimModified.loc [i, colTitleRsi])
            dfTradeSummaryTemp = farFromMovingAverageTradeSignal (currentDay, i, lastPrice, currentPrice, listOfLastEma, currentRsi, farFromMovAvgCriticalPriceDif, farFromMovAvgProfitTargetPerShare)
            if farFromMovAvgTradeSummary.shape [0] == 0:
                farFromMovAvgTradeSummary = dfTradeSummaryTemp
            else:
                farFromMovAvgTradeSummary = farFromMovAvgTradeSummary.append (dfTradeSummaryTemp)   
            print (farFromMovAvgTradeSummary)
        
        #See if we sold shares
            #First Check allTradeSummary is not empty; prevent error
                #If check above is fine then check if we have an active trade
                #If we have an active trade then see if we should exit that trade by calling checkIfExitTrade
                #If checkIfExitTrade function says we should exit that trade (returns a row of data) then 
                    #update allTradeSummary with the row of data returned by checkIfExitTrade function and
                    #calculate current balance
        if (allTradeSummary.shape [0] >=1):
            isTradeComplete = allTradeSummary.loc [allTradeSummary.index [-1],'IsTradeComplete']
            if isTradeComplete == "No":
                dfTemp = checkIfExitTrade (allTradeSummary.tail(1),stockDataLiveSimModified.tail(1),"Adj Close")
                if dfTemp is not None: #trade was exited
                    #Update allTradeSummary by dropping the last row of data and appending the row returned by checkIfExitTrade function
                    allTradeSummary.drop (index = allTradeSummary.index [-1], inplace = True)
                    allTradeSummary = allTradeSummary.append (dfTemp)
                    currentBalance = currentBalance + float (allTradeSummary.loc [allTradeSummary.index [-1],"Profit"]) #Calculate current balance since trade was exited

        #Returns 1 row for dfTradesummary,  baseTradeExecutedOn and farFromMovAvgTradeExecutedOn; the last two tells me if I executed on 
            #dfTradeSummary
                #If no trade is placed then none is returned for 1 row for dfTradesummary
                #Columns for one row of dataframe: TradeType (BaseTrade, FarFromMovingAverageTrade), 
                                                #TradeId (StartTimeIndex for Base Trade or i for far from moving average trade), BuyPrice, LimitSellPrice, StopLossPrice
            #baseTradeExecutedOn, farFromMovAvgTradeExecutedOn returns Nothing (which is default value in the corresponding dataframe) or Yes or No
        if (baseTradeSummary.shape [0] >= 1) or (farFromMovAvgTradeSummary.shape [0] >=1 ):
            dfTemp,baseTradeExecutedOn,farFromMovAvgTradeExecutedOn = placeTrade(currentDay, baseTradeSummary, farFromMovAvgTradeSummary, allTradeSummary, stockDataLiveSimModified, baseTradeCheckDurationInMin, 
                                timeDurForCheck, startingBalance, currentBalance,dailyMaxLoss, brokerFee)
            if dfTemp is not None:
                if allTradeSummary.shape[0] == 0:
                    allTradeSummary = dfTemp
                else:
                    allTradeSummary = allTradeSummary.append (dfTemp)
            #Update base trade summary; in some cases the returned row would be same as before
            # print (baseTradeSummary.shape[0])
            # print (baseTradeSummary.shape[0]>=1)
            # print (farFromMovAvgTradeSummary.shape[0])
            # print (farFromMovAvgTradeSummary.shape[0]>=1)
            if baseTradeSummary.shape[0] >= 1:
                baseTradeSummary.loc [baseTradeSummary.index[-1], "ExecutedOnSignal"] = baseTradeExecutedOn 
            if farFromMovAvgTradeSummary.shape[0] >= 1:
                farFromMovAvgTradeSummary.loc [farFromMovAvgTradeSummary.index [-1],"ExecutedOnSignal"]= farFromMovAvgTradeExecutedOn

    #set original ordering of columns to original
    stockDataLiveSimModified = stockDataLiveSimModified.loc [:,originalColOrder]
    print (stockDataLiveSimModified.tail (5))
    print (baseTradeSummary.tail (5))
    print (farFromMovAvgTradeSummary.tail (5))
    print (currentBalance)
    return stockDataLiveSimModified, baseTradeSummary, farFromMovAvgTradeSummary, allTradeSummary, currentBalance
# %%
def limitStopLossSell (tradeStatus, currentPrice, buyPrice, stopLossPrice, limitSellPrice, numShares):
    '''(string, float, float, float, float) ---> (string, float)

        Argument Names:
            tradeStatus: whether the current trade is short or long
            currentPrice: current price of the stock
            buyPrice: price of stock when the current trading position was opened
            stopLossPrice: stop loss price of current trade
            limitSellPrice: limit sell price of current trade
            numShares: number of shares of the current trade
        
        Return
            updatedTradeStatus: whether the trade closed or not. = tradeStatus and set to Nothing if trade closed
            profit: profit from the current trade. nan is returned if trade is not executed

        Given current stock price, buying price, stop lossp rice and limit sell price, determine if the trade is to be closed
        If the trade is closed then calculate profit/loss
    '''

    tradeProfit = float ("nan")
    updatedTradeStatus = tradeStatus

    if tradeStatus == "Short":
        if currentPrice < limitSellPrice:
            tradeProfit = numShares*(buyPrice - limitSellPrice) 
            updatedTradeStatus = "Nothing"
        #Stop Loss triggerred; sold for loss
        elif currentPrice > stopLossPrice:
           tradeProfit = numShares*(buyPrice-stopLossPrice)
           updatedTradeStatus = "Nothing"
    elif tradeStatus == "Long":
        #Limit Sell triggered; sold for profit
        if currentPrice > limitSellPrice:
            tradeProfit = numShares*(limitSellPrice-buyPrice) 
            updatedTradeStatus = "Nothing"
        #Stop Loss triggerred; sold for loss
        elif currentPrice < stopLossPrice:
            tradeProfit = numShares*(stopLossPrice-buyPrice) 
            updatedTradeStatus = "Nothing"

    return updatedTradeStatus, tradeProfit
# %%
def marketSell (tradeType, currentPrice, buyPrice, numShares):
    ''' (string, float, float) ---> (string, tradeProfit)

        Give type of trade, buy price, current price, number of shares, return updatedTradeStatus ("Nothing") and Profit (or loss)

        We are assuming that this method is only called when a trade is active and the trade will be exited no matter what
    '''
    tradeProfit = float ("nan")
    updatedTradeStatus = "Nothing"
    if tradeType == "Short":
        tradeProfit = numShares * (buyPrice - currentPrice)
    elif tradeType == "Long":
        tradeProfit = numShares * (currentPrice - buyPrice)

    return updatedTradeStatus, tradeProfit
# %%
def convSeriesTimeToTime (timeSeriesOneRow):
    ''' (one row of series with datetype object) --> (time object)

    Given one row of series containing a time object in the format: H:M:S, time object is returned

    Input Series Example:
    62  10:32:00

    Output Example:
    10:32:00

    >>>ConvSeriesTimeToTime (series_oneRow)
    10:32:00

    >>>ConvSeriesTimeToTime (series_oneRow)
    10:45:09
    '''
    testString = str (timeSeriesOneRow)
    testTime = dt.datetime.strptime (testString, "%H:%M:%S").time()
    return testTime
# %%
def convTimeStampToDay (timeStamp, format): 
    ''' (timestamp, string) ---> (date)
        Given timestamp and format string, return date object
    '''
    timeStampString = str (timeStamp)
    return dt.datetime.strptime (timeStampString,format).date()

# %%
def preProcessStockData (stockDataYahooFinace):
    '''
        Get's yahoo data in its raw form with 1 minute interval
        Returns a dataframe with index reset so "Datetime" is first column and add 'DateOnly' column as well
    '''
    dfTemp = stockDataYahooFinace
    dfTemp.reset_index (inplace = True) #reset index so now have Datetime column
    dfTemp ["Datetime"] = pd.to_datetime (dfTemp ["Datetime"]) #making sure Datetime column contains datetime object
    # dfTemp ["DateOnly"] = dfTemp["Datetime"].dt.date
    #print (dfTemp.head ())
    return dfTemp
# %%
def baseTradeSignal (dfStockPriceData, whichPriceToCheck,baseTradePriceVarMaxPrcntg,baseTradeProfitTargetPerShare,baseTradeLossTargetPerShare):
    ''' (DataFrame, string, float, float, float) ---> (DataFrame)
    Argument Names:
        dfStockPriceData: Stock's data from Yahoo Finance with derived numbers as well (RSI, SMA, EMA)
        whichPriceToCheck: Which price to check in the stock price DataFrame
        baseTradePriceVarMaxPrcntg: Maximum fluctuation in stock price over the 30 minute period for it to be in base
        baseTradeProfitTargetPerShare: profit target per share
        baseTradeLossTargetPerShare: loss target per share

    Given 31 minutes of stock's data as given by Yahoo Finance package along with derived numbers (RSI, SMA, EMA) in a DataFrame, return a DataFrame
    with analysis from Base Trade Algorithm: the stock is in a base or not and if a trade should be made
    '''
    
    
    
    #each run, I get 31 minute of data and I check the first 30 minute to see if the stock is in a base
    #mention what the dataframe looks like
    #error handling for wrong datatype (latear)
    #if the stock is in a base then I do the rest of the things (stopLossPrice, limitSellPrice, buyTime, etc.)
	#otherwise I just return nothing

    print (dfStockPriceData.columns)
    # print (dfStockPriceData.loc[:,["Datetime","TimeOnly"]])

    firstIndex = dfStockPriceData.index [0]
    #end index is the second last row because we are getting data for base duration (currently 30 minutes) + 1 minute (1 minute is the time frame we are using for trading)
    secondLastRowIndex = dfStockPriceData.index[-2]

    #dfTemp only contains the first 30 rows of data
    #all steps below to calculate max price variation to check if in base
    dfTemp = dfStockPriceData.loc [:secondLastRowIndex, ["TimeOnly", whichPriceToCheck]]
    dfTemp ["Diff"] = (dfTemp.loc [:,whichPriceToCheck] - dfTemp.loc [firstIndex, whichPriceToCheck])
    maxDifAbs = float (dfTemp ["Diff"].abs().max())
    
    #this calculation is done now regardless of whether we are in base/base-short/base-long or not
    #they could be helpful in future for analysis purposes
    maxDif = float (dfTemp ["Diff"].max())
    maxDifStockPrice = float (dfTemp.loc [dfTemp.loc [:,"Diff"] == maxDif, whichPriceToCheck].head (1))
    #maxDifTime; requiring multiple steps
    maxDifTime = dfTemp.loc [dfTemp.loc [:,"Diff"] == maxDif, "TimeOnly"].head (1)
    testTime = convSeriesTimeToTime (maxDifTime.iloc[0]) #get time object
    maxDifTime = testTime #assign time object to maxDifTime

    minDif = float (dfTemp ["Diff"].min())
    minDifStockPrice = float (dfTemp.loc [dfTemp.loc [:,"Diff"] == minDif, whichPriceToCheck].head (1))
    #minDifTime; requiring multiple steps.
    minDifTime = dfTemp.loc [dfTemp.loc [:,"Diff"] == minDif, "TimeOnly"].head (1)
    testTime = convSeriesTimeToTime (minDifTime.iloc[0]) #get time object
    minDifTime = testTime #assign time object to minDifTime

    # print ("Max Different Absolute: " + str (maxDifAbs))
    # print ("Max Difference: " + str (maxDif))
    # print ("Min Difference: " + str (minDif))
    # print ("Max Dif Stock Price: " + str (maxDifStockPrice))
    # print ("Min Dif Stock Price: " + str (minDifStockPrice))

    #to be in a base, maxPriceDiff can't be bigger than this price
    maxPriceCriteria = dfStockPriceData.loc [firstIndex, whichPriceToCheck]*(baseTradePriceVarMaxPrcntg/100)
    #print ("Max Price Criteria: " + str (maxPriceCriteria))

    #if true then in a base
    if maxDifAbs <= maxPriceCriteria: 
        #Go Long
        if dfStockPriceData.loc [secondLastRowIndex +1, whichPriceToCheck] > maxDifStockPrice:
            tradeSignal = "Long"
            buyTime = dfStockPriceData.loc [secondLastRowIndex +1, "TimeOnly"]
            buyTimeIndex = secondLastRowIndex+1
            buyPrice = dfStockPriceData.loc [secondLastRowIndex +1, whichPriceToCheck]
            #stopLossPrice = minDifStockPrice #stop loss is the minimum of the base consolidation.
            #stopLossPrice = buyPrice - baseTradeLossTargetPerShare
            stopLossPrice = max (buyPrice - baseTradeLossTargetPerShare,minDifStockPrice) #choose the number that limits loss more
            limitSellPrice = buyPrice + baseTradeProfitTargetPerShare 
        #Go Short
        elif dfStockPriceData.loc [secondLastRowIndex +1, whichPriceToCheck] < minDifStockPrice:
            tradeSignal = "Short"
            buyTime = dfStockPriceData.loc [secondLastRowIndex +1, "TimeOnly"]
            buyTimeIndex = secondLastRowIndex+1
            buyPrice = dfStockPriceData.loc [secondLastRowIndex +1, whichPriceToCheck]
            # stopLossPrice = maxDifStockPrice #stop loss is the maximum of the base consolidation. 
            #stopLossPrice = buyPrice + baseTradeLossTargetPerShare
            stopLossPrice = min (buyPrice + baseTradeLossTargetPerShare, maxDifStockPrice) #choose the number that limits loss more
            limitSellPrice = buyPrice - baseTradeProfitTargetPerShare
        #Base Only
        else:
            tradeSignal = "Base"
            buyTime = "Nothing"
            buyTimeIndex = float ("nan")
            buyPrice = float ("nan")
            stopLossPrice = float ("nan")
            limitSellPrice = float ("nan")
    else: #not in a base and thus can't be short/long
        tradeSignal = "Nothing"
        buyTime = "Nothing"
        buyTimeIndex = float ("nan")
        buyPrice = float ("nan")
        stopLossPrice = float ("nan")
        limitSellPrice = float ("nan")

    #dictionary summarizing StartTime, EndTime and MaxDif for the duration
    dictTemp = {
        'Date': [dfStockPriceData.loc [firstIndex, "DateOnly"]], #Does not matter which row I use for date; date would be the same
        'StartTime':[dfStockPriceData.loc[firstIndex,"TimeOnly"]], 
        'EndTime':[dfStockPriceData.loc[secondLastRowIndex,"TimeOnly"]],
        'StartTimeIndex': [firstIndex],
        'EndTimeIndex': [secondLastRowIndex],
        'MaxDifStockPrice' :[maxDifStockPrice],
        'MinDifStockPrice' : [minDifStockPrice],
        'MaxDif':[maxDif],
        'MinDif':[minDif],
        'MaxDifAbs':[maxDifAbs],
        'MaxDifTime' : [maxDifTime], 
        'MinDiftime' : [minDifTime],
        'TradeSignal': [tradeSignal],
        'BuyTime': [buyTime],
        'BuyTimeIndex': [buyTimeIndex],
        'BuyPrice': [buyPrice],
        'StopLossPrice': [stopLossPrice],
        'LimitSellPrice': [limitSellPrice],
        'ExecutedOnSignal': ["Nothing"]
        }
    
    dfTemp2 = pd.DataFrame (dictTemp, index = [firstIndex])

	# #there will be a slight delay between getting the signal for buying vs. actually buying so have to adjust this buy price accordingly
	# #since this base trade algorithm takes seconds to run. This price difference might not be much
    return dfTemp2
# %%
def farFromMovingAverageTradeSignal (currentDate, currentPriceTimeIndex, lastPrice, currentPrice, listOfLastEma, currentRsi, farFromMovAvgCriticalPriceDif, farFromMovAvgProfitTargetPerShare):
    ''' (date, int, float, float, list, float, float, float) ---> (DataFrame)
    Argument Names:
        currentDate: current date
        currentPriceTimeIndex: current time given in minutes passed since 9:30 AM
        lastPrice: price of stock recorded last minute
        currentPrice: stock's current price
        listOfLastEma: EMA as per last stock's data
        currentRsi: RSI as per last stock's data
        farFromMovAvgCriticalPriceDif: amount of difference between stock and the EMA to be used for this algorithm
        farFromMovAvgProfitTargetPerShare: profit target per share

    Given current price data along with derived numbers and last minute data, output a DataFrame with result of running far from moving average trading algorithm
    '''
    
    #it seems that one of the pre condition is the stock falling or rising aboeve the moving average quickly.
    #in my case, I am only looking at the distance between stock price and closest ema to check for trading signal. I think stock falling or rising quickly will be captured by RSI
    

    tradeSignal = "Nothing" #This is initially set to nothing and stays nothing unless changed by conditions below; easier to manage logic
    difEmaFromLastPrice = [abs(ema-lastPrice) for ema in listOfLastEma]
    closestEmaDifAbs = min (difEmaFromLastPrice)
    closestEma = listOfLastEma[difEmaFromLastPrice.index (closestEmaDifAbs)]
    #first check if RSI is >=80 or RSI <=20
        #RSI >=80 likely means we are shorting and RSI <=20 likely means we are going long but not always
    if (currentRsi >=80) or (currentRsi <=20):
        #calculate the difference between the lastPrice and listOfLastEma to find the closest Ema
        #if abs (closest Ema Difference) >=1.50
        if closestEmaDifAbs >=farFromMovAvgCriticalPriceDif:
            # if (lastPrice > closestEma) and (RSI >=80) then far from moving average condition exist
            if (lastPrice>closestEma) and (currentRsi>=80):
                #if currentPrice < lastPrice ==> price broke trend and we go short, otherwise signal is just FarFromMovingAverage
                if currentPrice<lastPrice:
                    tradeSignal = "Short"
                else:
                    tradeSignal = "FarFromMovingAverage"
            # if (lastPrice < closestEma) and (RSI <=20) then far from moving average condition exist   
            elif (lastPrice<closestEma) and (currentRsi <=20):
                #if currentPrice > lastPrice ==> price broke trend and we go long, otherwise signal is just FarFromMovingAverage
                if currentPrice>lastPrice:
                    tradeSignal = "Long"
                else:
                    tradeSignal = "FarFromMovingAverage"

    #Setting buy price, limit sell price and stop loss price
    #if trade signal is long:
    if (tradeSignal == "Long") or (tradeSignal == "Short"):
        buyPrice = currentPrice 
        stopLossPrice = lastPrice
        if tradeSignal == "Long":
            limitSellPrice = currentPrice + farFromMovAvgProfitTargetPerShare
        else:
            limitSellPrice = currentPrice - farFromMovAvgProfitTargetPerShare
    else:
        buyPrice = float ("nan")
        stopLossPrice = float ("nan")
        limitSellPrice = float ("nan")

    #dictionary summarizing data
    dictTemp = {
        'CurrentDate': [currentDate],
        'LastPrice' : [lastPrice],
        'CurrentPrice': [currentPrice],
        'CurrentRsi': [currentRsi],
        'ClosestEmaPrice': [closestEma],
        'DiffFromClosestEma': [closestEmaDifAbs],
        'TradeSignal' :[tradeSignal],
        'BuyPrice' : [buyPrice],
        'LimitSellPrice': [limitSellPrice],
        'StopLossPrice' : [stopLossPrice],
        'ExecutedOnSignal' : ["Nothing"]
    }
    dfTemp = pd.DataFrame (dictTemp, index = [currentPriceTimeIndex])


    return dfTemp
# %%
def placeTrade(currentDay, baseTradeSummary, farFromMovAvgTradeSummary, allTradeSummary,stockDataLiveSimModified, baseTradeCheckDurationInMin, timeDurForCheck, startingBalance, currentBalance,dailyMaxLoss, brokerFee):
   
    '''(date, DataFrame, DataFrame, DataFrame,DataFrame, int, int, float, float,float, float) ---> (None/DataFrame, str, str)

    Given Trade Summary which shows if there is an active trade or not along with DataFrame for each algorithm, decide if a trade should be made while remaining within the constraints of daily maximum loss

    '''
   #assuming that 
    # one or more or all of baseTradeSummary, farFromMovAvgTradeSummary, allTradeSummary could be empty
    #stockDataLiveSimModified is not empty

    #First check scenarios where the dataframes are empty or not
        #baseTradeSummary: empty or not Empty
        #farFromMovAvgTradeSummary: not empty
        #allTradeSummary: empty or not empty
        #stockDataLiveSimModified: not empty
        #Total # of choices: 2 x 1 x 2 x 1 = 4
            #Empty, Not Empty, Empty, Not Empty
            #Not Empty, Not Empty, Empty, Not Empty
            #Empty, Not Empty, Not Empty, Not Empty
            #Not Empty, Not Empty, Not Empty, Not Empty

    #Overall Thnking
    #lets think about the possible scenarios
        #currentTradeStatus = Short, Long or Nothing
        #tradeSignalFromBaseTrade = Short, Long, Nothing
        #tradeSignalFromFarFromMovingAverageTrade = Short, Long, Nothing
        #daily max loss crossed or not (2 choices)
        #at 3:30 or not (2 choices)
    # the number of choices = 3 x 3 x 3 x 2 x 2 = 108

    #in bigger picture view, I either place a trade or don't place a trade
    #if I place a trade, I want to return data containing the dataframe of useful info
    #if I don't place a trade then I want to return None

    #initially we are assuming that we won't place a trade
    toPlaceTrade = "No"

    #Current Trade Status
    if allTradeSummary.shape [0]>=1:
        isTradeComplete = str (allTradeSummary.loc [allTradeSummary.index[-1],'IsTradeComplete'])
    else:
        isTradeComplete = "Yes"

    #initializing variables we will return
    tradeStatus = "Nothing"
    tradeType = "Nothing" #possible values: BaseTrade, FarFromMovingAverageTrade, Nothing
    tradeId = float ("nan") #used to link to baseTradeSummary or farfromMovAvgTradeSummary; tradeId = latestTimeIndex for far from moving average or startTimeIndex for baseTradeSummary
    buyPrice = float ("nan")
    limitSellPrice = float ("nan")
    stopLossPrice = float ("nan")

    #Extract TradeSignal and ExecutedOn from base trade and moving average trade dataframe
        #For base trade, we won't have anything to extract till the 31st minute so we are using if condition to take care of this
        #We are also using dataFrame.shape [0] >= 1 to avoid error
        #Executed On
            #Default values for both of them is "Nothing"
            #Initializing them here so if executedOn variable is not changed later on in the code, Python does not give error
    if (stockDataLiveSimModified.shape [0] >= (baseTradeCheckDurationInMin + timeDurForCheck)) & (baseTradeSummary.shape[0]>=1) : 
        baseTradeStatus = baseTradeSummary.loc [baseTradeSummary.index[-1], "TradeSignal"]
        baseTradeExecutedOn = baseTradeSummary.loc [baseTradeSummary.index[-1], "ExecutedOnSignal"] 
    else:
        baseTradeStatus = "Nothing"
        baseTradeExecutedOn = "Nothing"

    print (farFromMovAvgTradeSummary.shape [0])
    print (farFromMovAvgTradeSummary.shape [0]>=1)
    if farFromMovAvgTradeSummary.shape [0]>=1: 
        farFromMovAvgTradeStatus = farFromMovAvgTradeSummary.loc [farFromMovAvgTradeSummary.index[-1], "TradeSignal"]
        farFromMovAvgTradeExecutedOn = farFromMovAvgTradeSummary.loc [farFromMovAvgTradeSummary.index[-1], "ExecutedOnSignal"]
    else:
        farFromMovAvgTradeStatus = "Nothing"
        farFromMovAvgTradeExecutedOn = "Nothing"

    #Don't execute any trade if we have any of the following condition
        #We have reached 3:30 PM
        #We have reached daily loss limit
        #There is an active trade
    if (stockDataLiveSimModified.shape[0]>=361) or ((startingBalance-currentBalance)>=dailyMaxLoss) or (isTradeComplete == "No"):
        #since we won't execute any more trade
            ##if base trade status is short or long then update ExecutedOnSignal to No
            #if far from moving average trade status is short or long then update ExecutedOnSignal to No
        if (baseTradeStatus == "Short") or (baseTradeStatus == "Long"):
            baseTradeExecutedOn = "No"
        if (farFromMovAvgTradeStatus == "Short") or (farFromMovAvgTradeStatus == "Long"):
            farFromMovAvgTradeExecutedOn = "No"
    else:
        if (baseTradeStatus == "Short") or (baseTradeStatus == "Long"):
            tradeType = "BaseTrade"
            tradeStatus = baseTradeStatus
            #if at the same time far from momving average trade also tells us to go long or short
            #we don't execute on it and update ExecutedOnSignal to No
            if (farFromMovAvgTradeStatus == "Short") or (farFromMovAvgTradeStatus == "Long"):
                farFromMovAvgTradeExecutedOn = "No"
        elif (farFromMovAvgTradeStatus == "Short") or (farFromMovAvgTradeStatus == "Long"):
            tradeType = "FarFromMovingAverageTrade"
            tradeStatus = farFromMovAvgTradeStatus
        
    #Get parameters: tradeId, buyPrice, stopLossPrice, limitSellPrice if from checks so far, we should place a trade; this data is for all trade summary (only the trade we actually make)
    if tradeType == "BaseTrade":
        tradeId = baseTradeSummary.index [-1] #holds the Time Index of last trade which we acted on
        buyPrice =  float (baseTradeSummary.loc [tradeId,"BuyPrice"])
        stopLossPrice = float (baseTradeSummary.loc [tradeId,"StopLossPrice"])
        limitSellPrice = float (baseTradeSummary.loc [tradeId,"LimitSellPrice"])
    elif tradeType == "FarFromMovingAverageTrade":
        tradeId = farFromMovAvgTradeSummary.index [-1]
        buyPrice =  float (farFromMovAvgTradeSummary.loc [tradeId,"BuyPrice"])
        stopLossPrice = float (farFromMovAvgTradeSummary.loc [tradeId,"StopLossPrice"])
        limitSellPrice = float (farFromMovAvgTradeSummary.loc [tradeId,"LimitSellPrice"])
    
    #if we are placing a trade then
        #Calculate Max Possible Loss from this Trade
            #If that loss takes us over the daily max loss then don't execute on the trade
            #otherwise execute on the trade
    if tradeType!= "Nothing":
        numSharesBought = math.floor((currentBalance-2*brokerFee)/buyPrice) #this will produce error when both trading signal produces false
        maxPossibleLoss = numSharesBought* abs(buyPrice-stopLossPrice)+2*brokerFee #holds the max possible loss; number is always positive
        if (startingBalance - (currentBalance-maxPossibleLoss)) > dailyMaxLoss:
            toPlaceTrade = "No"
            if tradeType == "BaseTrade":
                baseTradeExecutedOn = "No"
            elif tradeType == "FarFromMovingAverageTrade": #could have also used else
                farFromMovAvgTradeExecutedOn = "No"
        else:
            toPlaceTrade = "Yes"
            if tradeType == "BaseTrade":
                baseTradeExecutedOn = "Yes"
            elif tradeType == "FarFromMovingAverageTrade": #could have also used else
                farFromMovAvgTradeExecutedOn = "Yes"

    #return dataframe containing trade summary if we are placing trade
    #or return None if we are not placing a trade
    if toPlaceTrade == "Yes":
        dictTemp = {
        'CurrentDay': [currentDay],
        'TradeType' :[tradeType],
        'TradeStatus': [tradeStatus],
        'TradeId' : [tradeId],
        'BuyPrice': [buyPrice],
        'LimitSellPrice': [limitSellPrice],
        'StopLossPrice' : [stopLossPrice],
        'NumShares': [numSharesBought],
        'Profit': [float ("nan")],    #Profit column will be updated by other functions when we sell our stock
        'IsTradeComplete': ["No"],    #Will be changed to "Yes" when we exit the trade
        'SoldTime': [float ("nan")]   #Will be updated with real time when the trade is complete
        } 
        dfTemp = pd.DataFrame (dictTemp, index = [stockDataLiveSimModified.index[-1]])
        return dfTemp, baseTradeExecutedOn, farFromMovAvgTradeExecutedOn
    else:
        return None, baseTradeExecutedOn, farFromMovAvgTradeExecutedOn
 # %%
def checkIfExitTrade (currentTradeSummary, currentPriceData, whichPriceToCheck):
    ''' (DataFrame, DataFrame, string) ---> (DataFrame/None)

    Given details about current trade (buy time, buy price, limit sell and stop loss price, etc.) and current price, see if the trade should be closed
    '''

    #Current trade summary and current price data is both one row of data
    #This function is called when we have an active trade going

    updatedTradeSummary = currentTradeSummary

    #Extract data to see if limit loss or stop loss is triggerred
    currentPrice = float (currentPriceData.loc [currentPriceData.index [-1], whichPriceToCheck])
    buyPrice = float (currentTradeSummary.loc [currentTradeSummary.index [-1], "BuyPrice"])
    limitSellPrice= float (currentTradeSummary.loc [currentTradeSummary.index [-1], "LimitSellPrice"])
    stopLossPrice  = float (currentTradeSummary.loc [currentTradeSummary.index [-1], "StopLossPrice"])
    currentTradeStatus = str (currentTradeSummary.loc [currentTradeSummary.index [-1], "TradeStatus"]) #Short or Long
    numSharesBought = float (currentTradeSummary.loc [currentTradeSummary.index [-1], "NumShares"])

    #See if limit sell or stop loss was triggerred if market sell was not triggerred
    currentTradeStatus, currentTradeProfit = limitStopLossSell  (currentTradeStatus, currentPrice, buyPrice, stopLossPrice, limitSellPrice, numSharesBought)
    
    #Exit all trade by 3:50 PM; 380 is chronolgoical index for 3:50 PM
    if (currentPriceData.index [-1] >=380) and (currentTradeStatus!="Nothing"): #Second condition is to bypass market sell if limit sell or stop loss above was triggerred
         currentTradeStatus, currentTradeProfit = marketSell (currentTradeStatus, currentPrice, buyPrice, numSharesBought)
    
    #Trade was exited. Update this columns in currentTradeSummary: 
    if currentTradeStatus == "Nothing":
        updatedTradeSummary.loc [updatedTradeSummary.index [-1],"Profit"] =  currentTradeProfit
        updatedTradeSummary.loc [updatedTradeSummary.index [-1],"IsTradeComplete"] = "Yes"
        updatedTradeSummary.loc [updatedTradeSummary.index [-1],"SoldTime"] = currentPriceData.loc [currentPriceData.index [-1], "TimeOnly"]
        return updatedTradeSummary
    else:
        return None
# %%
def smaEma (stockDataPreviousDay,stockDataCurrentDay, period, colTitleForSmaEma):
    '''(DataFrame, DataFrame, int, str) --> (str, float, str, float)

    Given current day and previous day stock data, return EMA and SMA over the specified period
    '''

    #takes a dataframe with minute interval and adds SMA# and EMA# column
    #need to check dataframe so I only have columns with data type integer or float
    dataFrameSmaEma = stockDataPreviousDay
    dataFrameSmaEma = dataFrameSmaEma.append (stockDataCurrentDay)
    #previous and current day both have same indices. So dataFrameSmaEma have duplicate indices now. 
    # This line sets unique indices which is necessary for EMA calculation
    dataFrameSmaEma.index = range (0,dataFrameSmaEma.shape[0],1) 

    #set index to Datetime to avoid calculating rolling mean on Datetime
    #dataFrameSmaEma.set_index (dataFrameSmaEma.columns[0], inplace = True)

    #add SMA column and values
    smaColTitle = "SMA" + str (period)
    #print (dataFrameSmaEma.head ())
    #dataFrameSmaEma [smaColTitle] = dataFrameSmaEma[].rolling (period).mean ()[colTitleForSmaEma] #add SMA values
    dataFrameSmaEma [smaColTitle] = dataFrameSmaEma[colTitleForSmaEma].rolling (period).mean () #add SMA values

    #add EMA column
    #dataFrameSmaEma.reset_index (inplace = True) #reset index to be able to index by integer
    emaWeight = 2/ (period + 1)
    emaColTitle = "EMA" + str (period)
    dataFrameSmaEma [emaColTitle] = float ("nan") #creating a column EMA9 which is nan values for all; not sure if this step is necessary but doing this to avoid error later
    #print (dataFrameSmaEma.columns)

    # try:
    for i in range (0,dataFrameSmaEma.shape [0],1):
        if i == (period-1):
            dataFrameSmaEma.loc [i,emaColTitle] = dataFrameSmaEma.loc [i,smaColTitle] #first EMA value is just the SMA
        elif i>=period:
            dataFrameSmaEma.loc [i,emaColTitle] = dataFrameSmaEma.loc [i,colTitleForSmaEma]*emaWeight + dataFrameSmaEma.loc [i-1,emaColTitle]*(1-emaWeight)
        else:
            dataFrameSmaEma.loc [i,emaColTitle] = float ("nan") #otherwise those EMA values don't exist
    # except Exception:
    #     traceback.print_exc()
    #     print ("Hello")

    #dataFrameSmaEma.set_index (dataFrameSmaEma.columns[0], inplace = True) #set the index back to original datframe's index
    # testInt = stockDataCurrentDay.shape[0]
    # tempDf = dataFrameSmaEma.tail (stockDataCurrentDay.shape[0])

    smaPeriod = float (dataFrameSmaEma.tail (1)[smaColTitle])
    emaPeriod = float (dataFrameSmaEma.tail (1)[emaColTitle])

    return smaColTitle, smaPeriod, emaColTitle, emaPeriod
    #return dataFrameSmaEma.tail (stockDataCurrentDay.shape[0]) #only return dataframe for current day
# %%
def rsiPreviousDay (stockDataPreviousDay, period, colTitleForRSI):
    '''(DataFrame, int, str) ---> (DataFrame)

    Given last day's stock data from Yahoo Finance, return the same DataFrame with RSI calculated
    '''
    #have to pass in dataframe with integer as the indices
    stockDataPreviousDay ["Change"] = stockDataPreviousDay [colTitleForRSI].diff () #change from last minute price
    #holding positive change and negative change data in seperate columns
    stockDataPreviousDay ["Gain"] = 0 #initializing columns
    stockDataPreviousDay ["Loss"] = 0
    stockDataPreviousDay ["Gain"] = stockDataPreviousDay.loc [stockDataPreviousDay ["Change"]>0, "Change"] #positive change
    stockDataPreviousDay ["Loss"] = stockDataPreviousDay.loc [stockDataPreviousDay ["Change"]<0, "Change"].abs () #average loss; converted to positive
    stockDataPreviousDay ["Gain"].fillna (0, inplace = True) #replace na missing values with 0
    stockDataPreviousDay ["Loss"].fillna (0, inplace = True)

    #initialize more columns
    stockDataPreviousDay ["AvgGain"] = float ("nan")
    stockDataPreviousDay ["AvgLoss"] = float ("nan")
    stockDataPreviousDay ["RS"] = float ("nan")
    rsiColTitle = "RSI{0}".format (period)
    stockDataPreviousDay [rsiColTitle] = float ("nan")

    for i in range (period, stockDataPreviousDay.shape[0],1):
        # print (stockDataPreviousDay.iloc[1:period+1,:])
        if i == period: #for the first RSI (at i = period), average gain and loss is simply simple average over n period
            dfTemp = stockDataPreviousDay.iloc[1:period+1,:]
            avgGain = float (dfTemp ["Gain"].mean ())
            avgLoss = float (dfTemp ["Loss"].mean ())
        else:
            avgGain = float ((stockDataPreviousDay.loc [i-1,"AvgGain"]*(period-1) + stockDataPreviousDay.loc [i,"Gain"])/period)
            avgLoss = float ((stockDataPreviousDay.loc [i-1,"AvgLoss"]*(period-1) + stockDataPreviousDay.loc [i,"Loss"])/period)
    
        #When average loss is 0, RS is undefined and RSI = 100
        if avgLoss !=0:
            rs = avgGain/avgLoss
            rsi = 100 - 100/(1+rs)
        else: 
            rs = float ("nan")
            rsi = 100
        
        #Updating values of table; not sure if necessary
        stockDataPreviousDay.loc [i,"AvgGain"] = avgGain
        stockDataPreviousDay.loc [i,"AvgLoss"] = avgLoss
        stockDataPreviousDay.loc [i,"RS"] = rs
        stockDataPreviousDay.loc [i,rsiColTitle] = rsi
        # stockDataPreviousDay [i,rsiColTitle] = rsi
    return stockDataPreviousDay #return the stock price dataframe with RSI values calculated
# %%
def rsi (priceChange, colTitleForRSI, period, previousAvgGain, previousAvgLoss):
    '''(float, str, int, float, float) ---> (float)

    Given price change, period over which to calculate RSI for and average gain/loss, calculate RSI
    '''
    #calculate rsi for latest minute

    if priceChange > 0:
        gain = priceChange
        loss = 0
    else:
        loss = abs (priceChange)
        gain = 0
    
    avgGain = (previousAvgGain*(period-1) + gain)/period
    avgLoss = (previousAvgLoss*(period-1) + loss)/period

    if avgLoss !=0:
        rs = avgGain/avgLoss
        rsi = 100 - 100/(1+rs)
    else: 
        rs = float ("nan")
        rsi = 100
    return avgGain, avgLoss, rsi
# %%
def tradeOneDay ():

    '''
    Function for simulating trading over specified data in "CurrentDay" variable
    '''

    #Days for downloading data from yahoo finance
    currentDay = dt.datetime.strptime ("2020-04-02","%Y-%m-%d").date() #day object

    previousBusinessDay = currentDay - BDay (1) #previous business day time stamp
    #previousBusinessDay = convTimeStampToDay (previousBusinssDay,"%Y-%m-%d %H:%M:%S") #get day object
    previousBusinessDay = pd.Timestamp.date (previousBusinessDay)

    nextBusinessDay = currentDay + BDay (1) #previous business day time stamp
    #nextBusinessDay = convTimeStampToDay (nextBusinessDay,"%Y-%m-%d %H:%M:%S") #get day object
    nextBusinessDay = pd.Timestamp.date (nextBusinessDay)

    #stock data for current date; we will simulate trading for current date (not = present day in simulated trades)
    stockData1mIntervalCurrent = yf.download (tickers = "AAPL", start= currentDay, end = nextBusinessDay, interval= "1m")
    stockData1mIntervalCurrentModified = preProcessStockData (stockData1mIntervalCurrent)

    #stock data for previous business day; we need this data for SMA/EMA
    stockData1mIntervalPreviousBusinessDay = yf.download (tickers = "AAPL", start= previousBusinessDay, end = currentDay, interval= "1m")
    stockData1mIntervalPreviousBusinessDayModified = preProcessStockData (stockData1mIntervalPreviousBusinessDay)

    startingBalance = 10000 #starting balance is 10,000
    dailyMaxLoss = 100 #max loss per day is $100

    currentDayStockData, baseTradeSummary, farFromMovAvgTradeSummary, allTradeSummary, currentBalance = main(currentDay,stockData1mIntervalCurrentModified,stockData1mIntervalPreviousBusinessDayModified,
                                                                                                                startingBalance, dailyMaxLoss)
    print ("Profit Today {0}".format (currentBalance-startingBalance))
    
    filePath1 = r"C:\Users\KI PC\OneDrive\Documents\Finance\V5 Bot Export\StockData.csv"
    filePath2 = r"C:\Users\KI PC\OneDrive\Documents\Finance\V5 Bot Export\BaseTradeSummary.csv"
    filePath3 = r"C:\Users\KI PC\OneDrive\Documents\Finance\V5 Bot Export\FarFromMovingAverageTradeSummary.csv"
    filePath4 = r"C:\Users\KI PC\OneDrive\Documents\Finance\V5 Bot Export\AllTradeSummary.csv"

    currentDayStockData.to_csv (filePath1)
    baseTradeSummary.to_csv (filePath2)
    farFromMovAvgTradeSummary.to_csv (filePath3)
    allTradeSummary.to_csv (filePath4)
# %%
def tradeMultipleDay ():
    '''
        Function for simulating trading over multiple days
        Obtaining data for all the days from a CSV file for now as Yahoo Finance app only gives 1 minute interval data for last 30 days
    '''
    #30 day of stock data from csv file
    filePath = r"C:\Users\KI PC\OneDrive\Documents\Finance\Companies Data Export_2020_03_09_To_2020_04_03\2020_03_09_To_2020_04_03_AAPL.csv"
    stockDataHistorical = pd.read_csv (filePath)
    stockDataHistorical.columns = ["Datetime", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    stockDataHistorical ["Datetime"] = pd.to_datetime (stockDataHistorical ["Datetime"]) 
    stockDataHistorical ["DateOnly"] = stockDataHistorical ["Datetime"].dt.date

    listOfSortedDates = stockDataHistorical ["DateOnly"].unique()
    listOfSortedDates.sort ()

    startingBalance = 10000 #starting balance is 10,000
    dailyMaxLoss = 100 #max loss per day is $100

    #Dataframes for holding trade summary
    stockDataSummary = pd.DataFrame ()
    baseTradeSummary = pd.DataFrame ()
    farFromMovAvgTradeSummary = pd.DataFrame ()
    allTradeSummary = pd.DataFrame ()
    currentBalanceSummary = pd.DataFrame ()

    currentBalance = startingBalance #first balance is = startingBalance

    for i in range (len(listOfSortedDates)-1):
        currentDay = listOfSortedDates [i+1]
        previousBusinessDay = listOfSortedDates [i]

        #current day stock data
        stockData1mIntervalCurrent = stockDataHistorical.loc [stockDataHistorical ["DateOnly"] == currentDay,:] #don't need to preprocess stock data
        #changing index of stock data to start from 0
        stockData1mIntervalCurrent.index = range (0,stockData1mIntervalCurrent.shape[0],1)

        print (stockData1mIntervalCurrent.head ())

        #previous day stock data; we need this data for SMA/EMA and RSI
        stockData1mIntervalPreviousBusinessDay = stockDataHistorical.loc [stockDataHistorical ["DateOnly"] == previousBusinessDay,:] #don't need to preprocess stock data
        #changing index of stock data to start from 0
        stockData1mIntervalPreviousBusinessDay.index = range (0,stockData1mIntervalPreviousBusinessDay.shape[0],1)
        print (stockData1mIntervalPreviousBusinessDay.head ())

        #Get result for current date
        stockDataCurrentDay, baseTradeSummaryCurrentDay, farFromMovAvgTradeSummaryCurrentDay, allTradeSummaryCurrentDay, currentBalance = main(currentDay, 
                                                                                                                                            stockData1mIntervalCurrent,
                                                                                                                                            stockData1mIntervalPreviousBusinessDay, 
                                                                                                                                            currentBalance, 
                                                                                                                                            dailyMaxLoss)

        
        #Summary for current balance vs. dates. Might be useful later on
        dictTemp = {'Date': [currentDay],
                                 'EndingBalance': [currentBalance]}
        dfTemp = pd.DataFrame (dictTemp, index = [i+1])

                                 
        if i == 0:
            stockDataSummary = stockDataCurrentDay
            baseTradeSummary = baseTradeSummaryCurrentDay
            farFromMovAvgTradeSummary = farFromMovAvgTradeSummaryCurrentDay
            allTradeSummary = allTradeSummaryCurrentDay
            currentBalanceSummary = dfTemp
        else:
            stockDataSummary = stockDataSummary.append (stockDataCurrentDay)
            baseTradeSummary = baseTradeSummary.append (baseTradeSummaryCurrentDay)
            farFromMovAvgTradeSummary = farFromMovAvgTradeSummary.append (farFromMovAvgTradeSummaryCurrentDay)
            allTradeSummary = allTradeSummary.append (allTradeSummaryCurrentDay)
            currentBalanceSummary = currentBalanceSummary.append (dfTemp)

    filePath1 = r"C:\Users\KI PC\OneDrive\Documents\Finance\V7 Bot Export\StockData30Days.csv"
    filePath2 = r"C:\Users\KI PC\OneDrive\Documents\Finance\V7 Bot Export\BaseTradeSummary30Days.csv"
    filePath3 = r"C:\Users\KI PC\OneDrive\Documents\Finance\V7 Bot Export\FarFromMovingAverageTradeSummary30Days.csv"
    filePath4 = r"C:\Users\KI PC\OneDrive\Documents\Finance\V7 Bot Export\AllTradeSummary30Days.csv"
    filePath5 = r"C:\Users\KI PC\OneDrive\Documents\Finance\V7 Bot Export\BalanceChange30Days.csv"

    stockDataSummary.to_csv (filePath1)
    baseTradeSummary.to_csv (filePath2)
    farFromMovAvgTradeSummary.to_csv (filePath3)
    allTradeSummary.to_csv (filePath4)
    currentBalanceSummary.to_csv (filePath5)
# %%
if __name__ == "__main__":
    # #For trading one day only using yahoo finance data
    # tradeOneDay ()

    #For trading multiple days using csv files data
    tradeMultipleDay ()
# %%
