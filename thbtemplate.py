import re
import json

import mwparserfromhell

import curlrequests
import thbconstant


_REGEX_REF = re.compile(r'<ref>.*?</ref>')


def extract_wikilinks(string):
    parsed_wikitext = mwparserfromhell.parse(string)
    link_list = parsed_wikitext.filter_wikilinks()
    return link_list


class MusicTitleTemplate():
    def __init__(self, wikitext):
        filtered_wikitext = _REGEX_REF.sub('', wikitext)
        parsed_wikitext = mwparserfromhell.parse(filtered_wikitext)

        # Is it a link?
        # e.g. [[{{萃梦想音乐名|1|1}}（曲目）|{{萃梦想音乐名|1|1}}]]
        link_list = parsed_wikitext.filter_wikilinks()
        if len(link_list) == 1 and str(link_list[0]) == filtered_wikitext:
            if link_list[0].text:
                # If so, only extract the display text, because the page title
                # may contain disambiguous parenthesis.
                parsed_wikitext = link_list[0].text

                self.link_page = link_list[0].title
                self.link_text = link_list[0].text
            else:
                # Otherwise it's a bare wikilink, use the title
                # (text is empty).
                parsed_wikitext = link_list[0].title

                self.link_page = link_list[0].title
                self.link_text = link_list[0].title

            if not parsed_wikitext:
                raise ValueError("Unknown wikilink input: %s" % wikitext)
        else:
            self.link_page = None

        print("parsed: ", parsed_wikitext)
        template_list = parsed_wikitext.filter_templates()
        print(template_list)
        if len(template_list) == 1 and str(template_list[0]) == parsed_wikitext:
            self.wikitext = str(template_list[0])
            self.name = str(template_list[0].name)
            if len(template_list[0].params) != 2:
                raise ValueError("Unknown template parameters: %s" % template_list)
            self.language = int(str(template_list[0].params[0]))
            self.game_track_id = int(str(template_list[0].params[1]))
        else:
            raise ValueError("Unknown wikitext input: %s" % wikitext)


class WikitextRequest():
    def __init__(self, api_endpoint):
        self.api_endpoint = api_endpoint
        self.wikitext_list = []
        self.resp_list = []
        self.map = {}

    def append(self, wikitext):
        # For now, it must be a "clean" wikitext without other
        # strings or modifiers such as wikilinks.
        if wikitext not in self.wikitext_list:
            self.wikitext_list.append(wikitext)

    def request(self, chunk_size=40):
        for i in range(0, len(self.wikitext_list), chunk_size):
            self.resp_list += self._request_chunk(
                i, min(i + chunk_size - 1, len(self.wikitext_list) - 1)
            )

    def _request_chunk(self, first, last):
        req = "|".join(self.wikitext_list[first:last + 1])
        print(req)
        print(first, last)

        body = self.api_endpoint.get(
            action="expandtemplates",
            text=req,
            prop="wikitext", format="json"
        )
        resp = json.loads(body)["expandtemplates"]["wikitext"]
        resp_list = resp.split("|")
        print(resp_list)
        print(len(resp_list))

        if len(resp_list) != last - first + 1:
            raise ValueError("Respond length doesn't match the request length")
        return resp_list

    def substitute(self, wikitext):
        for idx, val in enumerate(self.wikitext_list):
            # match substrings here in the future?
            if val == wikitext:
                return self.resp_list[idx]
        raise ValueError("Substitution for %s not found!" % wikitext)
