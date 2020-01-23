#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 11:41:59 2020

@author: mike
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 11:35:08 2020

@author: mike
"""

import numpy as np
import pandas as pd
import re
import os

if os.name == 'nt': os.chdir('C:/Users/mikea/Documents/Analytics/Football Analytics/Kickers/Football/')
else: os.chdir('/home/mike/Analytics/Football Analytics/Kicker Web Scrape/')

# -----------------------------------------------------------------------------
######### Weather Data

######### USER INPUTS
year_start = 2009
year_end   = 2018 # Change to include 2019 when available
link = 'http://www.nflweather.com'

# Start by only looking at Regular Season games
years = [i for i in range(year_start, year_end+1)]
weeks = [i for i in range(1, 18)]


# Takes ~3 minutes
all_weeks = list()
for y in years:
    print(f'Working on Year {y}...')
    for w in weeks:
        
        if y == 2010:
            url = '/en/week/'+str(y)+'/week-'+str(w)+'-2/' # 2010's archive format is different
        else:
            url = '/en/week/'+str(y)+'/week-'+str(w)+'/'
        
        df_list = pd.read_html(link+url)
        for df in df_list:
            df['year'] = y
            df['week'] = w
            all_weeks.append(df)
        

first = True
for df in all_weeks:
    if first:
        weather_df = df
        first = False
    else:
        weather_df = weather_df.append(df)
weather_df = weather_df[['Away', 'TV', 'Wind', 'Unnamed: 11', 'year', 'week']]
weather_df = weather_df.reset_index(drop=True)
weather_df = weather_df.rename(columns={'TV':'Home', 'Wind':'Weather', 'Unnamed: 11':'Wind'})


### Create additional columns for Weather
def weather_fxn(row):
    # Weather
    w = row['Weather'].upper()
    row['Snow'] = bool(re.search('.*SNOW.*', w)) or bool(re.search('.*BLIZZARD.*', w)) or bool(re.search('.*FLURR.*', w))
    row['Rain'] = bool(re.search('.*RAIN.*', w)) or bool(re.search('.*SHOWER.*', w)) or bool(re.search('.*THUNDER.*', w)) or bool(re.search('.*DRIZZLE.*', w))
    row['Dome'] = bool(re.search('.*DOME.*', w))
    if row['Dome']:
        row['Temperature'] = np.nan # May want to overwrite with 70f...TBD
    elif bool(re.match('([0-9]+)F', w)):
        row['Temperature'] = float(re.match('([0-9]+)F', w).group(1)) # Wont handle negatives correctly, but unlikely scenario
    else:
        row['Temperature'] = np.nan
    
    # Wind
    if isinstance(row['Wind'], str):
        wind = row['Wind'].upper()
        wind_dir_start = re.match('.* ', wind).end()
        row['Wind_Direction'] = wind[wind_dir_start:]
        row['Wind_Speed'] = float(re.match('([0-9]+)M', wind).group(1))
    else:
        row['Wind_Direction'] = np.nan
        row['Wind_Speed'] = np.nan
    
    if row['Dome']:
        row['Wind_Speed'] = 0 # Overwrite wind speed indoors to 0
    
    return row

weather_df = weather_df.apply(lambda row: weather_fxn(row), axis=1)
weather_df.to_csv('weather_df.csv') # Save dataframe


# -----------------------------------------------------------------------------
######## Kicker Data
# Kicking data courtosy of pro=football-reference, a Sports Reference site. https://www.pro-football-reference.com/play-index/fg_finder.cgi
weather_df = pd.read_csv('weather_df.csv', index_col=0)

kicks = pd.read_csv('all_kicks.csv', parse_dates=['Date'])
kicks['Name'], kicks['Player_ID'] = zip(*kicks['Player'].apply(lambda x: x.split('\\')))

# Make new "Good" columns with boolean values
kicks['Good'] = kicks['Good?'].apply(lambda x: 1 if x=='Y' else 0)
kicks['Blocked'] = kicks['Blk?'].apply(lambda x: 1 if x=='Y' else 0)

# Drop old columns
kicks = kicks.drop(columns=['Rk', 'Unnamed: 3', 'Opp', 'Result', 'Player', 'Good?', 'Blk?'])

# Add Year/Week of schedule
schedule = pd.read_csv('NFL Schedule.csv', parse_dates=['Start_Date', 'End_Date'])

def nfl_week(date, schedule):
    subset = schedule[(schedule['Start_Date'] <= date) & (schedule['End_Date'] > date)]
    week = subset['Week'].iloc[0]
    year = subset['Year'].iloc[0]
    return week, year
kicks['week'], kicks['year'] = zip(*kicks['Date'].apply(lambda date: nfl_week(date, schedule)))

# Set up data to be mergeable with weather data
team_names = pd.read_csv('team_name_map.csv', index_col=0).to_dict()['weather']
kicks['Team'] = kicks['Tm'].apply(lambda team: team_names[team])
weather_df2 = weather_df.copy()
weather_df['Team']  = weather_df['Home']
weather_df2['Team'] = weather_df2['Away']
weather_df  = weather_df.drop(columns=['Home', 'Away'])
weather_df2 = weather_df2.drop(columns=['Home', 'Away'])
weather_df_final = weather_df.append(weather_df2)

# Merge and subset
total = kicks.merge(weather_df_final, how='left', on=['Team', 'year', 'week'])
df = total[(total['year'] >= 2012) & (total['year'] <= 2018)] # Range of dates with wind data

# STILL NEED PATs!!!
# -----------------------------------------------------------------------------
# Games played above 50degF, under 5mph wind, no snow/rain, OR in a dome
nice = df[((df['Rain']==False) & (df['Snow']==False) & (df['Temperature'] > 50) & (df['Wind_Speed'] <= 5)) | (df['Dome']==True)]
nice_year = nice.groupby(['year']).mean()[['Dist', 'Temperature', 'Wind_Speed', 'Good']]
all_year  = total.groupby(['year']).mean()[['Dist', 'Temperature', 'Wind_Speed', 'Good']]

from matplotlib import pyplot as plt
plt.scatter(nice_year.index, nice_year['Good'])
plt.scatter(all_year.index, all_year['Good'])
