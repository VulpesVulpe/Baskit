import asyncio
import aiohttp
import logging
from aiogram import Bot, Dispatcher, types, executor
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timedelta
import time
import statistics
import requests
import re
from aiogram.utils.markdown import hbold, hlink
import json
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()

bot = Bot(token=os.getenv('TOKEN_BOT'), parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())


async def get_match_info(date):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 YaBrowser/23.1.5.708 Yowser/2.5 Safari/537.36"
    }
    base_url = f'https://www.goaloo18.com/ajax/BasketballAjax?type=4&date={date}&timezone=6&kind=1&t=1680188738000'
    async with aiohttp.ClientSession() as session:
        async with session.get(url=base_url, headers=headers, timeout=200) as resp:
            if resp.status == 200:
                result_data = []
                soup = BeautifulSoup(await resp.text(), 'lxml')
                h = soup.find_all('h')
                print("Погнали")
                for game in h:
                    data_game = str(game).split('^')
                    dicti = {i: item for i, item in enumerate(data_game)}
                    match_id = dicti[0][15:]
                    home_name = dicti[8]
                    home_name_li = re.sub(r'\((.*?)\)', '', home_name)
                    home_name_lin = re.sub(r'\[(.*?)\]', '', home_name_li)
                    home_name_link = home_name_lin.lower().replace(" ", "-").replace("''", "").replace("'", "")
                    home_id = dicti[7]
                    away_name = dicti[10]
                    away_name_li = re.sub(r'\((.*?)\)', '', away_name)
                    away_name_lin = re.sub(r'\[(.*?)\]', '', away_name_li)
                    away_name_link = away_name_lin.lower().replace(" ", "-").replace("''", "").replace("'", "")
                    away_id = dicti[9]
                    match_name = f'{home_name} vs. {away_name}'
                    match_dates = datetime.strptime(dicti[4], '%Y,%m-%w,%d,%H,%M,%S') + timedelta(hours=6)
                    match_date = datetime.strftime(match_dates, '%d.%m %H:%M')
                    league_name = dicti[1]
                    league_name_link = dicti[33].lower().replace(" ", "-").replace("''", "").replace("'", "")
                    match_link = f'https://www.goaloo18.com/basketball/{league_name_link}-{home_name_link}-vs-' \
                                 f'{away_name_link}/analysis-{match_id}'
                    try:
                        response_match = requests.get(url=match_link, headers=headers, timeout=100)
                    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                        print('Connection error: ', e)
                        time.sleep(60)
                        continue
                    match_soup = BeautifulSoup(response_match.text, 'html.parser')
                    match_h2h = match_soup.find('table', {'id': 'table_v3'})
                    result_h2h = []
                    try:
                        a = match_h2h.find_all('tr')[2:]
                        for b in a:
                            try:
                                date_h2h_before = b.find_all('td')[1].find('span')['data-t']
                                date_h2h_after = datetime.strptime(date_h2h_before, '%Y-%m-%d %H:%M:%S')
                                date_2022 = datetime.strptime('2022-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
                                if date_h2h_after >= date_2022:
                                    date_h2h = datetime.strftime(date_h2h_after, '%d.%m.%Y')
                                    hom = b.find_all('td')[2].text
                                    awa = b.find_all('td')[5].text
                                    che = b.find_all('td')[3].text
                                    h2h_match = date_h2h + ' ' + hom + ' ' + 'vs.' + ' ' + awa + ' ' + che
                                    result_h2h.append(h2h_match)
                            except IndexError:
                                continue
                        res_h2h = '\n'.join(result_h2h)
                    except AttributeError:
                        continue
                    match_odd_link = f'https://www.goaloo18.com/basketball/{league_name}-{home_name}-vs-' \
                                     f'{away_name}/oddscomp-{match_id}'
                    try:
                        response_od = requests.get(url=match_odd_link, headers=headers, timeout=100)
                    except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                        print('Connection error: ', e)
                        time.sleep(60)
                        continue
                    odd_soup = BeautifulSoup(response_od.text, 'html.parser')
                    try:
                        odds = odd_soup.find_all('table', {'class': 'odds-table-bg'})[0]
                        odd = odds.find_all('tr')[1:]
                    except (AttributeError, IndexError):
                        continue
                    b_values = []
                    c_values = []
                    for a in odd:
                        b = None
                        if a.find_all('td')[5].find('span'):
                            b = a.find_all('td')[5].find('span').text
                        else:
                            b = a.find_all('td')[5].text
                        if b:
                            b_values.append(float(b))
                        else:
                            continue
                    if b_values:
                        average_b = statistics.mean(b_values)
                        sr_total_book = round(average_b, 1)
                    else:
                        sr_total_book = "NO"
                    for a in odd:
                        c = None
                        if a.find_all('td')[2].find('span'):
                            c = a.find_all('td')[2].find('span').find('script').text.strip()[27:-2]
                        elif a.find_all('td')[2].find('script'):
                            c = a.find_all('td')[2].find('script').text.strip()[27:-2]
                        else:
                            c = a.find_all('td')[2].text
                        if c:
                            c_values.append(float(c))
                        else:
                            continue
                    if c_values:
                        average_c = statistics.mean(c_values)
                        sr_handi_book = -round(average_c, 1)
                    else:
                        sr_handi_book = "NO"
                    page_range_h = range(1, 4)
                    page_range_a = range(1, 4)
                    games_h = 0
                    total_h = 0
                    total_handi_h = 0
                    games_a = 0
                    total_a = 0
                    total_handi_a = 0
                    for page in page_range_h:
                        home_link = f'https://basketball.goaloo18.com/ajax/TeamScheAjax?TeamID={home_id}&pageNo=' \
                                    f'{page}&flesh=0.5990759112233115'
                        try:
                            response_home = requests.get(url=home_link, headers=headers, timeout=100)
                        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                            print('Connection error: ', e)
                            time.sleep(60)
                            continue
                        home_soup = BeautifulSoup(response_home.text, 'lxml')
                        try:
                            bnm = home_soup.find('p').text
                        except AttributeError:
                            continue
                        try:
                            lis_bnm = eval(bnm[47:-3])
                        except SyntaxError:
                            lis_bnm = eval(bnm[46:-3])
                        for e in lis_bnm:
                            try:
                                dicth = {i: item for i, item in enumerate(e)}
                                date_match_home = datetime.strptime(dicth[3], '%Y/%m/%d %H:%M') + timedelta(hours=6)
                                delta = match_dates - timedelta(days=90)
                                league_hoz = dicth[10]
                                if match_dates > date_match_home >= delta and league_hoz == league_name:
                                    total_home = sum(map(int, dicth[6].replace("-", " ").split()))
                                    total_h += total_home
                                    games_h += 1
                                    shet_home = list(map(int, dicth[6].replace("-", " ").split()))
                                    try:
                                        res_hoz = shet_home[0]
                                        res_gues = shet_home[1]
                                    except IndexError:
                                        continue
                                    if res_hoz > res_gues:
                                        if dicth[4] == int(home_id):
                                            handi_h = res_gues - res_hoz
                                        else:
                                            handi_h = res_hoz - res_gues
                                    else:
                                        if dicth[4] == int(home_id):
                                            handi_h = res_gues - res_hoz
                                        else:
                                            handi_h = res_hoz - res_gues
                                    total_handi_h += handi_h
                            except (TypeError, ValueError, IndexError, KeyError):
                                continue
                    sr_home = games_h
                    try:
                        sr_total_home = round((total_h / games_h), 1)
                        sr_handi_home = round((total_handi_h / games_h), 1)
                    except ZeroDivisionError:
                        sr_total_home = 0
                        sr_handi_home = 0
                    for page in page_range_a:
                        away_link = f'https://basketball.goaloo18.com/ajax/TeamScheAjax?TeamID={away_id}&pageNo=' \
                                    f'{page}&flesh=0.5990759112233115'
                        try:
                            response_away = requests.get(url=away_link, headers=headers, timeout=100)
                        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                            print('Connection error: ', e)
                            time.sleep(60)
                            continue
                        home_soup = BeautifulSoup(response_away.text, 'lxml')
                        try:
                            bna = home_soup.find('p').text
                        except AttributeError:
                            continue
                        try:
                            lis_bna = eval(bna[47:-3])
                        except SyntaxError:
                            lis_bna = eval(bna[46:-3])
                        for e in lis_bna:
                            try:
                                dicta = {i: item for i, item in enumerate(e)}
                                date_match_away = datetime.strptime(dicta[3], '%Y/%m/%d %H:%M') + timedelta(hours=6)
                                delta = match_dates - timedelta(days=90)
                                league_awa = dicta[10]
                                if match_dates > date_match_away >= delta and league_awa == league_name:
                                    total_away = sum(map(int, dicta[6].replace("-", " ").split()))
                                    total_a += total_away
                                    games_a += 1
                                    shet_away = list(map(int, dicta[6].replace("-", " ").split()))
                                    try:
                                        res_hoz = shet_away[0]
                                        res_gues = shet_away[1]
                                    except IndexError:
                                        continue
                                    if res_hoz > res_gues:
                                        if dicta[4] == int(away_id):
                                            handi_a = res_gues - res_hoz
                                        else:
                                            handi_a = res_hoz - res_gues
                                    else:
                                        if dicta[4] == int(away_id):
                                            handi_a = res_gues - res_hoz
                                        else:
                                            handi_a = res_hoz - res_gues
                                    total_handi_a += handi_a
                            except (TypeError, ValueError, IndexError, KeyError):
                                continue
                    sr_away = games_a
                    try:
                        sr_total_away = round((total_a / games_a), 1)
                        sr_handi_away = round((total_handi_a / games_a), 1)
                    except ZeroDivisionError:
                        sr_total_away = 0
                        sr_handi_away = 0
                    sr_total = round(((sr_total_home + sr_total_away) / 2), 1)
                    sr_handi = round((sr_handi_home - sr_handi_away), 1)
                    if sr_total_book == 'NO':
                        dif_total = "NO"
                    else:
                        dif_total = abs(round((float(sr_total_book) - sr_total), 1))
                    if sr_handi_book == 'NO':
                        dif_handi = "NO"
                    else:
                        dif_handi = abs(round((float(sr_handi_book) - sr_handi), 1))

                    result_data.append(
                        {
                            'match_name': match_name,
                            'match_link': match_link,
                            'match_date': match_date,
                            'sr_home': sr_home,
                            'sr_away': sr_away,
                            'sr_total': sr_total,
                            'sr_total_book': sr_total_book,
                            'dif_total': dif_total,
                            'sr_handi': sr_handi,
                            'sr_handi_book': sr_handi_book,
                            'dif_handi': dif_handi,
                            'res_h2h': res_h2h,
                            'sr_total_home': round(sr_total_home),
                            'sr_total_away': round(sr_total_away)
                        }
                    )
                    #print(match_date)
                    #print(match_name)
                    with open("all_matches.json", "w", encoding="utf-8") as file:
                        json.dump(result_data, file, indent=4, ensure_ascii=False)
                return result_data
            else:
                logging.error(f"Failed to fetch data from {base_url}. Status code: {resp.status}")
                return None, None, None


@dp.message_handler(commands=['start'], state='*')
async def start_handler(message: types.Message):
    start_button = KeyboardButton('/start')
    reply_markup = ReplyKeyboardMarkup(resize_keyboard=True)
    reply_markup.add(start_button)
    keyboard = types.InlineKeyboardMarkup()
    dates = []
    today = datetime.today()
    for i in range(7):
        date = today + timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))
        keyboard.add(types.InlineKeyboardButton(text=date.strftime('%d.%m'),
                                                callback_data=f"date_{date.strftime('%Y-%m-%d')}"))
    await message.answer("Доступные даты:", reply_markup=keyboard)
    await message.answer("Нажмите на интересующую дату", reply_markup=reply_markup)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('date_'))
