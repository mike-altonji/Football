# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 19:59:41 2020

@author: mikea
"""

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import urllib.request
import os

if os.name == 'nt': os.chdir('C:/Users/mikea/Documents/Analytics/Football Analytics/Kickers/')
else: os.chdir('/home/mike/Analytics/Football Analytics/Kicker Web Scrape/')

df = pd.read_csv('kicking_merged.csv')

# Get list of names
all_names_space = list(df['Name'].unique())
all_names = [name.split(' ') for name in all_names_space]
for i in range(len(all_names)):
    row = all_names[i]
    row.append(row[-1] + ', ' + row[0])
    row.append(all_names_space[i])

link = 'https://www.footballdb.com/players/players.html'
pos = 'K' # Can make this dynamic as needed

### For a given lastname...
correct_links = list()
# all_lastnames = ['smith'] # test
for row in all_names:
    firstname = row[0]
    lastname  = row[1]
    last_comma_first = row[2]
    name_space = row[3]
    
    print(f'Analyzing Kicker: {last_comma_first}')
    
    player_strings = list()
    page=1
    more_pages = True
    while more_pages:
        src = urllib.request.urlopen(link+'?q='+lastname+'&page='+str(page)).read()
        soup = BeautifulSoup(src, features='lxml')
        for url in soup.find_all('a'):
            string = url.get('href')
            if string.startswith('/players/') and ('-' in string):
                player_strings.append(string[9:])
        
        # Want to look at the tmp_df to find only kickers, in case there are multiple of the same name.
        # Assumes no two kickers have the same exact name. In that case, I'd need to regex the "Teams" field.
        if page==1: tmp_df = pd.read_html(link+'?q='+lastname+'&page='+str(page))[0]
        else: tmp_df = tmp_df.append(pd.read_html(link+'?q='+lastname+'&page='+str(page))[0])
        
        # If there are additional pages, keep scrolling
        if len(player_strings) >= 200*page: page += 1
        else: more_pages = False
    
    # Decide if we found a unique match
    tmp_df.reset_index(drop=True, inplace=True)
    position_df = tmp_df[tmp_df['Pos'] == pos]
    if len(position_df) > 1: 
        position_df = position_df[position_df['Player'] == last_comma_first] # Only doing this when I have to...not confident names will always match
        if len(position_df) == 1:
            correct_links.append([firstname, lastname, last_comma_first, name_space, player_strings[position_df.index[0]]])
        elif len(position_df) > 1: print('Warning! More than one player of this name at this position:', last_comma_first)
        else: print(f'Error: No players have this name when I look at the full name, but there were >1 when looking at just lastname.')
    elif len(position_df) == 0:
        print('This player probably isnt a Kicker, as no one showed up.', last_comma_first)
    elif len(position_df) == 1: correct_links.append([firstname, lastname, last_comma_first, name_space, player_strings[position_df.index[0]]])
pd.DataFrame(correct_links, columns=['First_Name', 'Last_Name', 'Last_Comma_First', 'Name', 'link']).to_csv('correct_links.csv')

######### Given links, grab all kicker info -----------------------------------
### For a given lastname...
link = 'https://www.footballdb.com/players/'
first = True
df_len = 0 # For debugging
for row in correct_links:
    firstname = row[0]
    lastname  = row[1]
    last_comma_first = row[2]
    name_space = row[3]
    player_link = row[4]
    print(f'Analyzing Kicker: {last_comma_first}')
    
    seasons = df[df['Name'] == name_space]['year'].unique()
    
    for season in seasons:
        print(f'...Season {season} of {min(seasons)}')
        unique_link = f'{link}{firstname}-{lastname}-{player_link}/gamelogs/{season}'
        if first: 
            pat_df = pd.read_html(unique_link)[0]
            pat_df['Name'] = name_space
            first = False
        else: 
            tmp_df = pd.read_html(unique_link)[0]
            tmp_df['Name'] = name_space
            pat_df = pat_df.append(tmp_df)
        
        if len(pat_df) < df_len: print('STOP: Losing Rows...')
        df_len = len(pat_df)
    
pat_df.reset_index(drop=True, inplace=True)
pat_df.to_csv('pat_df.csv')
pat_df.columns = pat_df.columns.map(''.join)
pat_df=pat_df.rename(columns={pat_df.columns[0]: 'Date', pat_df.columns[3]: 'PAT_M', pat_df.columns[4]: 'PAT_A'})
pat_df_small = pat_df[['Date', 'PAT_M', 'PAT_A']]
pat_df_small['Date'] = pd.to_datetime(pat_df_small['Date'])

# Add Year/Week of schedule
schedule = pd.read_csv('NFL Schedule.csv', parse_dates=['Start_Date', 'End_Date'])

def nfl_week(date, schedule):
    subset = schedule[(schedule['Start_Date'] <= date) & (schedule['End_Date'] > date)]
    if len(subset) > 0:
        week = subset['Week'].iloc[0]
        year = subset['Year'].iloc[0]
    else: # Preseason and Postseason dont count
        week = np.nan
        year = np.nan
    return week, year
pat_df_small['week'], pat_df_small['year'] = zip(*pat_df_small['Date'].apply(lambda date: nfl_week(date, schedule)))
pat_df_small = pat_df_small[np.isnan(pat_df_small['week']) == False]
# --------------------------------------------------------------------------


# NEXT STEP: break pat_df_small into individual kicks (with MADE=1/0, BLK=NA). THEN, merge w/weather.
# This belongs in "Kickers.py" code!!!
kicks2 = kicks.merge(pat_df_small, on=['Name', ], how='left') # Don't merge...append as new rows!
