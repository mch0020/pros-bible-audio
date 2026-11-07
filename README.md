# Pros Bible audio

Original-language Bible readings by **Louis Tyler** (https://hebgkaudiobible.com),
used in the Pros Bible app (app.prosbible.org) with his permission.

- Releases `tyler-ot` (Hebrew Bible), `tyler-tr` (Textus Receptus NT),
  `tyler-wh` (Westcott-Hort NT): one mp3 per chapter as he recorded it,
  re-encoded mono 48 kbps. File name `<book number>-<chapter>.mp3`.
- `timings/<corpus>/<book number>.json`: for each verse id of the app,
  `[file, start seconds, end seconds, match score]`, found with the MMS
  forced aligner (`tools/align_book.py`).
