import requests
import json
import re
from flask import Flask, jsonify, request, render_template, send_file

BRAVE_SEARCH_API_KEYS = [] # Add your keys (can have multiple)

BRAVE_SEARCH_API_HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "X-Subscription-Token": "setme" # Set later by the calling function
}

WIKIPEDIA_API_HEADERS = {
    "User-Agent": "nilch/1.0 (jake.stbu@gmail.com)"
}

recent_searches = []

# Returns results
def add_recent_search(query: str, safe_search: str, is_videos: str, page: int, results):
    recent_searches.append({
        "query": query,
        "safe": safe_search,
        "is_videos": is_videos,
        "page": page,
        "results": results
    })
    if (len(recent_searches) >= 20):
        recent_searches.pop(0)
    return results

# Returns None if not in cache, otherwise search results
def check_for_recent_search(query: str, safe_search: str, is_videos: str, page: int):
    criteria = {
        "query": query,
        "safe": safe_search,
        "is_videos": is_videos,
        "page": page
    }
    for search in recent_searches:
        match = all(
            search.get(key) == value 
            for key, value in criteria.items() 
            if key != "results"
        )
        if match:
            return search.get("results")
    return None

def make_brave_request(url, params):
    for key in BRAVE_SEARCH_API_KEYS:
        headers = BRAVE_SEARCH_API_HEADERS
        headers["X-Subscription-Token"] = key
        try:
            response = requests.get(url, headers=BRAVE_SEARCH_API_HEADERS, params=params)
            if response.status_code == 200:
                return response
        except RateLimitError:
            continue

def get_web_results(query: str, safe_search: str, is_videos: str, page: int):
    recent = check_for_recent_search(query, safe_search, is_videos, page)
    if (recent != None):
        print("returning from cache!")
        return recent
    print("original search!")
    result_type = "videos" if is_videos else "web"
    url = "https://api.search.brave.com/res/v1/" + result_type + "/search"
    params = { "q": query, "safesearch": safe_search, "count": 10, "offset": page }
    response = make_brave_request(url, params)
    if response != None and response.status_code == 200:
        if (is_videos):
            return add_recent_search(query, safe_search, is_videos, page, response.json()["results"])
        else:
            return add_recent_search(query, safe_search, is_videos, page, response.json()["web"]["results"])
    return None

def get_img_results(query: str, safe_search: str):
    url = "https://api.search.brave.com/res/v1/images/search"
    params = { "q": query, "safesearch" : safe_search }
    response = make_brave_request(url, params)
    if response != None and response.status_code == 200:
        results = response.json()["results"]
        return [{"url": result["url"], "img": result["thumbnail"]["src"]} for result in results]
    return None

def get_infobox(web_results, query):
    # Check if the user is trying to get a maths equation done
    expr_pattern = r'[+\-/*÷x()0-9.^ ]+'
    maths_patterns = [
        rf'^what is ({expr_pattern})$',
        rf'^solve ({expr_pattern})$',
        rf'^calc ({expr_pattern})$',
        rf'^calculate ({expr_pattern})$',
        rf'^({expr_pattern})$',
        rf'^({expr_pattern})=$',
    ]
    for pattern in maths_patterns:
        match = re.match(pattern, query, re.IGNORECASE)
        if match:
            equ = match.group(1).strip()
            equ = equ.replace("x", "*").replace("÷", "/").replace("^", "**")
            try:
                return {"infotype": "calc", "equ": equ, "result": str(eval(equ))}
            except Exception:
                return None
    # Check if the user is checking the definition of a word
    def_match0 = re.match(r'^what does ([a-zA-Z]+) mean$', query, re.IGNORECASE)
    def_match1 = re.match(r'^define ([a-zA-Z]+)$', query, re.IGNORECASE)
    word = None
    if (def_match0):
        word = def_match0.group(1)
    elif (def_match1):
        word = def_match1.group(1)
    if (word != None):
        # it's a definition, return Wiktionary definition
        url = "https://en.wiktionary.org/api/rest_v1/page/definition/" + word
        response = requests.get(url, headers = WIKIPEDIA_API_HEADERS)
        if response.status_code != 200:
            return None
        data = response.json()
        definition = None
        for d in data["en"][0]["definitions"]:
            if d["definition"] != "":
                definition = d["definition"]
                break
        return {"word": word,
                "type": data["en"][0]["partOfSpeech"],
                "definition": definition,
                "url": "https://en.wiktionary.org/wiki/" + word,
                "infotype": "definition"}
    # If one of the first 3 results are a wikipedia article, return the first page of the article
    for i in range(min(3, len(web_results))):
        if "wikipedia.org" in web_results[i]["url"]:
            formatted_title = web_results[i]["title"].split(" - Wikipedia")[0].replace(" ", "_")
            url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + formatted_title
            response = requests.get(url, headers=WIKIPEDIA_API_HEADERS)
            if response.status_code != 200:
                return None
            data = response.json()
            return {"title": data["title"],
                    "info": data["extract"],
                    "url": data["content_urls"]["desktop"]["page"],
                    "infotype": "wikipedia"}
    return None # No infobox

app = Flask(__name__)

@app.route("/api/search")
def results():
    query = request.args.get("q")
    safe_search = request.args.get("safe")
    videos = True if request.args.get("videos") == "true" else False
    page = request.args.get("page")
    page = page if page != None else 0
    if (query == None):
        return "noquery"
    if (safe_search == None):
        safe_search = "strict"
    results = get_web_results(query, safe_search, videos, page)
    if (results == None):
        return "noresults"
    if (not videos):
        infobox = get_infobox(results, query)
    else:
        infobox = None
    infobox = "null" if (infobox == None) else infobox
    return {
        "infobox": infobox,
        "results": results,
    }

@app.route("/api/images")
def images():
    query = request.args.get("q")
    safe_search = request.args.get("safe")
    if (query == None):
        return "noquery"
    if (safe_search == None):
        safe_search = "strict"
    results = get_img_results(query, safe_search)
    if (results == None):
        return "noresults"
    return results

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
