import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from requests.exceptions import RequestException

import backend.main as main


class DummyResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class TestSearchCache(unittest.TestCase):
    def test_add_and_get_and_evict(self):
        cache = main.SearchCache(capacity=2)
        self.assertEqual(cache.add("q1", "strict", False, 0, ["r1"]), ["r1"])
        self.assertEqual(cache.add("q2", "strict", False, 0, ["r2"]), ["r2"])
        self.assertIsNone(cache.get("q1", "strict", False, 0))
        self.assertEqual(cache.add("q3", "strict", False, 0, ["r3"]), ["r3"])
        self.assertEqual(cache.get("q3", "strict", False, 0), ["r3"])

    def test_get_miss(self):
        cache = main.SearchCache()
        self.assertIsNone(cache.get("missing", "strict", False, 0))


class TestBraveClient(unittest.TestCase):
    def test_make_request_rotates_keys(self):
        client = main.BraveClient(["k1", "k2"], main.BRAVE_SEARCH_API_HEADERS)
        responses = [
            DummyResponse(429, {}),
            DummyResponse(200, {"web": {"results": []}}),
        ]
        with patch("backend.main.requests.get", side_effect=responses) as mock_get:
            response = client._make_request("http://example.com", {"q": "x"})
            self.assertIs(response, responses[1])
            self.assertEqual(mock_get.call_count, 2)

    def test_make_request_exception(self):
        client = main.BraveClient(["k1"], main.BRAVE_SEARCH_API_HEADERS)
        with patch("backend.main.requests.get", side_effect=RequestException):
            self.assertIsNone(client._make_request("http://example.com", {"q": "x"}))

    def test_make_request_non_200(self):
        client = main.BraveClient(["k1"], main.BRAVE_SEARCH_API_HEADERS)
        with patch("backend.main.requests.get", return_value=DummyResponse(500, {})):
            self.assertIsNone(client._make_request("http://example.com", {"q": "x"}))

    def test_get_web_results_web(self):
        client = main.BraveClient(["k1"], main.BRAVE_SEARCH_API_HEADERS)
        response = DummyResponse(200, {"web": {"results": ["a"]}})
        with patch.object(client, "_make_request", return_value=response):
            self.assertEqual(client.get_web_results("q", "strict", False, 0), ["a"])

    def test_get_web_results_videos(self):
        client = main.BraveClient(["k1"], main.BRAVE_SEARCH_API_HEADERS)
        response = DummyResponse(200, {"results": ["v1"]})
        with patch.object(client, "_make_request", return_value=response):
            self.assertEqual(client.get_web_results("q", "strict", True, 0), ["v1"])

    def test_get_web_results_none(self):
        client = main.BraveClient(["k1"], main.BRAVE_SEARCH_API_HEADERS)
        with patch.object(client, "_make_request", return_value=None):
            self.assertIsNone(client.get_web_results("q", "strict", False, 0))

    def test_get_img_results_filters(self):
        client = main.BraveClient(["k1"], main.BRAVE_SEARCH_API_HEADERS)
        response = DummyResponse(
            200,
            {
                "results": [
                    {"url": "u1", "thumbnail": {"src": "t1"}},
                    {"url": "u2"},
                ]
            },
        )
        with patch.object(client, "_make_request", return_value=response):
            self.assertEqual(
                client.get_img_results("q", "strict"), [{"url": "u1", "img": "t1"}]
            )

    def test_get_img_results_none(self):
        client = main.BraveClient(["k1"], main.BRAVE_SEARCH_API_HEADERS)
        with patch.object(client, "_make_request", return_value=None):
            self.assertIsNone(client.get_img_results("q", "strict"))


