import os
import re
import curlrequests
import json
from pprint import pprint
import tomli_w
import pathlib

import thbconstant
import thbparser
import threlease


OUTPUT_DIR = "./data/ost"


def fetch_musicroom_page_list(api_endpoint):
    body = api_endpoint.get(
        action="query", list="categorymembers",
        cmlimit=50, cmtitle=thbconstant.MUSICROOM_TITLE,
        format="json"
    )
    resp = json.loads(body)
    assert "continue" not in resp.keys(), "Response is truncated!"

    return [
        i["title"] for i in resp["query"]["categorymembers"]
    ]


def fetch_game_musicroom_page(api_endpoint, pagetitle):
    body = api_endpoint.get(
        action="query", prop="revisions",
        rvprop="content", rvslots="main", titles=pagetitle,
        format="json", formatversion=2
    )
    resp = json.loads(body)
    body = resp["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
    work_json = thbparser.parse_thbwiki_musicroom(api_endpoint, body)
    #return evaluate_musicroom_wikitext(work_json)
    return work_json


if __name__ == "__main__":
    api_endpoint = curlrequests.ApiRequest(thbconstant.API_URL)

    for i in fetch_musicroom_page_list(api_endpoint):
    #for i in ["东方地灵殿/Music"]:
    #for i in ["东方灵异传/Music"]:
        print(i)
        music_list = fetch_game_musicroom_page(api_endpoint, i)
        if not music_list:
            print("Failed to obtain music information for %s!" % i)
            break
        else:
            pass
            #pprint(music_list)

        music_data_structure = {
            "soundtrack-list": music_list,
            "title": {}
        }

        game_name = i.split("/")[0]
        try:
            game_threlease = threlease.title_to_release(game_name)
            music_data_structure["threlease"] = "TH%s" % game_threlease
            music_data_structure["title"] = threlease.release_to_title(game_threlease)
            print(threlease.release_to_title(game_threlease))
            filename = "TH%s" % game_threlease
        except IndexError:
            filename = game_name
            music_data_structure["title"]["zh-hans"] = filename
            
        pprint(music_data_structure)

        path = pathlib.Path(OUTPUT_DIR) / ("%s.toml" % filename)
        with open(str(path), "wb+") as f:
            tomli_w.dump(music_data_structure, f)

        #os.system("read && clear")
    #pprint(fetch_game_musicroom_page("东方地灵殿/Music"))
    #(fetch_game_musicroom_page("东方怪绮谈/Music"))
