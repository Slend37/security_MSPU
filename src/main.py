import shutil
from typing import Annotated
import uuid

from cryptography.fernet import InvalidToken
from pathlib import Path as FilePath
from fastapi import Depends, FastAPI, Query, Request, Form, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
import filetype
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic_settings import BaseSettings
from fastapi_csrf_protect import CsrfProtect
from fastapi.exceptions import HTTPException
from starlette import status
from typing import Any
import bleach
from dotenv import load_dotenv
import os
from cryptography.fernet import Fernet, InvalidToken


load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise RuntimeError("ENCRYPTION_KEY не задан в .env файле!")

cipher = Fernet(ENCRYPTION_KEY.encode())

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("APP_SECRET"),
    https_only=False
)

users = [
    {"username": "Admin", "role": "admin"},
    {"username": "Bob", "role": "user"},
    {"username": "Alice", "role": "user"},
    {"username": "Guest", "role": "guest"},
]

files_db = [
    {
        'id' : 1,
        'filename': 'bob_file.txt',
        'owner': 'Bob',
        'size' : 1024,
        'path' : 'storage/bob_file.txt',
        'original_name': 'bob_file.txt',
        'is_encrypted': False
    },
    {
        'id' : 2,
        'filename': 'alice_file.txt',
        'owner': 'Alice',
        'size' : 2048,
        'path' : 'storage/alice_file.txt',
        'original_name': 'alice_file.txt',
        'is_encrypted': False
    },
    {
        'id' : 3,
        'filename': 'secret_file.txt',
        'owner': 'Admin',
        'size' : 4096,
        'path' : 'storage/secret_file.txt',
        'original_name': 'secret_file.txt',
        'is_encrypted': False
    },
]

# class CsrfSettings(BaseSettings):
#     secret_key: str = os.environ.get("APP_SECRET")
#     cookie_samesite: str = "none"
#     cookie_secure: bool = True

# @CsrfProtect.load_config
# def get_csrf_config():
#     return CsrfSettings()

comments = []

# fake_db = {'money': 1000}

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'"
        return response

app.add_middleware(CSPMiddleware)

@app.post('/set-session')
def set_session(request: Request, name: str) -> Any:
    if name not in [u["username"] for u in users]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid username"
        )
    request.session['name'] = name
    return {"message": "Session set successfully"}

@app.get('/get-session')
def get_session(request: Request) -> Any:
    if "name" not in request.session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No name set in session"
        )
    name = request.session["name"]
    return {"name": name}

@app.get('/drop-session')
def drop_session(request: Request) -> Any:
    request.session.clear()
    return {"message": "Session cleared successfully"}

# @app.get('/login')
# def form(request: Request, csrf_protect: CsrfProtect = Depends()):
#     csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
#     response = templates.TemplateResponse(
#         request,
#         "form.html",
#         {"request": request, "csrf_token": csrf_token}
#     )
#     csrf_protect.set_csrf_cookie(signed_token, response)
#     return response

# @app.post('/login', response_class=JSONResponse)
# async def create_post(request: Request, csrf_protect: CsrfProtect = Depends()):
#     await csrf_protect.validate_csrf(request)
#     response: JSONResponse = JSONResponse(status_code=200, content={"detail": "OK"})
#     csrf_protect.unset_csrf_cookie(response)
#     return response

# @app.post('/transfer')
# def transfer(
#     request: Request, amount: int = Form(...), to_account: int = Form(...)
# ) -> Any:
#     user = request.session.get("user")
#     if not user:
#         return { "error": "login required"}
#     fake_db["money"] -= amount
#     return { "msg": f"Send {amount} to {to_account}"}

@app.get("/comments", response_class=HTMLResponse)
async def get_comments(request: Request):
    return templates.TemplateResponse(request, "comments.html", {"request": request, "comments": comments})

@app.post("/comments", response_class=HTMLResponse)
async def post_comments(request: Request):
    body = await request.body()
    body_str = body.decode('utf-8')

    comment = ""
    if body_str and "=" in body_str:
        comment = body_str.split("=", 1)[1]
        from urllib.parse import unquote_plus
        comment = unquote_plus(comment)

    if comment and comment.strip():
    #     allowed_tags = ['b', 'i', 'u', 'em', 'strong']
    #     cleaned = bleach.clean(comment.strip(), tags=allowed_tags, attributes={}, strip=True, strip_comments=True)
        comments.append(comment)

    return RedirectResponse(url="/comments", status_code=303)

