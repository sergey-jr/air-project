# google-drive search
## Info
This application developed for purpose of studying. This Project for Advanced Information Retrieval. 
## Features

- building inverted index of files on user Google Drive (``ext=[.doc, .docx, .ppt, .pptx]``)
- searching through index
- deleting files by query and from search result
- authentication

## Requirements

- Python >= 3.6
- OS from Linux family (highly recommend)
- all libs from requirements.txt

## How to use
Delete next: ``export OAUTHLIB_INSECURE_TRANSPORT=1`` if have secure connection (https) for any (development or production) type of runnable.

If you want to run it as dev:
``sh development.sh``

If you want to run it as prod:
``sh prod.sh``
