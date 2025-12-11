import re
import thbtemplate
import mwparserfromhell


def thbwiki_musicroom_splittracks(lines, keyword="category"):
    started = False

    for line in lines:
        if not started and line.startswith(keyword):
            item_buffer = [line]
            started = True
        elif started and (line.startswith("==") or line.startswith("xx")):
            yield "\n".join(item_buffer)
            started = False
            item_buffer = []
        elif started and (line.startswith(keyword)):
            yield "\n".join(item_buffer)
            item_buffer = [line]
        elif started:
            item_buffer.append(line)
        else:
            pass


def thbwiki_musicroom_splitkeys(lines):
    KEYS = [
        "category", "titleJA", "titleja", "titleZH", "titlezh", "composer", "source", "mp3", "ja", "zh"
    ]

    item_buffer = None
    for line in lines:
        if any(line.startswith(key) for key in KEYS):
            if item_buffer:
                yield "\n".join(item_buffer)
            item_buffer = [line]
        else:
            item_buffer.append(line)

    if item_buffer:
        yield "\n".join(item_buffer)


def thbwiki_musicroom_kv(entry_list):
    retval = []

    for entry in entry_list:
        if "=" in entry.split("\n")[0]:
            retval.append([
                entry[:entry.index("=")].strip(),
                entry[entry.index("=") + 1:].strip()
            ])
            #retval.append([i.strip() for i in entry.split("=")])
        elif "\n" in entry:
            retval.append([i.strip() for i in entry.split("\n")])
    return retval


def thbwiki_per_track_commentary(entry_list):
    has_source_key = False

    for entry in entry_list:
        key, *args = entry
        if key == "source":
            has_source_key = True

        if has_source_key and (key == "ja" or key == "zh"):
            return True
    return False


def thbwiki_extract_common_commentary(entry_list):
    retval = {}
    retval["commentary"] = {}

    for entry in entry_list:
        key, *args = entry
        if key == "ja":
            retval["commentary"]["ja"] = "\n".join(args)
        elif key == "zh":
            retval["commentary"]["zh-hans"] = "\n".join(args)
    return retval


def thbwiki_extract_per_track_commentary(entry_list):
    commentary = {}

    source = ["wav"]
    for entry in entry_list:
        key, *args = entry

        if key == "source":
            assert(len(args) == 1)
            source.append(args[0])

        if source[-1] not in commentary:
            commentary[source[-1]] = {}

        if key == "ja":
            commentary[source[-1]]["ja"] = "\n".join(args)
        elif key == "zh":
            commentary[source[-1]]["zh-hans"] = "\n".join(args)

    retval = {}
    retval["commentary"] = {}
    retval["source"] = {}

    REGEX_REF = re.compile(r'<ref>.*?</ref>')

    for k, v in commentary.items():
        is_filename = "." in k or '\\' in k

        if is_filename:
            k = k.replace("，", ",")
            k = REGEX_REF.sub("", k)
            for filename in k.split(","):
                format = thbwiki_filename_to_format(filename)
                if format not in retval["source"]:
                    retval["source"][format] = {"file-list": [], "file_metadata": {}}

                retval["source"][format]["file-list"].append(filename.strip())

                retval["source"][format]["file_metadata"]["ja"] = v["ja"]
                retval["source"][format]["file_metadata"]["zh-hans"] = v["zh-hans"]
        else:
            if "ja" in v:
                retval["commentary"]["ja"] = v["ja"]
            if "zh-hans" in v:
                retval["commentary"]["zh-hans"] = v["zh-hans"]

    return retval


def thbwiki_filename_to_format(name):
    if ".m2" in name.lower():
        return "fm26"
    elif ".m26" in name.lower():
        return "fm26"
    elif ".m86" in name.lower():
        return "fm86"
    elif ".mmd" in name.lower():
        return "midi"
    elif ".mid" in name.lower():
        return "midi"
    elif "music\\" in name.lower():
        return "data"
    elif ".dat" in name.lower():
        return "data"
    elif "_music.txt" in name.lower():
        return "data"
    elif ".m" in name.lower():
        return "fm86"
    else:
        assert False, "unknown format in filename %s!" % name