def current_user(request: Request) -> dict | None:
    return next(
        (u for u in users if u["username"] == request.session.get("name", None)),
        None
    )

@app.get("/file/{file_id}")
def get_file_safe(
    request: Request,
    file_id: int,
    user: Annotated[dict | None, Depends(current_user)]
) -> Any:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )
    file = next((f for f in files_db if f['id'] == file_id), None)
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    if user["role"] == 'admin' or file["owner"] == user["username"]:
        return {"file" : file}
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden"
        )

@app.delete("/file/{file_id}")
def delete_file_safe(
    request: Request,
    file_id: int,
    user: Annotated[dict | None, Depends(current_user)]
) -> Any:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )
    file = next((f for f in files_db if f['id'] == file_id), None)
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    if user["role"] == 'admin' or file["owner"] == user["username"]:
        files_db.remove(file)
        return {"message": "File has been removed"}
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden"
        )

@app.get("/files/my")
def get_user_files(
    request: Request,
    user: Annotated[dict | None, Depends(current_user)]
) -> Any:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )
    my_files = []
    for f in files_db:
        if f['owner'] == user["username"]:
            my_files.append(f)
    if not my_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You do not have files"
        )
    else:
        return {"my_files" : my_files}

@app.get("/files/all")
def get_all_files(
    request: Request,
    user: Annotated[dict | None, Depends(current_user)]
) -> Any:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )

    if user['role'] == 'admin':
        return {"my_files" : files_db}
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden"
        )

file_database = []

@app.post("/files/upload")
def upload_file(
    request: Request,
    file: UploadFile,
    user: Annotated[dict | None, Depends(current_user)],
    encrypt: bool = Query(False, description="Зашифровать файл перед сохранением")
) -> Any:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )

    limit = 1024 * 1024 * 2
    if file.size and file.size > limit:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size exceeds the 2MB limit"
        )

    if not file.filename.lower().endswith((".png", ".jpeg", ".jpg", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .jpeg, .png, .jpg, .txt files are allowed"
        )

    file_data = file.file.read()

    if file.filename.lower().endswith((".png", ".jpeg", ".jpg")):
        kind = filetype.guess(file_data[:261])
        if kind is None or kind.mime not in ["image/jpeg", "image/png"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid jpeg/png file",
            )

    if encrypt:
        encrypted_data = cipher.encrypt(file_data)
        data_to_save = encrypted_data
    else:
        data_to_save = file_data

    name = uuid.uuid4()
    storage_path = f"storage/{name}"

    FilePath("storage").mkdir(exist_ok=True)

    with open(storage_path, "wb") as f:
        f.write(data_to_save)

    new_id = max([f['id'] for f in files_db], default=0) + 1
    files_db.append({
        "id": new_id,
        "filename": str(name),
        "owner": user["username"],
        "size": len(file_data),
        "path": storage_path,
        "original_name": file.filename,
        "is_encrypted": encrypt
    })

    return {"message": f"File uploaded successfully{' (encrypted)' if encrypt else ''}"}

@app.get("/files/download/{file_id}")
def download_file(
    request: Request,
    file_id: int,
    user: Annotated[dict | None, Depends(current_user)]
) -> Any:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized"
        )

    file_meta = next((f for f in files_db if f['id'] == file_id), None)
    if file_meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    if user["role"] != 'admin' and file_meta["owner"] != user["username"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden"
        )

    file_path = file_meta["path"]
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )

    with open(file_path, "rb") as f:
        file_data = f.read()
    if file_meta.get("is_encrypted", False):
        try:
            decrypted_data = cipher.decrypt(file_data)
        except InvalidToken:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to decrypt file. Encryption key may have changed."
            )
    else:
        decrypted_data = file_data

    import mimetypes
    media_type, _ = mimetypes.guess_type(file_meta["original_name"])
    if media_type is None:
        media_type = "application/octet-stream"

    return Response(
        content=decrypted_data,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{file_meta['original_name']}"
        }
    )