class TestInfoboxResolver(unittest.TestCase):
    def setUp(self):
        self.resolver = main.InfoboxResolver()

    def test_solve_math_valid(self):
        result = self.resolver._solve_math("2+2")
        self.assertEqual(result["infotype"], "calc")
        self.assertEqual(result["result"], "4")

    def test_solve_math_invalid(self):
        self.assertIsNone(self.resolver._solve_math("2/0"))

    def test_get_definition(self):
        payload = {
            "en": [
                {
                    "partOfSpeech": "noun",
                    "definitions": [{"definition": "a test definition"}],
                }
            ]
        }
        with patch("backend.main.requests.get", return_value=DummyResponse(200, payload)):
            result = self.resolver._get_definition("define test")
        self.assertEqual(result["word"], "test")
        self.assertEqual(result["definition"], "a test definition")
        self.assertEqual(result["type"], "noun")
        self.assertEqual(result["infotype"], "definition")

    def test_get_definition_no_match(self):
        self.assertIsNone(self.resolver._get_definition("hello world"))

    def test_get_definition_non_200(self):
        with patch("backend.main.requests.get", return_value=DummyResponse(404, {})):
            self.assertIsNone(self.resolver._get_definition("define test"))

    def test_get_definition_request_exception(self):
        with patch("backend.main.requests.get", side_effect=RequestException):
            self.assertIsNone(self.resolver._get_definition("define test"))

    def test_get_wikipedia_summary(self):
        payload = {
            "title": "Python",
            "extract": "Summary",
            "content_urls": {"desktop": {"page": "https://example.com"}},
        }
        web_results = [{"url": "https://en.wikipedia.org/wiki/Python", "title": "Python - Wikipedia"}]
        with patch("backend.main.requests.get", return_value=DummyResponse(200, payload)):
            result = self.resolver._get_wikipedia_summary(web_results)
        self.assertEqual(result["title"], "Python")
        self.assertEqual(result["infotype"], "wikipedia")

    def test_get_wikipedia_summary_non_200(self):
        web_results = [{"url": "https://en.wikipedia.org/wiki/Python", "title": "Python - Wikipedia"}]
        with patch("backend.main.requests.get", return_value=DummyResponse(404, {})):
            self.assertIsNone(self.resolver._get_wikipedia_summary(web_results))

    def test_get_wikipedia_summary_request_exception(self):
        web_results = [{"url": "https://en.wikipedia.org/wiki/Python", "title": "Python - Wikipedia"}]
        with patch("backend.main.requests.get", side_effect=RequestException):
            self.assertIsNone(self.resolver._get_wikipedia_summary(web_results))

    def test_get_wikipedia_summary_no_wiki(self):
        web_results = [{"url": "https://example.com", "title": "Example"}]
        self.assertIsNone(self.resolver._get_wikipedia_summary(web_results))


class TestAppAndRoutes(unittest.TestCase):
    def test_create_app_debug_from_env(self):
        os.environ["NILCH_DEBUG"] = "true"
        try:
            app = main.create_app()
            self.assertTrue(app.debug)
        finally:
            os.environ.pop("NILCH_DEBUG", None)

    def test_create_app_debug_override(self):
        os.environ["NILCH_DEBUG"] = "true"
        try:
            app = main.create_app(debug=False)
            self.assertFalse(app.debug)
        finally:
            os.environ.pop("NILCH_DEBUG", None)

    def test_search_noquery(self):
        client = TestClient(main.app)
        response = client.get("/api/search")
        self.assertEqual(response.json(), "noquery")

    def test_search_cached_null_infobox(self):
        client = TestClient(main.app)
        with patch.object(main.search_cache, "get", return_value=[{"title": "t"}]):
            with patch.object(main.infobox_resolver, "get_infobox", return_value=None):
                response = client.get("/api/search", params={"q": "test"})
        data = response.json()
        self.assertEqual(data["infobox"], "null")
        self.assertEqual(data["results"], [{"title": "t"}])

    def test_search_fetch_with_infobox(self):
        client = TestClient(main.app)
        infobox = {"infotype": "calc", "equ": "1+1", "result": "2"}
        with patch.object(main.search_cache, "get", return_value=None):
            with patch.object(main.brave_client, "get_web_results", return_value=[{"title": "t"}]):
                with patch.object(main.search_cache, "add", return_value=[{"title": "t"}]):
                    with patch.object(main.infobox_resolver, "get_infobox", return_value=infobox):
                        response = client.get("/api/search", params={"q": "test"})
        data = response.json()
        self.assertEqual(data["infobox"], infobox)
        self.assertEqual(data["results"], [{"title": "t"}])

    def test_search_noresults(self):
        client = TestClient(main.app)
        with patch.object(main.search_cache, "get", return_value=None):
            with patch.object(main.brave_client, "get_web_results", return_value=None):
                response = client.get("/api/search", params={"q": "test"})
        self.assertEqual(response.json(), "noresults")

    def test_search_videos_skips_infobox(self):
        client = TestClient(main.app)
        with patch.object(main.search_cache, "get", return_value=None):
            with patch.object(main.brave_client, "get_web_results", return_value=[{"title": "v"}]):
                with patch.object(main.search_cache, "add", return_value=[{"title": "v"}]):
                    with patch.object(main.infobox_resolver, "get_infobox") as mock_infobox:
                        response = client.get("/api/search", params={"q": "test", "videos": "true"})
        data = response.json()
        self.assertEqual(data["infobox"], "null")
        self.assertEqual(data["results"], [{"title": "v"}])
        mock_infobox.assert_not_called()

    def test_images_noquery(self):
        client = TestClient(main.app)
        response = client.get("/api/images")
        self.assertEqual(response.json(), "noquery")

    def test_images_noresults(self):
        client = TestClient(main.app)
        with patch.object(main.brave_client, "get_img_results", return_value=None):
            response = client.get("/api/images", params={"q": "test"})
        self.assertEqual(response.json(), "noresults")

    def test_images_results(self):
        client = TestClient(main.app)
        results = [{"url": "u1", "img": "t1"}]
        with patch.object(main.brave_client, "get_img_results", return_value=results):
            response = client.get("/api/images", params={"q": "test"})
        self.assertEqual(response.json(), results)
