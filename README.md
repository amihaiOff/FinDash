# FinDash 
(naming suggestions are welcome)

## Features
* Create expense categories (e.g. bills, medical, rent, going out etc.) 
  with expense goals to define a budget.
* Import csv\excel transactions files from you bank and credit card companies
* Keep track of expense categories throughout the month
* Look at analysis of your historical data to see behavioural trends
* Split one transaction into multiple when it contains multiple categories.
  For example when buying on Amazon groceries and personal items.
* [Coming soon] Pension and investments tracking
* [Coming soon] Automatic scraping from Israeli financial institutions 
  (using [Israeli-bank-scrappers](https://github.com/eshaham/israeli-bank-scrapers)
  
  <img aling='right', width="958" alt="image" src="https://github.com/amihaiOff/FinDash/assets/57396603/0cc8848f-c525-47d7-aff9-48222d078f69">

  
## How to run

clone this repo
```bash
git clone https://github.com/amihaiOff/FinDash.git
```
[install poetry](https://python-poetry.org/docs/#installation) if you don't already have it installed

then run 
```bash
cd FinDash
poetry install
cd findash
poetry run python main.py
```


## Structure
The current implementation uses Plotly Dash as a front end and parquet 
files as the DB to save financial transaction data. Future implementation 
might move to a proper SQL DB, depending on the needs.

## Idea
FinDash is an all-in-one personal financial dashboard, organizing things 
such as budget, expenses, savings, investments and more. The goal of this 
dashboard is to be able to get full visibility into ones whole financial 
state including analytics, to help navigate the complex financial world 

### Expense tracking vs Budgeting

The idea for the app came to me when we were looking to move apartment, and 
didn't really know what our budget was for rent. We were moving to a new 
city with higher rent prices so we in order to make an informed decision, 
we needed to map out our expenses and goals (we love to travel :) ) and see 
how everything would fit in given our set amount of income. This made me 
realize the difference between passive expense tracking and active budgeting. 


Many personal finance apps mainly do one thing, which is expense tracking. 
Credit card and cash transactions are fed into the app and categorized, 
showing the user how much money was spent in each category. While this is 
extremely important, it is only half the picture. What is missing is are 
budgeting goals.

Ultimately, most of us have a fixed income, finite amount of resources we 
need to work with to achieve our goals. Whether it be to buy a house, go on 
a big trip, or just manage our spending behaviour, we have one pie we need 
to divide between all our wants. This faces us with choices we need to make,
do we spend more on food or on entertainment? How much do we save? etc. These 
questions are not answered by expense tracking alone, but by budgeting, by 
giving each expense category a goal we want to reach. This is a main 
functionality of FinDash - the ability to set expense\savings goals and 
keep track of them. 

### Behaviour tracking
As mentioned above, setting budgeting goals is very important to help us 
achieve the goals we want, while managing our available income. A major 
hurdle to overcome while striving to our goals are our own habits. While 
this isn't a habit changing app, it does provide a bunch of analytics to 
gain insights into our routines and habits, hopefully making it easier to 
find causes and change towards the path we want to take.
