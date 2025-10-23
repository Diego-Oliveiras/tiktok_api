from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
import requests, os, urllib.parse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# 🧩 Variáveis de ambiente
CLIENT_KEY = os.getenv("TT_CLIENT_KEY")
CLIENT_SECRET = os.getenv("TT_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# ============================================================
# 1️⃣ Endpoint de login — redireciona o usuário para o TikTok
# ============================================================
@app.get("/login/tiktok")
def login_tiktok():
    scope = "user.info.basic video.list"
    params = {
        "client_key": CLIENT_KEY,
        "scope": scope,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": "csrf123"
    }
    url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

# ======================================================================
# 2️⃣ Callback: TikTok redireciona pra cá com ?code=...  e ?state=...
# ======================================================================
@app.api_route("/auth/tiktok/callback", methods=["GET", "POST"])
def auth_callback(request: Request, code: str = None, state: str = None):
    if not code:
        return JSONResponse({"error": "Código de autorização ausente."}, status_code=400)

    # 🔁 Troca o code por access_token
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    data = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_resp = requests.post(token_url, headers=headers, data=data).json()

    access_token = token_resp.get("access_token")
    if not access_token:
        return JSONResponse({"error": "Falha ao obter access_token", "details": token_resp}, status_code=400)

    # 🔹 Guarda o token na sessão (aqui simplificado)
    request.session = {"access_token": access_token}

    # Redireciona para rota que lista os vídeos
    return RedirectResponse("/me/videos")

# ==========================================
# 3️⃣ Rota para listar vídeos do usuário
# ==========================================
@app.get("/me/videos")
def get_my_videos(request: Request):
    access_token = getattr(request, "session", {}).get("access_token")
    if not access_token:
        return JSONResponse({"error": "Você precisa se autenticar primeiro."}, status_code=401)

    # 🧩 1. Obter open_id
    user_info_url = "https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_resp = requests.get(user_info_url, headers=headers).json()

    user_data = user_resp.get("data", {}).get("user", {})
    open_id = user_data.get("open_id")
    if not open_id:
        return JSONResponse({"error": "Não foi possível obter open_id", "details": user_resp}, status_code=400)

    # 🧩 2. Buscar vídeos
    video_url = "https://open.tiktokapis.com/v2/video/list/"
    body = {
        "open_id": open_id,
        "cursor": 0,
        "count": 10,
        "fields": [
            "video_description", "create_time",
            "like_count", "comment_count", "share_count", "embed_link"
        ]
    }
    video_resp = requests.post(video_url, headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }, json=body).json()

    return JSONResponse(video_resp)

@app.get("/")
def read_root():
    return {"message": "Hello World"}