from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import pandas as pd
import unicodedata
from datetime import datetime
import os

app = FastAPI()

# =========================
# SESSÃO (CORRIGIDO)
# =========================

app.add_middleware(
    SessionMiddleware,
    secret_key="almox-secreto-123"
)

# =========================
# USUÁRIOS
# =========================

usuarios = {
    "admin": {"senha": "123", "tipo": "admin"},
    "A01": {"senha": "123", "tipo": "setor"},
    "A02": {"senha": "123", "tipo": "setor"},
    "A03": {"senha": "123", "tipo": "setor"},
    "A04": {"senha": "123", "tipo": "setor"},
    "A05": {"senha": "123", "tipo": "setor"},
    "A06": {"senha": "123", "tipo": "setor"},
    "A07": {"senha": "123", "tipo": "setor"},
    "A08": {"senha": "123", "tipo": "setor"},
    "BANHEIRO CENTRAL": {"senha": "123", "tipo": "setor"},
}

requisicoes = []
ARQ = "requisicoes.xlsx"

# =========================
# CARREGAR EXCEL
# =========================

if os.path.exists(ARQ):
    try:
        requisicoes = pd.read_excel(ARQ).to_dict("records")
    except:
        requisicoes = []

def salvar():
    pd.DataFrame(requisicoes).to_excel(ARQ, index=False)

# =========================
# UTIL
# =========================

def normalizar(txt):
    if not isinstance(txt, str):
        return str(txt)
    txt = txt.strip().upper()
    return unicodedata.normalize("NFKD", txt).encode("ASCII", "ignore").decode("ASCII")

def carregar_excel():
    df = pd.read_excel("materiais.xlsx")
    df.columns = [normalizar(c) for c in df.columns]
    return df

def pegar_colunas(df):
    col_codigo = [c for c in df.columns if "COD" in c][0]
    col_desc = [c for c in df.columns if "DESC" in c][0]
    return col_codigo, col_desc

# =========================
# LOGIN
# =========================

@app.get("/", response_class=HTMLResponse)
def login():
    return """
    <html>
    <body style="font-family:Arial; padding:20px;">
        <h2>🔐 Login</h2>

        <form method="post" action="/login">
            <input name="usuario" placeholder="Usuário" style="width:100%; padding:8px;">
            <br><br>
            <input name="senha" type="password" placeholder="Senha" style="width:100%; padding:8px;">
            <br><br>
            <button style="width:100%; padding:10px; background:#111; color:white;">Entrar</button>
        </form>
    </body>
    </html>
    """

