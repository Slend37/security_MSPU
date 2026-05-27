import shutil
from typing import Annotated
import uuid

from fastapi import Depends, FastAPI, Request, Form, Response, UploadFile
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

load_dotenv()

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
        'original_name': 'bob_file.txt'
    },
    {
        'id' : 2,
        'filename': 'alice_file.txt',
        'owner': 'Alice',
        'size' : 2048,
        'path' : 'storage/alice_file.txt',
        'original_name': 'alice_file.txt'
    },
    {
        'id' : 3,
        'filename': 'secret_file.txt',
        'owner': 'Admin',
        'size' : 4096,
        'path' : 'storage/secret_file.txt',
        'original_name': 'secret_file.txt'
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
    user: Annotated[dict | None, Depends(current_user)]
) -> Any:
    file_back = file
    limit = 1024 * 1024 * 2
    if file.size > limit:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File size exceeds the 2MB limit"
        )

    cur_size = file.size
    # chunk_size = 1024
    name = uuid.uuid4()
    # with open(f"storage/{name}", "wb") as f:
    #     while True:
    #         chunk = file.file.read(chunk_size)
    #         if not chunk:
    #             break
    #         cur_size += len(chunk)
    #         if cur_size > limit:
    #             os.remove(f"storage/{name}")
    #             raise HTTPException(
    #                 status_code=status.HTTP_413_CONTENT_TOO_LARGE,
    #                 detail="File size exceeds the 2MB limit",
    #             )
    #         f.write(chunk)

    if not file.filename.lower().endswith(".png") and not file.filename.lower().endswith(".jpeg"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .jpeg and .png files are allowed"
        )
    head = file.file.read()
    kind = filetype.guess(head)
    print(head)
    print(kind)
    if kind is None or kind.mime not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid jpeg/png image",
        )

    with open(f"storage/{name}", "wb") as f:
        f.write(head)
    files_db.append(
        {"id": len(files_db) + 1, "filename": name, "owner": user["username"], "size": cur_size, "path": f"storage/{name}", 'original_name': f"{file.filename}"}
    )
    print(files_db)
    return {"message": "File uploaded successfully"}

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

    file = next((f for f in files_db if f['id'] == file_id), None)
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    if user["role"] == 'admin' or file["owner"] == user["username"]:
        file_path = str(file["path"])
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk"
            )

        return FileResponse(
            path=file["path"],
            filename=file["original_name"],
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{file['original_name']}"
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden"
        )
