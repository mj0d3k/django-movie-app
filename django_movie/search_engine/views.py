from django.views import View
from django.shortcuts import render
from sklearn.feature_extraction.text import TfidfVectorizer
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from django.conf import settings
from django.http import Http404
import numpy as np
import time
import json
import os


class MovieSearchView(View):
    """
    Class designed for a movie search engine,
    provides functionality to process user queries,
    and return relevant movie results.

    Methods:
    - jaccard_similarity with kgrams;
    - correct_query;
    - calculate_tf_idf:
    - search_movies;

    Attributes:
    - WEIGHTS: A dictionary assigning weights to various movie attributes,
      influencing their importance in the TF-IDF calculation.
    """

    template_name = 'view1.html'

    WEIGHTS = {
        "title": 5,
        "cast": 3,
        "director": 3,
        "description": 2,
        "release_date": 2,
        "country": 2,
        "music": 1,
        "duration": 1,
    }

    def jaccard_similarity(self, set1, set2):
        intersection = len(set1.intersection(set2))
        union = len(set1) + len(set2) - intersection
        return intersection / union if union != 0 else 0

    def kgrams(self, term, k):
        return set(term[i:i+k] for i in range(len(term) - k + 1))

    def correct_query(self, query, movies, k=2, threshold=0.5):
        query = query.lower()
        query_kgrams = self.kgrams(query, k)

        for movie in movies:
            if query in movie.values():
                return query

        potential_corrections = []
        for movie in movies:
            for key, value in movie.items():
                if isinstance(value, str):
                    values = [value]
                elif isinstance(value, list):
                    values = value
                else:
                    continue

                for item in values:
                    item_kgrams = self.kgrams(item.lower(), k)
                    similarity = self.jaccard_similarity(query_kgrams, item_kgrams)
                    if similarity >= threshold:
                        potential_corrections.append((item, similarity))

        if potential_corrections:
            return max(potential_corrections, key=lambda x: x[1])[0]

        return query

    def calculate_tf_idf(self, movies):
        documents = []
        for movie in movies:
            document = " ".join(
                f"{key} {' '.join(str(movie[key]).split()) * self.WEIGHTS[key]}" 
                for key in self.WEIGHTS if movie[key] and self.WEIGHTS[key] > 0
            )
            documents.append(document)

        vectorizer = TfidfVectorizer(stop_words=None)
        tf_idf_matrix = vectorizer.fit_transform(documents)
        return tf_idf_matrix, vectorizer

    def search_movies(self, query, tf_idf_matrix, vectorizer, movies):
        query_transformed = vectorizer.transform([query])
        cosine_similarities = np.dot(tf_idf_matrix, query_transformed.T).toarray().ravel()
        top_indices = np.argsort(cosine_similarities)[::-1][:50]
        top_movies = [(movies[i], cosine_similarities[i]) for i in top_indices]
        return top_movies

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        user_query = request.POST.get('user_query', '').strip()
        review_score_filter = request.POST.get('review_score_filter', 0)
        number_of_results = int(request.POST.get('num_results', 50))
        try:
            review_score_filter = int(review_score_filter)
        except ValueError:
            review_score_filter = 0

        path_to_json = os.path.join(settings.BASE_DIR, 'movies.json')
        with open(path_to_json, 'r', encoding='utf-8') as json_file:
            movies = json.load(json_file)

        filtered_movies = []
        for movie in movies:
            review_score = movie.get('review_score')
            if review_score and review_score != "unknown":
                try:
                    review_score_value = int(review_score.rstrip('%'))
                    if review_score_value >= review_score_filter:
                        filtered_movies.append(movie)
                except ValueError:
                    pass

        corrected_query = self.correct_query(user_query, filtered_movies)
        tf_idf_matrix, vectorizer = self.calculate_tf_idf(filtered_movies)
        top_movies = self.search_movies(corrected_query, tf_idf_matrix, vectorizer, filtered_movies)
        top_movies = top_movies[:number_of_results]

        context = {
            'results': top_movies
        }

        return render(request, self.template_name, context)


