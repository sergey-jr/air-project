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
            self.files = self.gdrive_get_all_files()
            self.retrieve_time = datetime.now()
            self.retrieve_time_diff = (self.retrieve_time - self.total_start).total_seconds()
            self.download_start = datetime.now()
            files = dict()
            files_urls = dict()
            for item in self.files:
                if item["name"] not in files:
                    self.gdrive_download_file(item)
                    files[item["name"]] = 1
                    files_urls[item["name"]] = item["webContentLink"]
                else:
                    item_ = item.copy()
                    name, ext = os.path.splitext(item_["name"])
                    name, ext = name.lower(), ext.lower()
                    item_["name"] = "_".join([name, str(files[item["name"]])]) + ext
                    self.gdrive_download_file(item_)
                    files[item["name"]] += 1
                    files_urls[item_["name"]] = item["webContentLink"]

            with open(self.files_urls_path, "w") as json_file:
                json.dump(files_urls, json_file)

            self.load_time = datetime.now()
            self.load_time_diff = (self.load_time - self.download_start).total_seconds()
            self.build_index_start = datetime.now()
            self.build_index()
            self.total_time = datetime.now()
            self.build_index_diff = (self.total_time - self.build_index_start).total_seconds()
            self.total_time_diff = (self.total_time - self.total_time).total_seconds()

    def get_timers_load(self):
        return {"total": {"start_time": self.total_start, "end_time": self.total_time, "passed": self.total_time_diff},
                "retrieve": {"start_time": self.total_start, "end_time": self.retrieve_time,
                             "passed": self.retrieve_time_diff},
                "download": {"start_time": self.download_start, "end_time": self.load_time,
                             "passed": self.load_time_diff},
                "build_index": {"start_time": self.build_index_start, "end_time": self.total_time,
                                "passed": self.build_index_diff}, }

    def filter_files(self, item):
        ext = item["name"].split(".")[-1] if "." in item["name"] else None
        allowed = ["doc", "docx", "pdf", "txt", "ppt", "pptx"]
        base_condition = all([item["ownedByMe"],
                              not os.path.exists(os.path.join(self.path_to_save, item["name"])),
                              not item["name"].startswith("~")])
        return base_condition and ext is not None and ext in allowed

    def gdrive_get_all_files(self):
        page_token = None
        content = []
        query = "'me' in owners and mimeType != 'application/vnd.google-apps.folder'"
        while True:
            response = self.drive.files().list(q=query,
                                               spaces='drive',
                                               fields='nextPageToken, files(id, name, mimeType, ownedByMe, webContentLink)',
                                               pageToken=page_token).execute()

            page_token = response.get('nextPageToken', None)

            content.extend(response.get('files', []))

            if page_token is None:
                break

        folder_name = "root"
        res = []
        if len(content) == 0:
            print("no files in folder {}".format(folder_name))
        else:
            res = list(filter(self.filter_files, content))
        return res

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
        ext = os.path.splitext(path)[-1].lower()
        # extract with textract for these data types
        if ext in ['.pdf', '.html', '.docx', '.pptx', '.doc', '.ppt']:
            try:
                texts = str(textract.process(path, encoding='utf-8')).replace('\\n', '\n').replace('\\r', '').split(
                    '\n')
            except:
                print("Couldn't extract with textract")
                return None
        # for txt data, use standard file read
        elif ext in ['.txt', '.c', '.cpp', '.cs', '.js']:
            try:
                # first detect file encoding
                with open(path, 'rb') as file:
                    rawdata = file.read()
                    result = chardet.detect(rawdata)
                    charenc = result['encoding']
                    with open(path, 'r', encoding=charenc) as file:
                        texts = file.readlines()
            except:
                print("Couldn't read text file")
                return None
        else:
            print("File format %s is not supported" % ext)
            return None

        # print(texts)
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
            strings = self.get_file_strings(file.path)
            if strings:
                files_data[file.name] = strings
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
