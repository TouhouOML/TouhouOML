TouhouOML
==============

Convert Touhou soundtracks from MediaWiki to machine-readable TOML data.

See write-up (in Chinese): https://thwiki.cc/%E7%94%A8%E6%88%B7Wiki:NicoNicoNii

TODO
------

1. Non-game soundtracks are not included, this is a major deficiency.
   Implementing this feature would allow Sealing Club themes to be resolved
   properly!
2. Implement another parser for English descriptions from TouhouWiki.net.
3. "category" extractor is still buggy.
4. Track soundtrack relationships using the "Work-Recording" hierarchy.
5. Musician templates are not resolved yet.
6. The code is of extremely low quality, need a full rewrite, it's the
   worst program I've ever written.
7. Trialing newline handling is inconsistent.