class MovieInfoView(View):
    """
    Class responsible for presenting detailed information about a movie.
    Able to fetch and display movie-related data,
    such as clickstream information from external sources
    and movie posters from Wikipedia.

    Methods:
    - fetch_clickstream_data;
    - fetch_data_for_movie;
    - create_url;
    - create_wikipedia_link;
    - fetch_movie_poster_url;
    - load_movies_from_json;
    - get_movie_by_id;
    """

    def fetch_clickstream_data(self, movie_title):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--ignore-ssl-errors=yes')
        chrome_options.add_argument('--ignore-certificate-errors')

        with webdriver.Chrome(options=chrome_options) as driver:    
            data = self.fetch_data_for_movie(movie_title, driver)
        return data

    def fetch_data_for_movie(self, movie_title, driver):
        url = self.create_url(movie_title)
        driver.get(url)
        time.sleep(10)

        markers = driver.find_elements("xpath", "//div[contains(@class, 'sc-hHEiqL kvHQHO')]")
        if len(markers) < 2:
            return []

        split_index = markers[1].location['y']

        data_elements = driver.find_elements("xpath", "//div[@data-tag='allowRowEvents']")

        extracted_data = []
        for i in range(0, len(data_elements), 6):
            element_location = data_elements[i].location['y']
            pageview_type = 'outgoing' if element_location > split_index else 'incoming'

            source = data_elements[i].text
            views = data_elements[i + 2].text
            percentage = data_elements[i + 4].text

            if source and source not in ["other-search", "empty-search", "other-empty", "other-external", "other-internal", movie_title]:
                link = self.create_wikipedia_link(source)
                extracted_data.append({
                    "label": source,
                    "views": views,
                    "percentage": percentage,
                    "link": link,
                    "type": pageview_type
                })

        return extracted_data

    def create_url(self, movie_title):
        formatted_title = movie_title.replace(' ', '_')
        return f"https://wikinav.toolforge.org/?language=en&title={formatted_title}"

    def create_wikipedia_link(self, text):
        formatted_text = text.replace(' ', '_')
        return f"https://en.wikipedia.org/wiki/{formatted_text}"

    def fetch_movie_poster_url(self, wikipedia_url):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--ignore-ssl-errors=yes')
        chrome_options.add_argument('--ignore-certificate-errors')

        with webdriver.Chrome(options=chrome_options) as driver:
            driver.get(wikipedia_url)
            time.sleep(2)

            try:
                image_element = driver.find_element(By.XPATH, "//table[contains(@class, 'infobox')]//img")
                poster_url = image_element.get_attribute('src')

                if poster_url and poster_url.startswith("//"):
                    poster_url = "https:" + poster_url

                return poster_url
            except Exception as e:
                print("Nie znaleziono plakatu filmu.", e)
                return None

    def load_movies_from_json(self):
        path_to_json = os.path.join(settings.BASE_DIR, 'movies.json')
        with open(path_to_json, 'r', encoding='utf-8') as json_file:
            return json.load(json_file)

    def get_movie_by_id(self, movies, wikidata_id):
        for movie in movies:
            if movie.get('wikidata_id') == wikidata_id:
                return movie
        raise Http404("Film nie został znaleziony")

    def get(self, request, wikidata_id):
        movies = self.load_movies_from_json()
        movie = self.get_movie_by_id(movies, wikidata_id)
        wikipedia_url = self.create_wikipedia_link(movie['title'])
        poster_url = self.fetch_movie_poster_url(wikipedia_url)
        clickstream_data = self.fetch_clickstream_data(movie['title'])
        clickstream_json = json.dumps(clickstream_data, ensure_ascii=False)

        return render(request, 'view2.html', {
            'movie': movie,
            'clickstream_data': clickstream_data,
            'clickstream_json': clickstream_json,
            'poster_url': poster_url
        })
