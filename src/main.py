from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
import bleach

app = FastAPI()
templates = Jinja2Templates(directory="templates")

comments = []

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'"
        return response

app.add_middleware(CSPMiddleware)

@app.get("/comments", response_class=HTMLResponse)
async def get_comments(request: Request):
    return templates.TemplateResponse("comments.html", {"request": request, "comments": comments})

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
