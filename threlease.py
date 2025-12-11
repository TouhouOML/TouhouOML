from functools import cache
import json
import pathlib
import curlrequests
import tomllib
import tomli_w
import zhconv


WIKIDATA_API = "https://query.wikidata.org/sparql"
DATA_PATH = "./data/threlease/threlease.toml"

ALIAS = {
    "东方文花帖DS": "Double Spoiler",
    "东方花映塚": "东方花映冢"
}


@cache
def _threlease_dict():
    with open(DATA_PATH, "rb") as f:
        threlease_dict = tomllib.load(f)
    return threlease_dict


def release_to_title(release):
    threlease_dict = _threlease_dict()
    if not isinstance(release, str):
        release = "%g" % release
    return threlease_dict[release]["title"]


def title_to_release(title):
    for k, v in ALIAS.items():
        title = title.replace(k, v)

    threlease_dict = _threlease_dict()
    for threlease in threlease_dict:
        for lang, val in threlease_dict[threlease]["title"].items():
            if title in val:
                return threlease
    raise IndexError


def fetch_threlease_data():
    query = """
        SELECT ?game ?thReleaseValue ?titleJa ?titleEn ?titleZh ?titleZhHans WHERE {
            wd:Q907907 p:P527 [
                ps:P527 ?game ;
                pq:P1545 ?thReleaseValue
            ] .
            OPTIONAL { ?game rdfs:label ?titleJa FILTER(LANG(?titleJa) = "ja") }
            OPTIONAL { ?game rdfs:label ?titleEn FILTER(LANG(?titleEn) = "en") }
            OPTIONAL { ?game rdfs:label ?titleZh FILTER(LANG(?titleZh) = "zh") }
            OPTIONAL { ?game rdfs:label ?titleZhHans FILTER(LANG(?titleZhHans) = "zh-hans") }
        }
        ORDER BY xsd:float(?thReleaseValue)
    """
    
    url = curlrequests.construct_apiurl(
        WIKIDATA_API, format="json", query=query
    )
    resp = json.loads(curlrequests.get(url))

    all_game_dict = {}
    for i in resp["results"]["bindings"]:
        game_dict = {}
        game_dict["title"] = {}

        lang_list = [
            ("titleJa", "ja"),
            ("titleEn", "en"),
            ("titleZh", "zh"),
            ("titleZhHans", "zh-hans"),
        ]
        for lang_field, lang_code in lang_list:
            if lang_field in i:
                title = i[lang_field]["value"]
                title = title.replace("_", " ")
                game_dict["title"][lang_code] = title

        if "titleZhHans" not in i and "titleZh" in i:
            game_dict["title"]["zh-hans"] = zhconv.convert(
                game_dict["title"]["zh"], locale="zh-cn"
            )

        all_game_dict[i["thReleaseValue"]["value"]] = game_dict

    path = pathlib.Path(DATA_PATH)
    with open(str(path), "wb+") as f:
        tomli_w.dump(all_game_dict, f)
               

if __name__ == "__main__":
    fetch_threlease_data()
