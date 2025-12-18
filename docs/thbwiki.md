# Touhou OST Finder Development Notes: Data Retrieval from THBwiki via Black Magic

One of the most useful public services provided by THBwiki is the
[Music Data API](https://thwiki.cc/%E5%B8%AE%E5%8A%A9:%E9%9F%B3%E4%B9%90%E8%B5%84%E6%96%99API),
which contains information about over 10,000 Touhou music albums.
Unfortunately, only fanworks (and their corresponding originals)
are included.

It's not possible to query information about the original soundtracks
themselves, such as the games names, levels and locations where
they appear, the associated characters, the soundtrack titles
(in English, Japanese or Simplified Chinese), or the author's
commentary.

During my development of this Touhou soundtrack finder tool,
several kinds of black magic have been discovered, which exploits
some lesser-known features within the MediaWiki API or Wikitext
syntax.

These special findings are documented here.

## Obtain All Touhou OST Title Table Mappings

To canonicalize Touhou soundtrack titles in Japanese, English and Simplified
Chinese, THBwiki uses a custom MediaWiki extension known as *Table Mapping*.
Information such as character titles, character abilities, spellcard names,
or soundtrack information are stored as key-value data structures for
centralized management. For technical details, see
[Mapping Scheme Management](https://thwiki.cc/%E5%B8%AE%E5%8A%A9:%E7%AE%A1%E7%90%86%E6%98%A0%E5%B0%84%E6%96%B9%E6%A1%88).
Therefore, it provides an excellent technical means to retrieve
all Touhou soundtrack titles programmatically.

This section introduces three different methods to obtain all mapping tables,
from the simplest method (poor performance), the average method (poor performance),
and the cursed black magic (extreme performance).

### Difficulty Easy: Table Mapping API

The Table Mapping API `action=tablemapping` is the easiest method for
retrieving the mapping tables.

#### CSRF

API <code>action=tablemapping</code> is protected from CSRF attacks. A MediaWiki
CSRF protection token must be requested before this API can be used.

```bash
$ curl 'https://thwiki.cc/api.php'
       -d "action=query"
       -d "meta=tokens"
       -d "format=json" 2>/dev/null  | jq
```

Server response:

```json
{
  "batchcomplete": "",
  "query": {
    "tokens": {
      "csrftoken": "+\\"
    }
  }
}
```

All subsequent `action=tablemapping` API requests must pass the `csrftoken`
string via the required argument `token`.

It's noteworthy that the API is available for everyone, without logging in.
Since there's no security problems for unprivileged visiters, the token
response always contains a dummy placeholder `+\`. Thus, the CSRF token is
effectively non-existent. But considering the possibility of a breaking
change of the placeholder string, it's still recommend to request this
dummy token rather than hardcoding it.

#### Using `action=tablemapping`, `maction=list`

To obtain the mapping table names of a specific cagetory, use `maction=list`.
The argument `selectcat` is optional. If unset, all mapping table names (such
as character titles, character abilities, spellcard names) are returned.
Here, we're looking for soundtrack information only, thus we need the argument
`selectcat=音乐名日文` (soundtrack names in Japanese).

Example:

```bash
$ curl -X POST --data-urlencode "action=tablemapping" \
               --data-urlencode "format=json" \
               --data-urlencode "maction=list" \
               --data-urlencode "selectcat=音乐名日文" \
               --data-urlencode "token=+\\" \
               https://thwiki.cc/api.php 2>/dev/null | jq
```

The argument `token=` is the mandatory CSRF protection token (without logging
in, `token=+\`). For security, it can be submitted using only a ``POST`` request,
not a ``GET`` request. One must also use `--data-urlencode` since it contains
special characters.

Server response:

```json
{
  "tablemapping": {
    "result": "success",
    "schemes": [
      {
        "id": 1,
        "scheme": "红魔乡音乐名/日文"
      },
      {
        "id": 3,
        "scheme": "花映塚音乐名/日文"
      },
      {
        "id": 5,
        "scheme": "莲台野夜行音乐名/日文"
      },
      {
        "id": 7,
        "scheme": "蓬莱人形音乐名/日文"
      },
      {
        "id": 9,
        "scheme": "辉针城音乐名/日文"
      },
```

It's worthnoting that it's impossible to query multiple mapping tables. As a
workaround, it's possible to query only the Japanese tables, and manually
constructing the table names for other languages by replacing the suffix `/日文`
(Japanese) to `/英文` (English) or `/中文` (Chinese).

#### Using `action=tablemapping`, `maction=browse`

After obtaining the table names, use `maction=browse` to obtain their
contents.

Example:

```bash
$ curl -X POST --data-urlencode "action=tablemapping" \
               --data-urlencode "format=json" \
               --data-urlencode "maction=browse" \
               --data-urlencode "scheme=红魔乡音乐名/日文" \
               --data-urlencode "token=+\\" \
               https://thwiki.cc/api.php 2>/dev/null | jq
```

Server response:

```json
{
  "tablemapping": {
    "result": "success",
    "scheme_data": {
      "id": "1",
      "scheme": "红魔乡音乐名/日文",
      "data": [
        {
          "index_text": "!CAT",
          "value_text": "音乐名日文"
        },
        {
          "index_text": "!DEF",
          "value_text": "缺少参数"
        },
        {
          "index_text": "!TEM",
          "value_text": "红魔乡音乐名"
        },
        {
          "index_text": "1|T",
          "value_text": "赤より紅い夢"
        },
        {
          "index_text": "2|1-1",
          "value_text": "ほおずきみたいに紅い魂"
        },
        {
          "index_text": "3|1-2",
          "value_text": "妖魔夜行"
        },
        {
          "index_text": "4|2-1",
          "value_text": "ルーネイトエルフ"
        },
        ...
        {
          "index_text": "!COR",
          "value_text": "东方红魔乡"
        },
```

A single value may have multiple corresponding keys due to numbering schemes
differences (Music Room index, game level index, album index, etc). These keys
are separated by the symbol `|`.

In addition, the `!COR` field points to the corresponding work where the
soundtracks in this table are published in. It's possible to use this field
as a link to obtain the original work and its type. This will be explained
later.

#### Performance Considerations

The greatest problem of the `action=tablemapping` is its low performance.
Since this API doesn't support requesting multiple mapping tables, it creates
a serious request amplification effect. According to `jq`'s statistics, there
are currently 73 soundtrack mapping tables on THBwiki. Since each table are
available in Japanese, Chinese, and English variants, number of requests is
amplified by a factor of 3. It means that one needs at least 219 HTTPS requests
to obtain all mapping tables.

Therefore, it's crucial to reuse the existing HTTPS connections, otherwise
hundreds of handshakes would be involved already at the TLS layer. Caching
server responses is also essential. It's recommended to request the server
once only during software initialization, without making more requests in
the future. Otherwise, hundreds of requests would make your tool an eyesore
and a target of the THBwiki sysadmins. Nobody would be able to use the API
anymore if sysadmins rage-bans it.

```bash
$ jq ".tablemapping.schemes | length" < list.json
73
```

Unfortunately, due to this performance problem, it forces developers to
practice Black Magic rather than sticking with this blessed method.

In the following sections, we'll learn two kinds of Black Magic which are
more efficient than `action=tablemapping`.

### Difficulty Normal: `expandtemplates` 

To canonicalize the formatting of various types of data, it's a policy on
THBwiki to use Soundtrack Title Templates or Character Templates. Effectively,
these templates are de-facto standard library functions or API endpoints.
However, their usage is limited to MediaWiki. Unless the client has a
full MediaWiki interpreter, database and source code (which is impossible),
it's not impossible to parse these MediaWiki templates on the client side.

To offer a solution in this situation, MediaWiki provides a handy
`expandtemplates` API, which works almost like Remote Procedure Call for our
purpose.

For Soundtrack Title Template syntax, see
[帮助:音乐名模板](https://thwiki.cc/%E5%B8%AE%E5%8A%A9:%E9%9F%B3%E4%B9%90%E5%90%8D%E6%A8%A1%E6%9D%BF).
In short, the template name is the mapping table prefix obtained via
`maction=list` (without suffixes such as `/日文`, `/中文`, `/英文`).
The first argument is the language code (non-standard, see documentation),
the second argument is a key in the mapping table.

Example:

In *東方妖々夢 - Perfect Cherry Blossom*, what the boss fight soundtrack
at the end of the Stage 5?

```bash
$ curl -X POST --data-urlencode "action=expandtemplates" \
               --data-urlencode "text={{妖妖梦音乐名|2|5-2}}" \
               --data-urlencode "prop=wikitext" \
               --data-urlencode "format=json" \
               https://thwiki.cc/api.php 2>/dev/null | jq
```

Server response:

```json
{
  "expandtemplates": {
    "wikitext": "広有射怪鳥事　～ Till When?"
  }
}
```

The `expandtemplates` API effectively transforms the Soundtrack
Title Template as a "Ask the Magic Conch Shell" service, ready
to answer any question.

Example: Query the first Music Room soundtrack of 
*東方紅魔郷 - the Embodiment of Scarlet Devil*, in Japanese,
English, and Simplified Chinese.

```bash
$ curl -X POST --data-urlencode "action=expandtemplates" \
               --data-urlencode "text={{红魔乡音乐名|2|1}},{{红魔乡音乐名|4|1}},{{红魔乡音乐名|1|1}}" \
               --data-urlencode "prop=wikitext" \
               --data-urlencode "format=json" \
               https://thwiki.cc/api.php 2>/dev/null | jq
```

Server response:

```json
{
  "expandtemplates": {
    "wikitext": "赤より紅い夢,A Dream More Scarlet than Red,比赤色更红的梦"
  }
}
```

#### Performance Considerations

* **Connection reusing and cache**: This API is open for everyone without logging
  in. To avoid abusing the THBwiki system and making your application an eyesore
  for sysadmins (which may lead to the disablement of public API, making it unusable
  for everyone), it's recommended to keep the connection context between API requests
  to reuse the existing HTTPS connection, rather than handshaking with the server
  several thousand times. The resposes should be cached into a local file or database,
  information retrieval should be limited only to the first-use initialization.

* **GET and POST requests**: ``POST`` requests are suitable only for large request sizes,
  For a short text request, it's more appropriate to use ``GET`` instead, which allows
  caching at the HTTP level (even if currently non-existent, future deployment is possible
  in principle, unlike `POST` which is usually uncached).

  ```bash
  curl 'https://thwiki.cc/api.php' -G \
      -d 'action=expandtemplates' \
      -d 'text={{红魔乡音乐名|2|1}},{{红魔乡音乐名|4|1}},{{红魔乡音乐名|1|1}}' \
      -d 'prop=wikitext' -d 'format=json' \
      2>/dev/null | jq
  ```

* **Bulk Template Expansions**: For large number of template expansions, it's better
  to batch them as a single string joined by an unambiguous separator (such as newline,
  tab, or Unicode Zero-Width Space `U+200B`), and expanding all templates simultaneously
  in a ``POST`` request. If the resultant string size exceeds the upper limit, send
  multiple batches. It's easy to obtain over 1000 of template expansions within minutes
  using this technique. The length of a `GET` query string is limited to a few thousands
  characters, while a ``POST`` request allows MiB-size requests.

Template expansion is the most flexible method of data retrieval. However, according to
the method introduced above, a client still needs to (1) obtain all mapping table names
via ``maction=list``, (2) obtain all Japanese mapping table contents to extract valid
keys, (3) construct a `wikitext` to expand the same templates in Chinese and English,
and (4) finally obtain the result by splitting the server response.

Therefore, this solution still generates at least 75 HTTP requests, with poor performance.

### Difficulty Hard: Parser Functions Template Expansion
  
In MediaWiki, in additional to ordinary templates (which are essentially HTML
generators), several built-in functions are also included, which are known as
[Parser Functions](https://www.mediawiki.org/wiki/Parser_functions). Additional
parser functions are installed as MediaWiki extensions on THBwiki, making the
wiki powerful and programmable. For details, see
[解析函数](https://thwiki.cc/%E5%B8%AE%E5%8A%A9:%E8%A7%A3%E6%9E%90%E5%87%BD%E6%95%B0).

In the following text, we'll introduce several important functions.

#### Functions `getmapname` and `getmaparray`

* `getmapname`: Obtain all mapping table names of a specific category,
   equivalent to `maction=list`.

   Example:

   ```bash
   $ wikitext='{{#getmapname:音乐名日文}}'
   $ curl -X POST --data-urlencode "action=expandtemplates" \
                  --data-urlencode "text=$wikitext" \
                  --data-urlencode "prop=wikitext" \
                  --data-urlencode "format=json" \
                  https://thwiki.cc/api.php 2>/dev/null | jq
   ```

   Server response:

   ```json
   {   
     "expandtemplates": {
       "wikitext": "红魔乡音乐名/日文\n花映塚音乐名/日文\n莲台野夜行音乐名/日文\n蓬莱人形音乐名/日文\n辉针城音乐名/日文\n风神录音乐名/日文\n..."
      }
   }
   ```

* `getmaparray`: Obtain the key-value pairs of a specific mapping table,
  equivalent to `maction=browse`.

  Example:

  ```bash
  $ wikitext='{{#getmaparray:红魔乡音乐名/日文}}'
  $ curl -X POST --data-urlencode "action=expandtemplates" \
                 --data-urlencode "text=$wikitext" \
                 --data-urlencode "prop=wikitext" \
                 --data-urlencode "format=json" \
                 https://thwiki.cc/api.php 2>/dev/null | jq
  </syntaxhighlight>
  ```

  Server response:

  ```json
  {   
    "expandtemplates": {
      "wikitext": "音乐名日文\n东方红魔乡\n缺少参数\n6\n红魔乡音乐名\n赤より紅い夢\nほおずきみたいに紅い魂\n妖魔夜行\n..."
     }
  }
  ```

#### Function `arraymap` 

What are the differences between these operations and the conventional
`action=tablemapping` API? The most important difference is the ability
of nesting Wikitext templates, allowing one to use the return value of
one function as the input of the next function, enabling powerful data
processing.

One of the most powerful functions is `arraymay`. It accepts an input
string `INPUT_EXPRESSION` and splits the string into parts according to
the `INPUT_SEPARATOR`. For each of the substring, it's assigned to a
`VARIABLE_NAME`, and is modified by applying `OUTPUT_EXPRESSION`. Finally,
all modified substrings are rejoined together according to the `OUTPUT_SEPARATOR`.

```wikitext
<syntaxhighlight lang="wikitext">
{{#arraymap:
    INPUT_EXPRESSION|
    INPUT_SEPARATOR|
    VARIABLE_NAME|
    OUTPUT_EXPRESSION|
    OUTPUT_SEPARATOR
}}
```

Therefore, it's effectively equivalent to `array.map(lambda var: do_something(var))`
in functional programming or `foreach` in procedural programming. Using this function,
it's easy to process all outputs from the previous functionsin a loop. For example,
we can first obtain all mapping tables names ``{{#getmapname:音乐名日文}}``, and for
each table names, we can further apply ``getmaparray`` to extract the soundtrack tiles,
allowing us to obtain *all* soundtrack titles in *all* mapping tables.

```bash
$ wikitext=$(cat <<'EOF'
{{#arraymap:
    {{#getmapname:音乐名日文}}|
    \n|
    tablename|
    {{#getmaparray:tablename|\n|pair}}|
    ,
}}
EOF
)

$ curl -X POST --data-urlencode "action=expandtemplates" \
               --data-urlencode "text=$wikitext" \
               --data-urlencode "prop=wikitext" \
               --data-urlencode "format=json" \
               https://thwiki.cc/api.php 2>/dev/null | jq
</syntaxhighlight>
```

Server Response:

```json
{
  "expandtemplates": {
    "wikitext": "!CAT 音乐名日文\n!COR 东方红魔乡\n!DEF 缺少参数\n!SOR 6\n!TEM 红魔乡音乐名\n1 赤より紅い夢\n1-1 ほおずきみたいに紅い魂\n1-2 妖魔夜行\n2 ほおずきみたいに紅い魂\n...!CAT 音乐名日文\n!COR 东方花映塚\n!DEF 缺少参数\n!SOR 9\n!TEM 花映塚音乐名\n1 花映塚　～ Higan Retour\n2 春色小径　～ Colorful Path\n3 オリエンタルダークフライト\n4 フラワリングナイト\n5 東方妖々夢　～ Ancient Temple\n6 狂気の瞳　～ Invisible Full Moon\n7 おてんば恋娘の冒険\n8...!CAT 音乐名日文\n!COR 莲台野夜行\n!DEF 缺少参数\n!SOR 902\n!TEM 莲台野夜行音乐名\n1 夜のデンデラ野を逝く\n2 少女秘封倶楽部\n3 東方妖々夢　～ Ancient Temple\n4 古の冥界寺\n5 幻視の夜　～ Ghostly Eyes\n6 魔術師メリー\n7 月の妖鳥、化猫の幻\n8 過去の花　～ Fairy of Flower\n9 魔法少女十字軍\n10 少女幻葬　～ Necro-Fantasy\n11 幻想の永遠祭,!CAT 音乐名日文\n!COR 蓬莱人形\n!DEF 缺少参数\n!SOR 901\n!TEM 蓬莱人形音乐名\n1 蓬莱伝説\n2 二色蓮花蝶　～ Red and White\n3 桜花之恋塚　～ Japanese Flower\n4 明治十七年の上海アリス\n5 東方怪奇談\n6 エニグマティクドール\n7 サーカスレヴァリエ\n8 人形の森\n9 Witch of Love Potion\n10 リーインカーネイション\n11 U.N.オーエンは彼女なのか？\n12 永遠の巫女\n13 空飛ぶ巫女の不思議な毎日,!CAT 音乐名日文\n!COR 东方辉针城\n...“
  }
}
```

#### Performance Considerations

As we can see, this data retrieval method is efficient by exploiting MediaWiki
templates as a general-purpose querying language, dumping the entire database.
One can obtain all soundtrack mapping tables using only 3 HTTPS requests. If
the code above is duplicated for three languages and joined in a single string, 
it's possible to simultaneously request `音乐名日文`, `音乐名英文`, and `音乐名中文`
using only a single HTTPS request.

### Difficulty Lunatic: Manually Construct JSON Strings via Parser Functions

In the tutorial above, we've utilized the MediaWiki parser functions to obtain
all fields in all mapping tables. Hovever, the API response still requires
further post-processing (such as splitting strings) before it can be made in a
form useful for applications. If mapping tables of multiple languages are requested
simultaneously, additional application logic is needed to associate these tables
together.
If we can make the MediaWiki response more structured, the application logic
would be greatly simplified.

Recall that, in the current template code, we're currently using `getmaparray` to
extract all Japanese mapping table names, and for each `tablename`, we apply
`getmaparray` to obtain all key-value pairs, one line per pair.

```wikitext
{{#arraymap:
    {{#getmapname:音乐名日文}}|
    \n|
    tablename|
    {{#getmaparray:tablename|\n|pair}}|
    ,
}}
```

#### Splitting Every Line

One can further improve this MediaWiki templates, so that we can process the
content of each mapping table, one line at a time. To make it check to check
whether the splitting is correct, we wrap each line with `<item></item>`.
The improved program is as follows:

```bash
$ wikitext=$(cat <<'EOF'
{{#arraymap:
    {{#getmapname:音乐名日文}}|
    \n|
    tablename|
    {{#arraymap:
      {{#getmaparray:tablename|\n|pair}}|
      \n|
      line |
      <item>line</item> |
      \n
    }}|
    ,
}}
EOF
)

$ curl -X POST --data-urlencode "action=expandtemplates" \
               --data-urlencode "text=$wikitext" \
               --data-urlencode "prop=wikitext" \
               --data-urlencode "format=json" \
               https://thwiki.cc/api.php 2>/dev/null | jq
```

Server Response:

```json
<syntaxhighlight lang="json">
{
  "expandtemplates": {
    "wikitext": "<item>!CAT 音乐名日文</item>\n<item>!COR 东方红魔乡</item>\n<item>!DEF 缺少参数</item>\n<item>!SOR 6</item>\n<item>!TEM 红魔乡音乐名</item>\n<item>1 赤より紅い夢</item>\n<item>1-1 ほおずきみたいに紅い魂</item>\n<item>1-2 妖魔夜行</item>\n<item>2 ほおずきみたいに紅い魂</item>\n<item>2-1 ルーネイトエルフ</item>\n<item>2-2 おてんば恋娘</item>\n<item>3 妖魔夜行</item>\n<item>3-1 上海紅茶館　～ Chinese Tea</item>\n<item>3-2 明治十七年の上海アリス</item>\n<item>4 ルーネイトエルフ</item>\n<item>4-1 ヴワル魔法図書館</item>\n<item>4-2 ラクトガール　～ 少女密室</item>\n<item>5 おてんば恋娘</item>\n<item>5-1 メイドと血の懐中時計</item>\n<item>..."
  }
}
</syntaxhighlight>
```

As we can see, the logic is correctly implemented, and every line
has been accurately splitted.

#### Splitting the Key and Value in Every Line

Furthermore, we further split every single line we've just splitted into smaller
units, as that the data can be formatted as the `key: value` format. To achieve
this objective, we can use the `pos` function to identify the position of the
first space character within the line. Subsequently, all characters before this
space is seen as the `key` substring, and all characters after this space is
seen as the `value` substring. To improve the readability of our code, we can use
the `vardefine` function to store the results of the split into temporary variables.
We also need to protect the "space" argument using `<nowiki> </nowiki>`, otherwise
the parser would delete all leading and trailing spaces.

```wikitext
{{#vardefine:key_value_boundary | {{#pos:line|<nowiki> </nowiki>}}}}
{{#vardefine:rawkey | {{#sub:line|0|{{#var:key_value_boundary}}}}}}
{{#vardefine:rawvalue | {{#sub:line|{{#var:key_value_boundary}}}}}}

{{#var:rawkey}}: {{#var:rawvalue}}
```

Strictly speaking, tthe position of `rawvalue` is not given as
`{{#sub:line|{{#var:key_value_boundary}}}}`, but as ``{{#sub:line|{{#var:key_value_boundary + 1}}}}``.
However, since it's cumbersome to do arithmetic in MediaWiki templates,
we tolerate this error since leading and trailing spaces are deleted by
the parser anyway.

The complete code is as follows:

```bash
$ wikitext=$(cat <<'EOF'
{{#arraymap:
    {{#getmapname:音乐名日文}}|
    \n|
    tablename|
    {{#arraymap:
      {{#getmaparray:tablename|\n|pair}}|
      \n|
      line |
      {{#vardefine:key_value_boundary | {{#pos:line|<nowiki> </nowiki>}}}}
      {{#vardefine:rawkey | {{#sub:line|0|{{#var:key_value_boundary}}}}}}
      {{#vardefine:rawvalue | {{#sub:line|{{#var:key_value_boundary}}}}}}
      {{#var:rawkey}}: {{#var:rawvalue}} |
      \n
    }}|
    ,
}}
EOF
)

$ curl -X POST --data-urlencode "action=expandtemplates" \
               --data-urlencode "text=$wikitext" \
               --data-urlencode "prop=wikitext" \
               --data-urlencode "format=json" \
               https://thwiki.cc/api.php 2>/dev/null | jq
</syntaxhighlight>
```

Server Response:

```json
{
  "expandtemplates": {
    "wikitext": "!CAT: 音乐名日文\n!COR: 东方红魔乡\n!DEF: 缺少参数\n!SOR: 6\n!TEM: 红魔乡音乐名\n1: 赤より紅い夢\n1-1: ほおずきみたいに紅い魂\n1-2: 妖魔夜行\n2: ほおずきみたいに紅い魂\n2-1: ルーネイトエルフ\n2-2: おてんば恋娘\n3: 妖魔夜行\n3-1: 上海紅茶館　～ Chinese Tea\n3-2: 明治十七年の上海アリス\n4: ルーネイトエルフ\n4-1: ヴワル魔法図書館\n4-2: ラクトガール　～ 少女密室\n5: おてんば恋娘\n5-1: メイドと血の懐中時計\n5-2: 月時計　～ ルナ・ダイアル\n..."
  }
}
```

#### Construct JSON Key-Value Format

Now our key-value format is already machine-friendly, only slight
adjustments are needed to the output format.

##### Escaping Quotes

We wrap all `key` and `value` with quotes. To prevent the situation
where the strings already contains quotes by themselves, we can
the `replace` function to rewrite all `"` to `\"`.

```wikitext
{{#vardefine:key_value_boundary | {{#pos:line|<nowiki> </nowiki>}}}}
{{#vardefine:rawkey | {{#sub:line|0|{{#var:key_value_boundary}}}}}}
{{#vardefine:rawvalue | {{#sub:line|{{#var:key_value_boundary}}}}}}
{{#vardefine:key | {{#replace:{{#var:rawkey}}|"|\"}}}}
{{#vardefine:value | {{#replace:{{#var:rawvalue}}|"|\"}}}}

"{{#var:key}}": "{{#var:value}}"
```

##### Adding Square Brackets and Parentheses

Next, in the outer loop (loop variable `tablename`), we insert the following
characters to wrap the inner `key: value` string:

```json
[
    {
        "tablename", {
            inner string
        }
    }
]
```

In other words:

```wikitext
[
  {{#arraymap:
    {{#getmapname:音乐名日文}}|
    \n|
    tablename|
    {
    "tablename": {
      {{#arraymap:
        {{#getmaparray:tablename|\n|pair}}|
        \n|
        line |
        .... |
        ,
      }}
      }
      }|
      ,
  }}
]
```

##### Our First Successful JSON output

The full code is as follows:

```bash
$ wikitext=$(cat <<'EOF'
[
  {{#arraymap:
    {{#getmapname:音乐名日文}}|
    \n|
    tablename|
    {
    "tablename": {
      {{#arraymap:
        {{#getmaparray:tablename|\n|pair}}|
        \n|
        line |
        {{#vardefine:key_value_boundary | {{#pos:line|<nowiki> </nowiki>}}}}
        {{#vardefine:rawkey | {{#sub:line|0|{{#var:key_value_boundary}}}}}}
        {{#vardefine:rawvalue | {{#sub:line|{{#var:key_value_boundary}}}}}}
        {{#vardefine:key | {{#replace:{{#var:rawkey}}|"|\"}}}}
        {{#vardefine:value | {{#replace:{{#var:rawvalue}}|"|\"}}}}
        "{{#var:key}}": "{{#var:value}}" |
        ,
      }}
      }
      }|
      ,
  }}
]
EOF
)

$ curl -X POST --data-urlencode "action=expandtemplates" \
               --data-urlencode "text=$wikitext" \
               --data-urlencode "prop=wikitext" \
               --data-urlencode "format=json" \
               https://thwiki.cc/api.php 2>/dev/null | jq
```

Server Response:

```json
{
  "expandtemplates": {
    "wikitext": "[\n  {\n    \"红魔乡音乐名/日文\": {\n      \"!CAT\": \"音乐名日文\",\"!COR\": \"东方红魔乡\",\"!DEF\": \"缺少参数\",\"!SOR\": \"6\",\"!TEM\": \"红魔乡音乐名\",\"1\": \"赤より紅い夢\",\"1-1\": \"ほおずきみたいに紅い魂\",\"1-2\": \"妖魔夜行\",\"2\": \"ほおずきみたいに紅い魂\",\"2-1\": \"ルーネイトエルフ\",\"2-2\": \"おてんば恋娘\",\"3\": \"妖魔夜行\",\"3-1\": \"上海紅茶館　～ Chinese Tea\",\"3-2\": \"明治十七年の上海アリス\",\"4\": \"ルーネイトエルフ\",\"4-1\": \"ヴワル魔法図書館\",\"4-2\": \"ラクトガール　～ 少女密室\",\"5\": \"おてんば恋娘\",\"5-1\": \"メイドと血の懐中時計\",\"5-2\": \"月時計　～ ルナ・ダイアル\",\"6\": \"上海紅茶館　～ Chinese Tea\",\"6-1\": \"ツェペシュの幼き末裔\",\"6-2\": \"亡き王女の為のセプテット\",\"7\": \"明治十七年の上海アリス\",\"7-1\": \"魔法少女達の百年祭\",\"7-2\": \"U.N.オーエンは彼女なのか？\",\"8\": \"ヴワル魔法図書館\",\"9\": \"ラクトガール　～ 少女密室\",\"10\": \"メイドと血の懐中時計\",\"11\": \"月時計　～ ルナ・ダイアル\",\"12\": \"ツェペシュの幼き末裔\",\"13\": \"亡き王女の為のセプテット\",\"14\": \"魔法少女達の百年祭\",\"15\": \"U.N.オーエンは彼女なのか？\",\"16\": \"紅より儚い永遠\",\"17\": \"紅楼　～ Eastern Dream...\",\"E\": \"紅より儚い永遠\",\"S\": \"紅楼　～ Eastern Dream...\",\"T\": \"赤より紅い夢\"\n      }\n      },............\n]"
  }
}
```

We've successfully constructed our output as a standard-compliant JSON string.
Because the JSON output is encapsulated in the outer JSON data structure, we
need to extract the inner string and parse the string as a JSON again. This
can be done using the `fromjson` filter of `jq`:

```bash
$ curl -X POST --data-urlencode "action=expandtemplates" \
               --data-urlencode "text=$wikitext" \
               --data-urlencode "prop=wikitext" \
               --data-urlencode "format=json" \
               https://thwiki.cc/api.php 2>/dev/null | jq ".expandtemplates.wikitext | fromjson"
```

Server Response:

```json
[
  {
    "红魔乡音乐名/日文": {
      "!CAT": "音乐名日文",
      "!COR": "东方红魔乡",
      "!DEF": "缺少参数",
      "!SOR": "6",
      "!TEM": "红魔乡音乐名",
      "1": "赤より紅い夢",
      "1-1": "ほおずきみたいに紅い魂",
      "1-2": "妖魔夜行",
      "2": "ほおずきみたいに紅い魂",
      "2-1": "ルーネイトエルフ",
      "2-2": "おてんば恋娘",
      ...
    }
  },
  {
    "花映塚音乐名/日文": {
      "!CAT": "音乐名日文",
      "!COR": "东方花映塚",
      "!DEF": "缺少参数",
      "!SOR": "9",
      "!TEM": "花映塚音乐名",
      "1": "花映塚　～ Higan Retour",
      "2": "春色小径　～ Colorful Path",
      "3": "オリエンタルダークフライト",
      "4": "フラワリングナイト",
      "5": "東方妖々夢　～ Ancient Temple",
      ...
    }
  },
  ...
}
```

##### Constructing Multi-Language JSON

Right now we've successfully exploited the functional programming
language known as the MediaWiki template to construct a JSON string
for all Japanese soundtrack titles. Next, we'll generalize our result
to multiple languages.

To implement this feature, we can use the `explode` function to extract
the suffix of the template (without the language prefix). Three strings
can then be manually constructed for the Japanese, Chinese and English
versions of the mapping tables.

```wikitext
{{#vardefine:table_basename | {{#explode:tablename|/|0}}}}
{{#vardefine:tablename_ja | {{#var:table_basename}}/日文}}
{{#vardefine:tablename_en | {{#var:table_basename}}/英文}}
{{#vardefine:tablename_zh_hans | {{#var:table_basename}}/中文}}
```

Next, we insert more curly brackets to our templates so that
the output string follows the following format.

```json
[
    {
        "table_basename", {
            "ja": {  },
            "en": {  },
            "zh-hans": {  },
        }
    }
]
```

In other words,

```wikitext
[
  {{#arraymap:
    {{#getmapname:音乐名日文}}|
    \n|
    tablename|
    {{#vardefine:table_basename | {{#explode:tablename|/|0}}}}
    {{#vardefine:tablename_ja | {{#var:table_basename}}/日文}}
    {{#vardefine:tablename_en | {{#var:table_basename}}/英文}}
    {{#vardefine:tablename_zh_hans | {{#var:table_basename}}/中文}}
    {
    "{{#var:table_basename}}": {
      "ja": {
        {{#arraymap:
          {{#getmaparray:{{#var:tablename_ja}}|\n|pair}}|
          \n|
          line |
          .... |
          ,
        }}
      },
      "en": {
        {{#arraymap:
          {{#getmaparray:{{#var:tablename_en}}|\n|pair}}|
          \n|
          line |
          .... |
          ,
        }}
      },
      "zh-hans": {
        {{#arraymap:
          {{#getmaparray:{{#var:tablename_zh_hans}}|\n|pair}}|
          \n|
          line |
          .... |
          ,
        }}
      }
    }
    }|
    ,
  }}
]
```

Finally, we copy-paste the key-value extraction logic of the inner
loop three times.

```bash
$ wikitext=$(cat <<'EOF'
[
  {{#arraymap:
    {{#getmapname:音乐名日文}}|
    \n|
    tablename|
    {{#vardefine:table_basename | {{#explode:tablename|/|0}}}}
    {{#vardefine:tablename_ja | {{#var:table_basename}}/日文}}
    {{#vardefine:tablename_en | {{#var:table_basename}}/英文}}
    {{#vardefine:tablename_zh_hans | {{#var:table_basename}}/中文}}
    {
    "{{#var:table_basename}}": {
      "ja": {
        {{#arraymap:
          {{#getmaparray:{{#var:tablename_ja}}|\n|pair}}|
          \n|
          line |
          {{#vardefine:key_value_boundary | {{#pos:line|<nowiki> </nowiki>}}}}
          {{#vardefine:rawkey | {{#sub:line|0|{{#var:key_value_boundary}}}}}}
          {{#vardefine:rawvalue | {{#sub:line|{{#var:key_value_boundary}}}}}}
          {{#vardefine:key | {{#replace:{{#var:rawkey}}|"|\"}}}}
          {{#vardefine:value | {{#replace:{{#var:rawvalue}}|"|\"}}}}
          "{{#var:key}}": "{{#var:value}}" |
          ,
        }}
      },
      "en": {
        {{#arraymap:
          {{#getmaparray:{{#var:tablename_en}}|\n|pair}}|
          \n|
          line |
          {{#vardefine:key_value_boundary | {{#pos:line|<nowiki> </nowiki>}}}}
          {{#vardefine:rawkey | {{#sub:line|0|{{#var:key_value_boundary}}}}}}
          {{#vardefine:rawvalue | {{#sub:line|{{#var:key_value_boundary}}}}}}
          {{#vardefine:key | {{#replace:{{#var:rawkey}}|"|\"}}}}
          {{#vardefine:value | {{#replace:{{#var:rawvalue}}|"|\"}}}}
          "{{#var:key}}": "{{#var:value}}" |
          ,
        }}
      },
      "zh-hans": {
        {{#arraymap:
          {{#getmaparray:{{#var:tablename_zh_hans}}|\n|pair}}|
          \n|
          line |
          {{#vardefine:key_value_boundary | {{#pos:line|<nowiki> </nowiki>}}}}
          {{#vardefine:rawkey | {{#sub:line|0|{{#var:key_value_boundary}}}}}}
          {{#vardefine:rawvalue | {{#sub:line|{{#var:key_value_boundary}}}}}}
          {{#vardefine:key | {{#replace:{{#var:rawkey}}|"|\"}}}}
          {{#vardefine:value | {{#replace:{{#var:rawvalue}}|"|\"}}}}
          "{{#var:key}}": "{{#var:value}}" |
          ,
        }}
      }
    }
    }|
    ,
  }}
]
EOF
)
```

##### Final Result

Example (`bash` variable definition from the last section is required):

```bash
$ curl -X POST --data-urlencode "action=expandtemplates" \
               --data-urlencode "text=$wikitext" \
               --data-urlencode "prop=wikitext" \
               --data-urlencode "format=json" \
               https://thwiki.cc/api.php 2>/dev/null | jq ".expandtemplates.wikitext | fromjson"
```

Server Response:

```json
[
  {
    "红魔乡音乐名": {
      "ja": {
        "!CAT": "音乐名日文",
        "!COR": "东方红魔乡",
        "!DEF": "缺少参数",
        "!SOR": "6",
        "!TEM": "红魔乡音乐名",
        "1": "赤より紅い夢",
        "1-1": "ほおずきみたいに紅い魂",
        "1-2": "妖魔夜行",
        ...
      },
      "en": {
        "!CAT": "音乐名英文",
        "!DEF": "缺少参数",
        "!TEM": "红魔乡音乐名",
        "1": "A Dream More Scarlet than Red",
        "1-1": "A Soul as Scarlet as a Ground Cherry",
        "1-2": "Apparitions Stalk the Night",
        ...
      },
      "zh-hans": {
        "!CAT": "音乐名中文",
        "!DEF": "缺少参数",
        "!TEM": "红魔乡音乐名",
        "1": "比赤色更红的梦",
        "1-1": "如鬼灯般的红色之魂",
        "1-2": "妖魔夜行",
        ...
      }
    }
  },
  {
    "花映塚音乐名": {
      "ja": {
        "!CAT": "音乐名日文",
        "!COR": "东方花映塚",
        "!DEF": "缺少参数",
        "!SOR": "9",
        "!TEM": "花映塚音乐名",
        "1": "花映塚　～ Higan Retour",
        "2": "春色小径　～ Colorful Path",
        "3": "オリエンタルダークフライト",
        ...
      },
      "en": {
        "!CAT": "音乐名英文",
        "!DEF": "缺少参数",
        "!TEM": "花映塚音乐名",
        "1": "Flower Reflecting Mound ~ Higan Retour",
        "2": "Spring Lane ~ Colorful Path",
        "3": "Oriental Dark Flight",
        ...
      },
      "zh-hans": {
        "!CAT": "音乐名中文",
        "!DEF": "缺少参数",
        "!TEM": "花映塚音乐名",
        "1": "花映塚　～ Higan Retour",
        "2": "春色小径　～ Colorful Path",
        "3": "Oriental Dark Flight",
        ...
      }
    }
  },
  {
    "莲台野夜行音乐名": {
      "ja": {
        "!CAT": "音乐名日文",
        "!COR": "莲台野夜行",
        "!DEF": "缺少参数",
        "!SOR": "902",
        "!TEM": "莲台野夜行音乐名",
        "1": "夜のデンデラ野を逝く",
        "2": "少女秘封倶楽部",
        "3": "東方妖々夢　～ Ancient Temple",
        ...
      },
      "en": {
        "!CAT": "音乐名英文",
        "!DEF": "缺少参数",
        "!TEM": "莲台野夜行音乐名",
        "1": "Passing on Through the Dendera Fields in the Night",
        "2": "Girls' Sealing Club",
        "3": "Eastern Ghostly Dream ~ Ancient Temple",
        ...
      },
      "zh-hans": {
        "!CAT": "音乐名中文",
        "!DEF": "缺少参数",
        "!TEM": "莲台野夜行音乐名",
        "1": "走在夜晚的莲台野",
        "2": "少女秘封俱乐部",
        "3": "东方妖妖梦　～ Ancient Temple",
        ...
      }
    }
  },
  {
    "蓬莱人形音乐名": {
      "ja": {
        "!CAT": "音乐名日文",
        "!COR": "蓬莱人形",
        "!DEF": "缺少参数",
        "!SOR": "901",
        "!TEM": "蓬莱人形音乐名",
        "1": "蓬莱伝説",
        "2": "二色蓮花蝶　～ Red and White",
        "3": "桜花之恋塚　～ Japanese Flower",
        ...
      },
      "en": {
        "!CAT": "音乐名英文",
        "!DEF": "缺少参数",
        "!TEM": "蓬莱人形音乐名",
        "1": "Legend of Hourai",
        "2": "Dichromatic Lotus Butterfly ~ Red and White",
        "3": "Lovely Mound of Cherry Blossoms ~ Japanese Flower",
        ...
      },
      "zh-hans": {
        "!CAT": "音乐名中文",
        "!DEF": "缺少参数",
        "!TEM": "蓬莱人形音乐名",
        "1": "蓬莱传说",
        "2": "二色莲花蝶　～ Red and White",
        "3": "樱花之恋塚　～ Japanese Flower",
        ...
      }
    }
  },
  ...
]
```

It's super effective!
