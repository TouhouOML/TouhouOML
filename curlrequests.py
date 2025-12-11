import urllib.parse
import curl
import pycurl
import json
import hashlib
import pathlib

# THBWiki requires HTTP/2
HTTP_VERSION = pycurl.CURL_HTTP_VERSION_2_0

HTTP_HEADERS = [
    'User-Agent: Touhou Metadata Downloader, by https://thwiki.cc/User:NicoNicoNii'
]

CACHE_DIR = "./data/cache"


def construct_apiurl(baseurl, **kwargs):
    params = [baseurl]

    for idx, item in enumerate(kwargs.items()):
        k, v = item
        if idx == 0:
            params.append("?%s=%s" % (k, urllib.parse.quote(str(v))))
        else:
            params.append("&%s=%s" % (k, urllib.parse.quote(str(v))))
    print(params)
    return "".join(params)


def get(
    url,
    coding="UTF-8",
    headers=HTTP_HEADERS,
    http_version=HTTP_VERSION
):
    c = curl.Curl()

    c.set_option(pycurl.HTTP_VERSION, http_version)
    if headers:
        c.set_option(pycurl.HTTPHEADER, headers)

    params = {
        "url": url,
        "coding": coding,
        "headers": headers,
        "http_version": HTTP_VERSION
    }
    if not _in_cache(params):
        string = c.get(url.encode(coding)).decode(coding)
        _write_to_cache(string, params)
    else:
        string = _read_from_cache(params)
    return string


def _write_to_cache(string, kwargs):
    kwargs_json = json.dumps(kwargs)
    filename = hashlib.sha256(kwargs_json.encode("UTF-8")).hexdigest()
    filepath = str((pathlib.Path(CACHE_DIR) / filename).resolve())

    kwargs["resp"] = string
    with open(filepath, "w+") as f:
        f.write(json.dumps(kwargs))


def _in_cache(kwargs):
    kwargs_json = json.dumps(kwargs)
    filename = hashlib.sha256(kwargs_json.encode("UTF-8")).hexdigest()
    return (pathlib.Path(CACHE_DIR) / filename).exists()


def _read_from_cache(kwargs):
    kwargs_json = json.dumps(kwargs)
    filename = hashlib.sha256(kwargs_json.encode("UTF-8")).hexdigest()
    filepath = str((pathlib.Path(CACHE_DIR) / filename).resolve())

    with open(filepath, "r") as f:
        resp_json = json.loads(f.read())
        return resp_json["resp"]