def thbwiki_kv_to_json(entry_list):
    retval = {
        "title": {}, "context": {}, "composer": {},
        "extra": {
            "thbwiki": {
                "category": {}
            }
        }
    }

    for entry in entry_list:
        key, *args = entry

        if key == "category":
            retval["extra"]["thbwiki"]["category"]["zh-hans"] = args
        elif key.lower() == "titleja":
            assert len(args) == 1
            if "{{" in args[0] or "}}" in args[0]:
                template = thbtemplate.MusicTitleTemplate(args[0])
                retval["extra"]["thbwiki"]["title-template"] = [
                    template.name, template.game_track_id
                ]
                if template.link_page:
                    retval["extra"]["thbwiki"]["linked-page"] = {
                        "text": str(template.link_text),
                        "page": str(template.link_page)
                    }
                if template.language != 2:
                    raise ValueError(
                        "Unknown template language code: %s" % template.language
                    )
            elif "[[" in args[0] or "]]" in args[0]:
                retval["title"]["ja"] = args[0].replace("[[", "").replace("]]", "")
            else:
                retval["title"]["ja"] = args[0]
        elif key.lower() == "titlezh":
            assert len(args) == 1
            if "{{" in args[0] or "}}" in args[0]:
                template = thbtemplate.MusicTitleTemplate(args[0])
                if template.link_page:
                    retval["extra"]["thbwiki"]["linked-page"] = {
                        "text": str(template.link_text),
                        "page": str(template.link_page)
                    }
                    
                retval["extra"]["thbwiki"]["title-template"] = [
                    template.name, template.game_track_id
                ]
                if template.language != 1:
                    raise ValueError(
                        "Unknown template language code: %s" % template.language
                    )
            elif "[[" in args[0] or "]]" in args[0]:
                retval["title"]["zh-hans"] = args[0].replace("[[", "").replace("]]", "")
            else:
                retval["title"]["zh-hans"] = args[0]
        elif key == "composer":
            retval["composer"]["ja"] = "\n".join(args)

    if thbwiki_per_track_commentary(entry_list):
        commentary = thbwiki_extract_per_track_commentary(entry_list)
    else:
        commentary = thbwiki_extract_common_commentary(entry_list)

    return {**retval, **commentary}


def thbwiki_evaluate_title_wikitext(track_parsed_list):
    LANG_ZH = 1
    LANG_JA = 2
    LANG_EN = 4

    request = thbtemplate.WikitextRequest()

    for track in track_parsed_list:
        if "title-template" in track["extra"]["thbwiki"]:
            name, track_id = track["extra"]["thbwiki"]["title-template"]
            request.append("{{%s|%s|%s}}" % (name, LANG_ZH, track_id))
            request.append("{{%s|%s|%s}}" % (name, LANG_JA, track_id))
            request.append("{{%s|%s|%s}}" % (name, LANG_EN, track_id))

        if "linked-page" in track["extra"]["thbwiki"] and "{{" in track["extra"]["thbwiki"]["linked-page"]["page"]:
            request.append(track["extra"]["thbwiki"]["linked-page"]["page"])
            request.append(track["extra"]["thbwiki"]["linked-page"]["text"])

    request.request()
    for track in track_parsed_list:
        if "title-template" in track["extra"]["thbwiki"]:
            name, track_id = track["extra"]["thbwiki"]["title-template"]
            title_zh = request.substitute("{{%s|%s|%s}}" % (name, LANG_ZH, track_id))
            title_ja = request.substitute("{{%s|%s|%s}}" % (name, LANG_JA, track_id))
            title_en = request.substitute("{{%s|%s|%s}}" % (name, LANG_EN, track_id))

            track["title"]["ja"] = title_ja
            track["title"]["zh-hans"] = title_zh
            track["title"]["en"] = title_en

        if "linked-page" in track["extra"]["thbwiki"] and "{{" in track["extra"]["thbwiki"]["linked-page"]["page"]:
            track["extra"]["thbwiki"]["linked-page"]["page"] = (
                request.substitute(track["extra"]["thbwiki"]["linked-page"]["page"])
            )
            track["extra"]["thbwiki"]["linked-page"]["text"] = (
                request.substitute(track["extra"]["thbwiki"]["linked-page"]["text"])
            )


