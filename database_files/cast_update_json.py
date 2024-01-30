import json

with open('no_duplicates.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

filtered_data = [movie for movie in data if all(key in movie for key in ['title', 'wikidata-id', 'wikipedia-link', 'review-score', 'rotten-tomatoes-id', 'freebase-id', 'director', 'music', 'cast', 'country', 'duration', 'description', 'release_date'])]

for movie in filtered_data:
    movie['cast'] = ', '.join(movie['cast'])

with open('DATABASE.json', 'w', encoding='utf-8') as file:
    json.dump(filtered_data, file, ensure_ascii=False, indent=2)