@app.post("/login")
def login_post(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    if usuario in usuarios and usuarios[usuario]["senha"] == senha:
        request.session["user"] = usuario

        if usuarios[usuario]["tipo"] == "admin":
            return RedirectResponse("/painel", status_code=303)
        else:
            return RedirectResponse("/materiais", status_code=303)

    return RedirectResponse("/", status_code=303)

# =========================
# MATERIAIS
# =========================

@app.get("/materiais", response_class=HTMLResponse)
def materiais(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/")

    df = carregar_excel()
    tabela = df.to_html(index=False)

    return f"""
    <html>
    <body style="font-family:Arial; padding:20px;">
        <h2>📦 Materiais</h2>

        <a href="/requisicao">Nova Requisição</a> |
        <a href="/minhas">📄 Minhas Requisições</a> |
        <a href="/logout">Sair</a>

        <br><br>

        {tabela}
    </body>
    </html>
    """

# =========================
# REQUISIÇÃO
# =========================

@app.get("/requisicao", response_class=HTMLResponse)
def req(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/")

    df = carregar_excel()
    cod, desc = pegar_colunas(df)

    options = ""
    for _, r in df.iterrows():
        options += f'<option value="{r[cod]}">{r[desc]}</option>'

    return f"""
    <html>
    <body style="font-family:Arial; padding:20px;">
        <h2>🧾 Nova Requisição</h2>

        <form method="post" action="/enviar">
            <select name="codigo">{options}</select>
            <br><br>
            <input type="number" name="quantidade" required>
            <br><br>
            <button>Enviar</button>
        </form>

        <br>
        <a href="/materiais">Voltar</a>
    </body>
    </html>
    """

# =========================
# ENVIAR
# =========================

@app.post("/enviar")
def enviar(request: Request, codigo: str = Form(...), quantidade: int = Form(...)):
    df = carregar_excel()
    cod, desc = pegar_colunas(df)

    df[cod] = df[cod].astype(str).str.strip().str.upper()
    codigo = codigo.strip().upper()

    item = df[df[cod] == codigo]

    if item.empty:
        return HTMLResponse("Não encontrado")

    item = item.iloc[0]

    requisicoes.append({
        "id": len(requisicoes) + 1,
        "user": request.session.get("user"),
        "codigo": codigo,
        "descricao": item[desc],
        "quantidade": quantidade,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "status": "PENDENTE"
    })

    salvar()
    return RedirectResponse("/materiais", status_code=303)

# =========================
# MINHAS
# =========================

@app.get("/minhas", response_class=HTMLResponse)
def minhas(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/")

    html = """
    <html>
    <body style="font-family:Arial; background:#f4f6f9; padding:20px;">
        <h2>📄 Minhas Requisições</h2>

        <table border="1" cellpadding="8" style="width:100%; background:white;">
        <tr style="background:#111; color:white;">
            <th>ID</th><th>Código</th><th>Descrição</th><th>Qtd</th><th>Data</th><th>Status</th>
        </tr>
    """

    for r in requisicoes:
        if r["user"] == request.session.get("user"):

            cor = ""
            if r["status"] == "PENDENTE":
                cor = "background:#fff3cd;"
            elif r["status"] == "ATENDIDO":
                cor = "background:#d4edda;"
            elif r["status"] == "RECUSADO":
                cor = "background:#f8d7da;"

            html += f"""
            <tr style="{cor}">
                <td>{r['id']}</td>
                <td>{r['codigo']}</td>
                <td>{r['descricao']}</td>
                <td>{r['quantidade']}</td>
                <td>{r['data']}</td>
                <td>{r['status']}</td>
            </tr>
            """

    html += "</table><br><a href='/materiais'>Voltar</a></body></html>"
    return html

# =========================
# PAINEL ADMIN
# =========================

@app.get("/painel", response_class=HTMLResponse)
def painel(request: Request, filtro: str = "TODOS"):
    user = request.session.get("user")

    if not user or usuarios[user]["tipo"] != "admin":
        return RedirectResponse("/")

    total = len(requisicoes)
    pend = len([r for r in requisicoes if r["status"] == "PENDENTE"])
    ok = len([r for r in requisicoes if r["status"] == "ATENDIDO"])
    neg = len([r for r in requisicoes if r["status"] == "RECUSADO"])

    lista = requisicoes
    if filtro != "TODOS":
        lista = [r for r in requisicoes if r["status"] == filtro]

    html = f"""
    <html>
    <body style="margin:0; font-family:Arial; background:#f4f6f9;">
    <div style="padding:20px;">
        <h2>📊 Dashboard</h2>

        <p>Total: {total} | Pendentes: {pend} | Atendidos: {ok} | Recusados: {neg}</p>

        <table border="1" cellpadding="8" style="width:100%; background:white;">
        <tr>
            <th>ID</th><th>User</th><th>Cod</th><th>Desc</th><th>Qtd</th><th>Status</th>
        </tr>
    """

    for r in lista:
        html += f"""
        <tr>
            <td>{r['id']}</td>
            <td>{r['user']}</td>
            <td>{r['codigo']}</td>
            <td>{r['descricao']}</td>
            <td>{r['quantidade']}</td>
            <td>{r['status']}</td>
        </tr>
        """

    html += "</table></div></body></html>"
    return html

# =========================
# STATUS
# =========================

@app.get("/atender/{id}")
def atender(id: int):
    for r in requisicoes:
        if r["id"] == id:
            r["status"] = "ATENDIDO"
            salvar()
            break
    return RedirectResponse("/painel")

@app.get("/recusar/{id}")
def recusar(id: int):
    for r in requisicoes:
        if r["id"] == id:
            r["status"] = "RECUSADO"
            salvar()
            break
    return RedirectResponse("/painel")

# =========================
# LOGOUT
# =========================

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")