import curl
import pycurl
import json
import hashlib
import pathlib


class ApiRequest():
    ENCODING = "UTF-8"
    CACHE_DIR = "./data/cache"

    HTTP_VERSION = pycurl.CURL_HTTP_VERSION_2_0
    HTTP_HEADERS = [
        'User-Agent: Touhou Metadata Downloader, '
        'by https://thwiki.cc/User:NicoNicoNii'
    ]

    def __init__(self, api_endpoint):
        self.curl = curl.Curl()

        self.curl_params = {
            pycurl.HTTP_VERSION: self.HTTP_VERSION,
            pycurl.HTTPHEADER: self.HTTP_HEADERS,
            pycurl.URL: api_endpoint
        }
        for k, v in self.curl_params.items():
            if k == pycurl.URL:
                self.curl.set_url(v)
            else:
                self.curl.set_option(k, v)

    def _request_params_dict(self, request_kwargs, method):
        params = {}
        params["curl"] = self.curl_params.copy()
        params["request"] = {"kwargs": request_kwargs}
        params["method"] = method
        return params

    def _get_cachefile(self, request_kwargs, method):
        params = json.dumps(self._request_params_dict(request_kwargs, method))
        filename = hashlib.sha256(params.encode("UTF-8")).hexdigest()
        filepath = (pathlib.Path(self.CACHE_DIR) / filename).resolve()
        return filepath

    def _read_cache(self, request_kwargs, method):
        with open(self._get_cachefile(request_kwargs, method), "r") as file:
            resp_json = json.loads(file.read())
            return resp_json["resp"]["body"]

    def _write_cache(self, request_kwargs, method):
        with open(self._get_cachefile(request_kwargs, method), "w+") as file:
            params = self._request_params_dict(request_kwargs, method)
            params["resp"] = {
                "body": self.curl.body().decode(self.ENCODING)
            }
            file.write(json.dumps(params))

    def get(self, **kwargs):
        try:
            resp = self._read_cache(kwargs, method="get")
            return resp
        except FileNotFoundError:
            resp = self.curl.get(params=kwargs).decode(self.ENCODING)
            self._write_cache(kwargs, method="get")
            return resp

    def post(self, **kwargs):
        try:
            resp = self._read_cache(params=kwargs, method="post")
            return resp
        except FileNotFoundError:
            resp = self.curl.get(params=kwargs).decode(self.ENCODING)
            self._write_cache(kwargs, method="post")
            return resp
