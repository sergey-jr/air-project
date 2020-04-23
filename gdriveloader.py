import io
import os
from collections import Counter
from datetime import datetime
import json

import chardet
import nltk
import textract
from googleapiclient.http import MediaIoBaseDownload
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer
import numpy as np

nltk.download('punkt')
nltk.download("stopwords")


def is_apt(word):
    russian_stopwords = set(stopwords.words("russian"))
    english_stopwords = set(stopwords.words("english"))
    ru_en_stopwords = russian_stopwords.union(english_stopwords)
    return word.isalpha() and word not in ru_en_stopwords


def preprocess(sent):
    prep = nltk.word_tokenize(sent.lower())
    prep = [w for w in prep if is_apt(w)]
    return prep


class GDriveFiles:
    def __init__(self, drive, client_id, logger):
        self.drive = drive
        self.path_to_save = os.path.join("drive_files", client_id)
        self.index_path = os.path.join("drive_files", client_id, "index.json")
        self.files_urls_path = os.path.join("drive_files", client_id, "docs_urls.json")
        self.terms_path = os.path.join("drive_files", client_id, "terms.json")
        self.docs_id = os.path.join("drive_files", client_id, "docs.json")
        self.logger = logger

    @property
    def index_exists(self):
        return os.path.exists(self.index_path)

    def load(self, fl=False):
        if not self.index_exists or not fl:
            self.total_start = datetime.now()
            self.logger.debug("Loading started")
            self.gdrive_get_all_files()
            self.logger.debug("Dowloading finished")
            self.retrieve_time = datetime.now()
            self.retrieve_time_diff = (self.retrieve_time - self.total_start).total_seconds()
            self.logger.debug("Building index started")
            self.build_index()
            self.logger.debug("Building index finished. Loading Finished")
            self.total_time = datetime.now()
            self.build_index_diff = (self.total_time - self.retrieve_time).total_seconds()
            self.total_time_diff = (self.total_time - self.total_start).total_seconds()

    def get_timers_load(self):
        return {"total": {"start_time": self.total_start, "end_time": self.total_time, "passed": self.total_time_diff},
                "retrieve": {"start_time": self.total_start, "end_time": self.retrieve_time,
                             "passed": self.retrieve_time_diff},
                "build_index": {"start_time": self.retrieve_time, "end_time": self.total_time,
                                "passed": self.build_index_diff}, }

    @staticmethod
    def filter_files(item):
        ext = item["name"].split(".")[-1] if "." in item["name"] else None
        allowed = ["doc", "docx", "ppt", "pptx"]
        # "pdf", "txt"
        base_condition = not item["name"].startswith("~")
        return base_condition and ext is not None and ext in allowed

    def gdrive_get_all_files(self):
        self.files = []
        files = dict()
        files_urls = dict()
        page_token = None
        query = "'me' in owners and mimeType != 'application/vnd.google-apps.folder'"
        while True:
            response = self.drive.files().list(q=query,
                                               spaces='drive',
                                               fields='nextPageToken, files(id, name, mimeType, webViewLink)',
                                               pageToken=page_token).execute()

            page_token = response.get('nextPageToken', None)

            for file in response.get('files', []):
                if self.filter_files(file):
                    # file["name"] = translate(file["name"])
                    if file["name"] not in files:
                        self.gdrive_download_file(file)
                        files[file["name"]] = 1
                        files_urls[file["name"]] = {"id": file["id"], "link": file["webViewLink"]}
                        self.files.append(file)
                    else:
                        file_duplicate = file.copy()
                        name, ext = os.path.splitext(file_duplicate["name"])
                        name, ext = name.lower(), ext.lower()
                        file_duplicate["name"] = "_".join([name, str(files[file["name"]])]) + ext
                        self.gdrive_download_file(file_duplicate)
                        files[file["name"]] += 1
                        files_urls[file_duplicate["name"]] = {"id": file["id"], "link": file["webViewLink"]}
                        self.files.append(file_duplicate)

            if page_token is None:
                break

        folder_name = "root"
        if len(self.files) == 0:
            self.logger.error("no files in folder {}".format(folder_name))
            return -1
        with open(self.files_urls_path, "w") as json_file:
            json.dump(files_urls, json_file)
        return 0

    def gdrive_download_file(self, file):
        path_to_save = self.path_to_save
        if not os.path.exists(path_to_save):
            os.makedirs(path_to_save)
        file_id, file_name = file['id'], file['name']
        file_path = os.path.join(path_to_save, file_name)
        try:
            request = self.drive.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                self.logger.debug("Download {} {}%.".format(file_name, int(status.progress() * 100)))

            with io.open(file_path, 'wb') as f:
                f.write(fh.getvalue())
        except Exception as e:
            self.logger.error(" ".join([file_name, str(e)]))

    def get_file_strings(self, path):
        texts = ''
        try:
            texts = io.open(path, 'r', ).read()
        except Exception as e:
            ext = os.path.split(path)[-1].split(".")[-1]
            try:
                texts = textract.process(path, extension=ext)
                try:
                    texts = texts.decode("utf-8", errors="ignore")
                except:
                    texts = str(texts)
            except Exception as e1:
                try:
                    with open(path, 'rb') as f:
                        texts = io.TextIOWrapper(f, encoding='cp1251').read()
                except Exception as e2:
                    self.logger.error(" ".join([path, str(e2)]))
        texts = texts.replace('\\n', ' ').replace('\\r', '').replace("\n", " ").replace("\r", "")
        return texts

    def build_index(self):
        files_data = dict()
        for file in os.scandir(self.path_to_save):
            try:
                ext = os.path.splitext(file.path)[-1].lower()
                if ext != '.json':
                    strings = self.get_file_strings(file.path)
                    if strings != '':
                        files_data[file.name] = strings
                    os.remove(file.path)
            except Exception as e:
                self.logger.error(" ".join([file.name, str(e)]))

        res = {}
        for file in files_data:
            file_data = files_data[file]
            file_index = Counter(preprocess(file_data))
            for word in file_index:
                word_freq = file_index[word]
                if word not in res:
                    res[word] = {file: word_freq}
                else:
                    # res[word][0] += word_freq
                    res[word].update({file: word_freq})

        terms = list(res.keys())
        doc_ids = {i: doc for i, doc in enumerate(files_data)}

        with open(self.index_path, "w") as json_file:
            json.dump(res, json_file)

        with open(self.terms_path, "w") as json_file:
            json.dump(dict(terms=terms), json_file)

        with open(self.docs_id, "w") as json_file:
            json.dump(doc_ids, json_file)


class GDriveIndex:
    def __init__(self, client_id):
        self.index_path = os.path.join("drive_files", client_id, "index.json")
        self.files_urls_path = os.path.join("drive_files", client_id, "docs_urls.json")
        self.terms_path = os.path.join("drive_files", client_id, "terms.json")
        self.docs_id = os.path.join("drive_files", client_id, "docs.json")

    @property
    def exists(self):
        return os.path.exists(self.index_path)

    def find(self, query):
        if self.exists:
            index = json.load(open(self.index_path))
            postings = []
            query_index = Counter(preprocess(query))
            terms = json.load(open(self.terms_path))['terms']
            for term in query_index.keys():
                if term not in index:  # ignoring absent terms
                    continue
                # extract document info only
                posting = [doc for doc in index[term]]
                postings.append(posting)
            docs = set.intersection(*map(set, postings))
            urls = json.load(open(self.files_urls_path))
            res = [[doc, urls[doc]] for doc in docs]
            return res
        else:
            return None