async def process_callback_date(callback_query: types.CallbackQuery):
    date = callback_query.data.split('_')[1]
    selected_date_obj = datetime.strptime(date, '%Y-%m-%d')
    formatted_date = selected_date_obj.strftime("%d.%m")
    await bot.answer_callback_query(callback_query.id, text=f"Собираю на {formatted_date}\n")
    await bot.send_message(callback_query.from_user.id, text=f"Вы выбрали дату {formatted_date}\nИдёт сбор данных...")
    await get_match_info(date)
    with open("all_matches.json") as file:
        data = json.load(file)
    for item in data:
        card = f"{hbold('Match: ')} {hlink(item.get('match_name'), item.get('match_link'))}\n" \
               f"{hbold('Data: ')} {item.get('match_date')}\n" \
               f"{hbold('Based on the last: ')} {item.get('sr_home')} and {item.get('sr_away')} games\n" \
               f"{hbold('Expected total: ')} {item.get('sr_total')}\n" \
               f"{hbold('Bookmaker total: ')} {item.get('sr_total_book')}\n" \
               f"{hbold('Different total: ')} {item.get('dif_total')}\n" \
               f"{hbold('Expected handicap: ')} {item.get('sr_handi')}\n" \
               f"{hbold('Bookmaker handicap: ')} {item.get('sr_handi_book')}\n" \
               f"{hbold('Different handicap: ')} {item.get('dif_handi')}\n" \
               f"{hbold('Expected_account: ')} {item.get('sr_total_home')}:{item.get('sr_total_away')}\n" \
               f"{hbold('H2H: ')}\n" \
               f"{item.get('res_h2h')}\n"
        try:
            await asyncio.sleep(1)
            await bot.send_message(chat_id=callback_query.from_user.id, text=card)
        except asyncio.TimeoutError:
            await asyncio.sleep(1)
            await bot.send_message(chat_id=callback_query.from_user.id, text=card)


if __name__ == '__main__':
    while True:
        try:
            updates = bot.get_updates(timeout=5200)
            executor.start_polling(dp, skip_updates=True, timeout=6000)
        except (TimeoutError, ConnectionError, ConnectionResetError):
            time.sleep(10)
            continue

