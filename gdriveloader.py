import io
import os
from datetime import datetime

from googleapiclient.http import MediaIoBaseDownload


class GDriveFiles:
    def __init__(self, drive, path_to_save, client_id):
        self.drive = drive
        self.client_id = client_id
        self.path_to_save = os.path.join(path_to_save, client_id)

    def load(self):
        self.total_start = datetime.now()
        self.files = self.gdrive_get_all_files()
        self.retrieve_time = datetime.now()
        self.retrieve_time_diff = (self.retrieve_time - self.total_start).total_seconds()
        self.download_start = datetime.now()
        for item in self.files:
            self.gdrive_download_file(item, self.path_to_save)
        self.total_time = datetime.now()
        self.load_time_diff = (self.total_time - self.download_start).total_seconds()
        self.total_time_diff = (self.total_time - self.total_time).total_seconds()

    def get_timers_load(self):
        return {"total": {"start_time": self.total_start, "end_time": self.total_time, "passed": self.total_time_diff},
                "retrieve": {"start_time": self.total_start, "end_time": self.retrieve_time,
                             "passed": self.retrieve_time_diff},
                "download": {"start_time": self.download_start, "end_time": self.total_time,
                             "passed": self.load_time_diff}}

    def gdrive_get_all_files(self):
        page_token = None
        content = []
        query = "'me' in owners and mimeType != 'application/vnd.google-apps.folder'"
        while True:
            response = self.drive.files().list(q=query,
                                               spaces='drive',
                                               fields='nextPageToken, files(id, name, mimeType, ownedByMe)',
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
            res = list(filter(lambda item: item["ownedByMe"], content))
        return res

    def gdrive_download_file(self, file, path_to_save):
        if not os.path.exists(path_to_save):
            os.makedirs(path_to_save)
        file_id, file_name = file['id'], file['name']
        file_path = os.path.join(path_to_save, file_name)
        if not os.path.exists(file_path):
            request = self.drive.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print("Download %d%%." % int(status.progress() * 100))

            with io.open(file_path, 'wb') as f:
                f.write(fh.getvalue())
