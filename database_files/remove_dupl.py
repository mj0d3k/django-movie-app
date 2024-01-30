import json


def remove_duplicate_movies(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    movies_dict = {movie['title']: movie for movie in data}

    unique_movies = list(movies_dict.values())

    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(unique_movies, file, indent=2)


input_filename = 'wikidata_films_updated_DATABASE.json'
output_filename = 'no_duplicates.json'

remove_duplicate_movies(input_filename, output_filename)

print(f'Duplikaty usunięte. Wynik zapisano w pliku: {output_filename}')
