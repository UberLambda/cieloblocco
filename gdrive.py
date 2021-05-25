import pickle
import os.path
from pathlib import Path
from types import SimpleNamespace as Namespace
from typing import List
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from . import env


class GDrive:
    auth_scopes = env.Var('CB_GDRIVE_AUTH_SCOPES',
                          help="Google Drive authentication scopes (comma-separated)",
                          optional=True, default='https://www.googleapis.com/auth/drive')
    cred_json = env.Var('CB_GDRIVE_CRED', type=Path,
                        help="Path to Google Drive service account credentials (.json)",
                        optional=False)
    root_id = env.Var('CB_GDRIVE_ROOT_ID', type=Path,
                      help="File id of the Google Drive folder / drive to store files in",
                      optional=False)

    def __init__(self):
        self.credentials = Credentials.from_service_account_file(self.cred_json, scopes=self.auth_scopes.split(','))
        self.api = build('drive', 'v3', credentials=self.credentials)

    def list(self, fields: List[str] = ['id', 'name'], q: str = None) -> List[Namespace]:
        q = f"'{self.root_id}' in parents and" + q
        resp = self.api.files().list(fields=f'files({",".join(fields)}), nextPageToken', q=q, pageSize=100).execute()
        files = resp.get('files', [])
        return [Namespace(**f) for f in files]
