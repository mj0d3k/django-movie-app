import requests
import json
import time
import re
from bs4 import BeautifulSoup
from requests.exceptions import RequestException


def get_info(info_box, row_name):
    row = info_box.find('th', string=lambda t: t and row_name in t)
    if row and row.next_sibling:
        return row.next_sibling.get_text(strip=True)
    return None


def get_cast(info_box_html):
    cast_raw = re.findall(r'<th .*?>Starring</th><td .*?>(.*?)</td>', info_box_html, re.DOTALL)
    if cast_raw:
        cast_cleaned = re.sub(r'<.*?>', '.', cast_raw[0])
        cast_list = cast_cleaned.split('.')
        filtered_cast = [actor.strip() for actor in cast_list if actor.strip() and not actor.startswith("mw-parser-output") and not actor.startswith("plainlist")]
        return filtered_cast
    return []


def scrape_wikipedia_data(movie_link):
    try:
        response = requests.get(movie_link)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        info_box = soup.find('table', class_='infobox vevent')
        if not info_box:
            return {}

        info_box_html = str(info_box)

        data = {
            'director': get_info(info_box, 'Directed by'),
            'music': get_info(info_box, 'Music by'),
            'cast': get_cast(info_box_html),
            'country': get_info(info_box, 'Country'),
            'duration': get_info(info_box, 'Running time'),
            'description': ''
        }

        release_date = info_box.find('span', class_='bday')
        if release_date:
            data['release_date'] = release_date.get_text(strip=True)

        description_tag = soup.find('p', class_=False, id=False)
        if description_tag:
            data['description'] = description_tag.get_text(strip=True, separator=' ')

        return data

    except RequestException as e:
        print(f"Error fetching {movie_link}: {e}")
        return {}


with open('wikidata_films.json', 'r', encoding='utf-8') as file:
    films = json.load(file)

output_filename = 'wikidata_films_updated.json'
with open(output_filename, 'w'):
    pass

for film in films:
    if film.get('wikipedia-link'):
        updated_film = scrape_wikipedia_data(film.get('wikipedia-link', ''))
        film.update(updated_film)
        time.sleep(1)

    with open(output_filename, 'a', encoding='utf-8') as file:
        json.dump(film, file, indent=4)
        file.write('\n')

print("Zaktualizowano dane filmów.")
