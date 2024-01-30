import requests
import json
import time


def query_wikidata(offset, limit=500):
    sparql_query = f"""
    SELECT DISTINCT ?film ?filmLabel ?wikipediaLink ?reviewScore ?rottenTomatoesID ?freebaseID WHERE {{
      ?film wdt:P31 wd:Q11424.
      OPTIONAL {{
        ?film rdfs:label ?filmLabel.
        FILTER(LANG(?filmLabel) = "en")
      }}
      OPTIONAL {{ ?film wdt:P646 ?freebaseID. }}
      OPTIONAL {{ ?film wdt:P1258 ?rottenTomatoesID. }}
      OPTIONAL {{ ?film wdt:P444 ?reviewScore. FILTER(CONTAINS(STR(?reviewScore), "%")) }}
      OPTIONAL {{
        ?article schema:about ?film;
        schema:inLanguage "en";
        schema:isPartOf <https://en.wikipedia.org/>.
        BIND(REPLACE(STR(?article), "http://", "https://") AS ?wikipediaLink)
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT {limit} OFFSET {offset}
    """
    url = "https://query.wikidata.org/sparql"
    while True:
        try:
            response = requests.get(url, params={'format': 'json', 'query': sparql_query})
            response.raise_for_status()
            data = response.json()
            return data['results']['bindings']
        except requests.exceptions.HTTPError as errh:
            print("HTTP Error:", errh)
        except requests.exceptions.ConnectionError as errc:
            print("Error Connecting:", errc)
        except requests.exceptions.Timeout as errt:
            print("Timeout Error:", errt)
        except requests.exceptions.RequestException as err:
            print("Oops: Something Else", err)
        except json.JSONDecodeError as json_err:
            print("JSON Decode Error:", json_err)
        print("Retrying in 5 seconds...")
        time.sleep(5)


def extract_film_data(film):
    title = film.get('filmLabel', {}).get('value')
    if title is None:
        return None

    empty_values_count = sum(1 for value in film.values() if not value.get('value'))
    if empty_values_count >= 2:
        return None

    wikidata_id = film.get('film', {}).get('value').split('/')[-1]

    return {
        'title': title,
        'wikidata-id': wikidata_id,
        'wikipedia-link': film.get('wikipediaLink', {}).get('value', ''),
        'review-score': film.get('reviewScore', {}).get('value', 'Unknown'),
        'rotten-tomatoes-id': film.get('rottenTomatoesID', {}).get('value', ''),
        'freebase-id': film.get('freebaseID', {}).get('value', ''),
    }


def save_data_to_file(films, json_file, is_first_entry):
    for film in films:
        extracted_data = extract_film_data(film)
        if extracted_data is None:
            continue

        if not is_first_entry:
            json_file.write(',\n')
        else:
            is_first_entry = False
        json.dump(extracted_data, json_file, indent=4)
    return is_first_entry


if __name__ == '__main__':
    with open('wikidata_films.json', 'w',  encoding='utf-8') as json_file:
        json_file.write('[')
        offset = 0
        is_first_entry = True

        while True:
            films = query_wikidata(offset)
            if not films:
                break

            is_first_entry = save_data_to_file(films, json_file, is_first_entry)

            offset += 500
            time.sleep(1)

        json_file.write(']')
        json_file.truncate()

    print("Pobrano informacje o filmach.")
