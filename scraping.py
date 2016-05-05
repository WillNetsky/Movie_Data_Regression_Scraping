import string
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import requests
import datetime
import re
from fake_useragent import UserAgent
ua = UserAgent()
from datetime import time
import omdb




def remove_punctuation(x):
    x = str(x)
    return x.translate(str.maketrans({a:None for a in string.punctuation}))

def get_soup(url, timeout=5):
    headers  = {'User-Agent':ua.random}
    try:
        response = requests.get(url,headers=headers)
    except:
        print("FAILED "+ url)
        return 0
    attempts = 0
    while(not response.ok):
            print((url+' failed with code: '+str(response.status_code)))
            if attempts > timeout:
                raise Exception(url+' failed with code: '+str(response.status_code))
            response = requests.get(url)
            attempts += 1
    page = response.text
    soup = BeautifulSoup(page,'lxml')
    return soup

def scrape_opening_weekend(year=2015):
    url = 'http://www.boxofficemojo.com/yearly/chart/?yr='+str(year)+'&p=.htm'
    response = requests.get(url)
    while(not response.ok):
        response = requests.get(url)

    page = response.text
    soup = BeautifulSoup(page,'lxml')

    # Find number of pages on table for the year
    item = soup.find('center')
    pages = len(item.find_all('a'))+1

    # Pull table from each page
    for i in range(1,pages+1):
        url = 'http://www.boxofficemojo.com/yearly/chart/?page='+str(i)+'&view=releasedate&view2=domestic&yr='+str(year)+'&sort=opengross&p=.htm'
        tables = pd.read_html(url)
        table = tables[2]
        table = table.iloc[6:-6,2:9]
        table.columns = ['title','studio','total_gross','total_theatres','opening','opening_theatres','release_date']
        if i==1:
            df = table
        else:
            df = pd.concat([df,table])

    # Clean up dataframe types
    df.release_date = pd.to_datetime(df.release_date+str(year),format='%m/%d%Y')
    df = df.dropna(subset=['opening','opening_theatres'])
    df.total_gross = df.total_gross.map(lambda x: int(remove_punctuation(x)))
    df.total_theatres = df.total_theatres.map(lambda x: int(x))
    df.opening = df.opening.map(lambda x: int(remove_punctuation(x)))
    df.opening_theatres = df.opening_theatres.map(lambda x: int(x))
    return df

def get_torrent_stats(df_row):
    title = remove_punctuation(df_row.title)
    title = title.replace(' ','%20')
    url = 'https://thepiratebay.se/search/'+str(title)+'%20'+str(df_row.year)+'/0/4/0'
    print(df_row.title)
    soup = get_soup(url)


    time.sleep(0.5)

    if soup == 0:
        return df_row

    activity = 0
    num_torrents = 0
    for row in soup.find_all('tr')[1:]:
        tds = row.find_all('td')
        #activity += int(tds[2].get_text()) + int(tds[3].get_text())
        text = tds[1].get_text().split('\n')[4].replace('\xa0',' ')
        reg = re.compile('[0-9]+-[0-9]+ [0-9]+\:[0-9]+|[0-9]+-[0-9]+ [0-9]+')
        try:
            date = re.findall(reg, text)[0]
        except:
            date = datetime.today()
        try:
            date = datetime.strptime(date,'%m-%d %Y')
        except:
            try:
                date = datetime.strptime(date+datetime.today().year,'%m-%d %H:%M%Y')
            except:
                date = datetime.today()
        if date <= df_row.release_date:
            num_torrents += 1
            activity += int(tds[2].get_text()) + int(tds[3].get_text())
    df_row['num_torrents'] = num_torrents
    df_row['torrent_activity'] = activity
    return df_row

def find_omdb_movie(title,year):
    for movie in omdb.search(title):
        if movie.year[-1] == '-':
            movie.year = movie.year.replace('-','')
        if movie.year == str(year):
            return omdb.imdbid(movie.imdb_id)
        print(movie.title)
    return np.nan

def row_to_omdb(row):
    omdb = find_omdb_movie(row.title,row.year)
    time.sleep(0.2)
    try:
        row['imdb_rating'] = omdb.imdb_rating
        row['metascore'] = omdb.metascore
        row['runtime'] = omdb.runtime
        row['genre'] = omdb.genre
        row['director'] = omdb.director
        row['rating'] = omdb.rated
        row['acting_lead'] = omdb.actors.split(',')[0]
    except:
        return row
    return row

if __name__ == '__main__':
    for year in range(2010,2017):
        data = pd.concat([data,scrape_opening_weekend(year)])
    data = data.apply(lambda x: get_torrent_stats(x), axis=1)
    data['year'] = data.release_date.map(lambda x: x.year)
    data = data.apply(row_to_omdb,axis=1)

    pd.to_pickle(data,'2010-2016_alldata.pkl')