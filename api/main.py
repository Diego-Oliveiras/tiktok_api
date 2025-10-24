# app.py
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse,PlainTextResponse
from fastapi.responses import FileResponse

from starlette.middleware.sessions import SessionMiddleware
import requests, os, urllib.parse
from dotenv import load_dotenv

# ============================================================
# 🔧 Configuração inicial
# ============================================================
load_dotenv()

app = FastAPI()

# 🔐 Middleware de sessão
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "chave_super_secreta"),
    session_cookie="session_tiktok",
)

# 🔑 Variáveis de ambiente
CLIENT_KEY = os.getenv("TT_CLIENT_KEY")
CLIENT_SECRET = os.getenv("TT_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# ============================================================
# 1️⃣ Endpoint de login — redireciona o usuário para o TikTok
# ============================================================
@app.get("/login/tiktok")
def login_tiktok():
    scope = "user.info.basic,video.list"
    params = {
        "client_key": CLIENT_KEY,
        "scope": scope,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": "csrf123",  # em produção: gerar aleatório
    }
    url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

# =====================================================================
# 2️⃣ Callback: TikTok redireciona pra cá com ?code=...  e ?state=...
# =====================================================================
@app.get("/auth/tiktok/callback")
def auth_callback(request: Request, code: str = None, state: str = None):
    if not code:
        return JSONResponse({"error": "Código de autorização ausente."}, status_code=400)

    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    data = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    token_resp = requests.post(token_url, headers=headers, data=data).json()

    access_token = token_resp.get("access_token")
    if not access_token:
        return JSONResponse(
            {"error": "Falha ao obter access_token", "details": token_resp},
            status_code=400,
        )

    # 🔹 Salva o token na sessão
    request.session["access_token"] = access_token

    # Redireciona para rota que lista os vídeos
    return RedirectResponse("/me/videos")

# ==========================================
# 3️⃣ Rota para listar vídeos do usuário
# ==========================================
@app.get("/me/videos")
def get_my_videos(request: Request):
    access_token = request.session.get("access_token")
    if not access_token:
        return JSONResponse(
            {"error": "Você precisa se autenticar primeiro."}, status_code=401
        )

    # 🧩 1. Obter open_id
    user_info_url = "https://open.tiktokapis.com/v2/user/info/"
    headers = {"Authorization": f"Bearer {access_token}"}
    body = {"fields": ["open_id", "display_name"]}

    user_resp = requests.post(user_info_url, headers=headers, json=body).json()

    user_data = user_resp.get("data", {}).get("user", {})
    open_id = user_data.get("open_id")

    if not open_id:
        return JSONResponse(
            {"error": "Não foi possível obter open_id", "details": user_resp},
            status_code=400,
        )

    # 🧩 2. Buscar vídeos
    video_url = "https://open.tiktokapis.com/v2/video/list/"
    body = {
        "open_id": open_id,
        "cursor": 0,
        "count": 10,
        "fields": [
            "id",
            "video_description",
            "create_time",
            "like_count",
            "comment_count",
            "share_count",
            "embed_link",
        ],
    }
    video_resp = requests.post(
        video_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=body,
    ).json()

    return JSONResponse(video_resp)

# ==========================================
# 4️⃣ Raiz e Webhook (teste)
# ==========================================
@app.get("/")
def read_root():
    return {"message": "TikTok API v2 - FastAPI funcionando 🚀"}

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    return JSONResponse({"received": body})


@app.get("/tiktok-verification.html")
def serve_tiktok_verification():
    """
    Serve o conteúdo de verificação exigido pelo TikTok.
    """
    # Diretório atual (onde está o main.py)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Sobe um nível (da pasta /api para a raiz do projeto)
    root_dir = os.path.dirname(base_dir)
    
    # Caminho completo até o arquivo
    file_path = os.path.join(root_dir, "tiktokwF4NstLzn3GvEEgMtbCnpG9tPV9RAotO.txt")

    # Se o arquivo existe, retorna o conteúdo puro
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        return PlainTextResponse(content, media_type="text/plain")

    # Caso não exista
    return PlainTextResponse("Arquivo de verificação não encontrado.", status_code=404)