def thbwiki_parse_category(category_string):
    character_list = []
    location_list = []
    ambiguous_list = []

    category_string = category_string.replace(" ", "\n")
    category_string = category_string.replace("路线", "路线\n")
    #category_string = category_string.replace("剧情模式", "剧情模式\n")
    category_list = category_string.split("\n")

    location_indicators = [
        "面", "boss", "场景", "对话曲", "对话用曲", "ending", "角色选择画面"
    ]
    character_indicators = [
        "角色", "路线", "过场曲"
    ]

    for i in category_list:
        target_list = ambiguous_list

        for indicator in location_indicators:
            if indicator in i.lower():
                target_list = location_list

        for indicator in character_indicators:
            if indicator in i.lower():
                target_list = character_list

        target_list.append(i)

    print("cl", character_list, "ll", location_list, "al", ambiguous_list)

    for i in ambiguous_list:
        if character_list:
            location_list.append(i)
        elif location_list:
            character_list.append(i)
        else:
            if "[[" in i and "]]" in i:
                character_list.append(i)
            else:
                location_list.append(i)

    character_list_output = []
    location_list_output = []

    for list_in, list_out in [
        (character_list, character_list_output),
        (location_list, location_list_output)
    ]:
        for idx, val in enumerate(list_in):
            parsed_wikitext = mwparserfromhell.parse(val)
            link_list = parsed_wikitext.filter_wikilinks()
            if link_list:
                for link in link_list:
                    list_out.append(str(link.title))
            else:
                list_out.append(val)

    return {
        "character-list": {"zh-hans": character_list_output},
        "scenario-list": {"zh-hans": location_list_output}
    }
            

def thbwiki_evaluate_category_wikitext(track_parsed_list):
    request = thbtemplate.WikitextRequest()

    for track in track_parsed_list:
        context = thbwiki_parse_category(
            "\n".join(track["extra"]["thbwiki"]["category"]["zh-hans"])
        )

        track["context"] = context

        for list_type in ["character-list", "scenario-list"]:
            for idx, val in enumerate(track["context"][list_type]["zh-hans"]):
                parsed_wikitext = mwparserfromhell.parse(val)
                template_list = parsed_wikitext.filter_templates()
                for template in template_list:
                    print("templated character/location: ", template)
                    request.append(str(template))

    request.request()

    for track in track_parsed_list:
        context = thbwiki_parse_category(
            "\n".join(track["extra"]["thbwiki"]["category"]["zh-hans"])
        )

        track["context"] = context

        for list_type in ["character-list", "scenario-list"]:
            for idx, val in enumerate(track["context"][list_type]["zh-hans"]):
                parsed_wikitext = mwparserfromhell.parse(val)
                template_list = parsed_wikitext.filter_templates()
                for template in template_list:
                    track["context"][list_type]["zh-hans"][idx] = request.substitute(str(template))


def thbwiki_evaluate_source_wikitext(track_parsed_list):
    request = thbtemplate.WikitextRequest()

    for track in track_parsed_list:
        if "source" not in track:
            continue
        source = track["source"]

        for format, dic in source.items():
            for lang, text in dic["file_metadata"].items():
                if "{{" in text and "}}" in text:
                    request.append(text)
    request.request(chunk_size=1)

    for track in track_parsed_list:
        if "source" not in track:
            continue
        source = track["source"]

        for format, dic in source.items():
            for lang, text in dic["file_metadata"].items():
                if "{{" in text and "}}" in text:
                    dic["file_metadata"][lang] = request.substitute(text)


def parse_thbwiki_musicroom(text):
    track_list = list(thbwiki_musicroom_splittracks(text.split("\n")))

    track_parsed_list = []
    for track in track_list:
        entry_list = list(thbwiki_musicroom_splitkeys(track.split("\n")))
        kv = thbwiki_musicroom_kv(entry_list)
        json = thbwiki_kv_to_json(kv)
        #pprint(kv)
        #pprint(thbwiki_kv_to_json(kv))
        track_parsed_list.append(json)

    thbwiki_evaluate_title_wikitext(track_parsed_list)
    thbwiki_evaluate_category_wikitext(track_parsed_list)
    thbwiki_evaluate_source_wikitext(track_parsed_list)
    return track_parsed_list
