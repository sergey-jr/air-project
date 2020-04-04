import io
import os
from collections import Counter
from datetime import datetime
import json

import nltk
import textract
from googleapiclient.http import MediaIoBaseDownload
from nltk.corpus import stopwords

nltk.download('punkt')
nltk.download("stopwords")


class GDriveFiles:
    def __init__(self, drive, client_id):
        self.drive = drive
        self.path_to_save = os.path.join("drive_files", client_id)
        self.index_path = os.path.join("drive_files", client_id, "index.json")
        self.files_urls_path = os.path.join("drive_files", client_id, "docs_urls.json")

    @property
    def index_exists(self):
        return os.path.exists(self.index_path)

    def load(self, fl=False):
        if not self.index_exists and not fl:
            self.total_start = datetime.now()
            self.gdrive_get_all_files()
            self.retrieve_time = datetime.now()
            self.retrieve_time_diff = (self.retrieve_time - self.total_start).total_seconds()
            self.build_index_start = datetime.now()
            self.build_index()
            self.total_time = datetime.now()
            self.build_index_diff = (self.total_time - self.build_index_start).total_seconds()
            self.total_time_diff = (self.total_time - self.total_start).total_seconds()

    def get_timers_load(self):
        return {"total": {"start_time": self.total_start, "end_time": self.total_time, "passed": self.total_time_diff},
                "retrieve": {"start_time": self.total_start, "end_time": self.retrieve_time,
                             "passed": self.retrieve_time_diff},
                "build_index": {"start_time": self.build_index_start, "end_time": self.total_time,
                                "passed": self.build_index_diff}, }

    @staticmethod
    def filter_files(item):
        ext = item["name"].split(".")[-1] if "." in item["name"] else None
        allowed = ["doc", "docx", "pdf", "txt", "ppt", "pptx"]
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
            print("no files in folder {}".format(folder_name))
            return -1
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
                print("Download {} {}%.".format(file_name, int(status.progress() * 100)))

            with io.open(file_path, 'wb') as f:
                f.write(fh.getvalue())
        except Exception as e:
            print(file_name, e)

    @staticmethod
    def get_file_strings(path):
        texts = ''
        try:
            texts = io.open(path, 'r', ).read()
        except Exception as e:
            try:
                texts = str(textract.process(path, method='tesseract'))
            except Exception as e1:
                try:
                    with open(path, 'rb') as f:
                        texts = io.TextIOWrapper(f, encoding='cp1251').read()
                except Exception as e2:
                    print(path, e2)
        texts = texts.replace('\\n', '\n').replace('\\r', '').split('\n')
        return texts

    @staticmethod
    def is_apt(word):
        russian_stopwords = set(stopwords.words("russian"))
        english_stopwords = set(stopwords.words("english"))
        ru_en_stopwords = russian_stopwords.union(english_stopwords)
        return word.isalpha() and word not in ru_en_stopwords

    def preprocess(self, file_data):
        res = []
        for row in file_data:
            prep = nltk.word_tokenize(row)
            prep = [w for w in prep if self.is_apt(w)]
            res.extend(prep)
        return res

    def build_index(self):
        files_data = dict()
        for file in os.scandir(self.path_to_save):
            ext = os.path.splitext(file.path)[-1].lower()
            if ext != '.json':
                strings = self.get_file_strings(file.path)
                if strings != '':
                    files_data[file.name] = strings
                print("Preprocess of {} is {}".format(file.name, "OK" if strings != '' else "NOT OK"))
                os.remove(file.path)

        res = {}
        for file in files_data:
            file_data = files_data[file]
            file_index = Counter(self.preprocess(file_data))
            for word in file_index:
                word_freq = file_index[word]
                if word not in res:
                    res[word] = [word_freq, (file, word_freq)]
                else:
                    res[word][0] += word_freq
                    res[word].append((file, word_freq))

        with open(self.index_path, "w") as json_file:
            json.dump(res, json_file)


class GDriveIndex:
    def __init__(self, client_id):
        self.path = os.path.join("drive_files", client_id, "index.json")
        self.urls_path = os.path.join("drive_files", client_id, "docs_urls.json")

    @property
    def exists(self):
        return os.path.exists(self.path)

    def find(self, query):
        if self.exists:
            index = json.load(open(self.path))
            postings = []
            query_prep = nltk.word_tokenize(query)
            query_index = Counter(query_prep)
            for term in query_index.keys():
                if term not in index:  # ignoring absent terms
                    continue
                posting = index[term][1:]
                # extract document info only
                posting = [i[0] for i in posting]
                postings.append(posting)
            docs = set.intersection(*map(set, postings))
            urls = json.load(open(self.urls_path))
            res = [[doc, urls[doc]] for doc in docs]
            return res
        else:
            return None
