import pickle
import os.path
from pathlib import Path
from types import SimpleNamespace as Namespace
from typing import Callable, List, Optional
from tqdm.auto import tqdm
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from . import env
from .i18n import tr


class GDrive:
    auth_scopes = env.Var('CB_GDRIVE_AUTH_SCOPES',
                          help="Google Drive authentication scopes (comma-separated)",
                          optional=True, default='https://www.googleapis.com/auth/drive')
    cred_json = env.Var('CB_GDRIVE_CRED', type=Path,
                        help="Path to Google Drive service account credentials (.json)",
                        optional=False)
    root_id = env.Var('CB_GDRIVE_ROOT_ID', type=str,
                      help="File id of the Google Drive folder / drive to store files in",
                      optional=False)

    def __init__(self):
        self.credentials = Credentials.from_service_account_file(self.cred_json, scopes=self.auth_scopes.split(','))
        self.api = build('drive', 'v3', credentials=self.credentials)

    def list(self, fields: List[str] = ['id', 'name'], q: str = None) -> List[Namespace]:
        q = f"'{self.root_id}' in parents"
        q += f' and {q}' if q else ''
        resp = self.api.files().list(fields=f'files({",".join(fields)}), nextPageToken', q=q, pageSize=100).execute()
        files = resp.get('files', [])
        return [Namespace(**f) for f in files]

    def upload_file(self, src: Path, name: str, mime: str = 'application/zip', on_progress: Optional[Callable] = None) -> str:
        cur_files = self.list()
        existing_file = next((f for f in cur_files if f.name == name), None)

        media = MediaFileUpload(str(src), chunksize=1024*1024, resumable=True)
        if not existing_file:
            body = dict(
                name=name,
                parents=[self.root_id],
                mimeType=mime,
            )
            req = self.api.files().create(body=body, media_body=media,
                                          fields='id')
        else:
            body = {}
            req = self.api.files().update(body=body, media_body=media, fileId=existing_file.id,
                                          fields='id')

        on_progress = on_progress if on_progress is not None else (lambda *args, **kwargs: None)

        with tqdm(total=100, leave=False, ncols=200, unit='%', desc=tr("Upload")) as pbar:
            resp = None
            while resp is None:
                status, resp = req.next_chunk()
                if status:
                    progress = status.progress() * 100.0
                    pbar.update(progress - pbar.n)
                    on_progress(pbar)

        return resp.get('id')
