import pickle
import os.path
from pathlib import Path
from types import SimpleNamespace as Namespace
from typing import List
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials

class GDrive:
    auth_scopes = ['https://www.googleapis.com/auth/drive']

    def __init__(self, auth_json: Path):
        self.credentials = Credentials.from_service_account_file(auth_json, scopes=self.auth_scopes)
        self.api = build('drive', 'v3', credentials=self.credentials)

    def list(self, fields: List[str] = ['id', 'name'], q: str = None) -> List[Namespace]:
        resp = self.api.files().list(fields=f'files({",".join(fields)}), nextPageToken', q=q, pageSize=100).execute()
        files = resp.get('files', [])
        return [Namespace(**f) for f in files]
