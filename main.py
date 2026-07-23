from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
import pandas as pd
import unicodedata
from datetime import datetime
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    SessionMiddleware,
    secret_key="almox_app_chave_2026"
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
    except Exception:
        requisicoes = []

def salvar():
    pd.DataFrame(requisicoes).to_excel(ARQ, index=False)

def proximo_id():
    if not requisicoes:
        return 1
    return max(r["id"] for r in requisicoes) + 1

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
    cods = [c for c in df.columns if "COD" in c]
    descs = [c for c in df.columns if "DESC" in c]
    if not cods or not descs:
        raise ValueError(
            "A planilha materiais.xlsx precisa ter uma coluna com 'CODIGO' e outra com 'DESCRICAO' no nome."
        )
    return cods[0], descs[0]

def pagina_erro(msg):
    return HTMLResponse(f"""
    <html>
    <body style="font-family:Arial; padding:30px;">
        <h2>⚠️ Ops, deu um problema</h2>
        <p>{msg}</p>
        <a href="/materiais">Voltar</a>
    </body>
    </html>
    """)

# =========================
# LOGIN
# =========================

@app.get("/", response_class=HTMLResponse)
def login():
    return """
    <html>
    <body style="font-family:Arial; display:flex; justify-content:center; align-items:center; height:100vh; background:#f4f6f9;">
        <div style="background:white; padding:30px; border-radius:10px; width:300px; text-align:center;">
            <img src="/static/logo.png" style="max-width:200px; margin-bottom:15px;">
            <h2>🔐 Login</h2>

            <form method="post" action="/login">
                <input name="usuario" placeholder="Usuário" style="width:100%; padding:8px;">
                <br><br>
                <input name="senha" type="password" placeholder="Senha" style="width:100%; padding:8px;">
                <br><br>
                <button style="width:100%; padding:10px; background:#111; color:white;">Entrar</button>
            </form>
        </div>
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
            return RedirectResponse("/requisicao", status_code=303)

    return RedirectResponse("/", status_code=303)

# =========================
# MATERIAIS
# =========================

@app.get("/materiais", response_class=HTMLResponse)
def materiais(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/")

    try:
        df = carregar_excel()
    except FileNotFoundError:
        return pagina_erro("Arquivo materiais.xlsx não encontrado. Coloque a planilha na pasta do sistema.")
    except ValueError as e:
        return pagina_erro(str(e))

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

    try:
        df = carregar_excel()
        cod, desc = pegar_colunas(df)
    except FileNotFoundError:
        return pagina_erro("Arquivo materiais.xlsx não encontrado.")
    except ValueError as e:
        return pagina_erro(str(e))

    unidades = [c for c in df.columns if "UNID" in c]
    col_un = unidades[0] if unidades else None

    itens_html = ""
    for _, r in df.iterrows():
        un = f" ({r[col_un]})" if col_un else ""
        itens_html += f"""
        <div class="item" data-codigo="{r[cod]}" data-desc="{r[desc]}{un}"
             onclick="selecionar(this)"
             style="padding:10px; border-bottom:1px solid #eee; cursor:pointer;">
            <b>{r[cod]}</b> - {r[desc]}{un}
        </div>
        """

    return f"""
    <html>
    <body style="font-family:Arial; padding:20px; max-width:500px; margin:0 auto;">
        <div style="text-align:center; margin-bottom:10px;">
            <img src="/static/logo.png" style="max-width:150px;">
        </div>
        <h2>🧾 Nova Requisição</h2>

        <input id="busca" type="text" placeholder="🔎 Buscar material por nome..."
               oninput="filtrar()" autocomplete="off"
               style="width:100%; padding:10px; box-sizing:border-box; margin-bottom:10px; font-size:16px;">

        <div id="lista" style="max-height:300px; overflow-y:auto; border:1px solid #ddd; border-radius:6px; margin-bottom:15px;">
            {itens_html}
        </div>

        <form method="post" action="/enviar" onsubmit="return validar()">
            <div id="selecionado" style="margin-bottom:10px; font-weight:bold; color:#111;">Nenhum item selecionado</div>
            <input type="hidden" name="codigo" id="codigo">

            <input type="number" name="quantidade" min="1" placeholder="Quantidade" required
                   style="width:100%; padding:10px; box-sizing:border-box; font-size:16px;">
            <br><br>
            <button style="width:100%; padding:12px; background:#111; color:white; border:none; border-radius:6px; font-size:16px;">Enviar Requisição</button>
        </form>

        <br>
        <a href="/minhas">📄 Ver status das minhas requisições</a> |
        <a href="/logout">Sair</a>

        <script>
        function filtrar() {{
            const termo = document.getElementById('busca').value.toUpperCase();
            const itens = document.querySelectorAll('.item');
            itens.forEach(function(item) {{
                const desc = item.getAttribute('data-desc').toUpperCase();
                const cod = item.getAttribute('data-codigo').toUpperCase();
                item.style.display = (desc.includes(termo) || cod.includes(termo)) ? '' : 'none';
            }});
        }}

        function selecionar(el) {{
            document.querySelectorAll('.item').forEach(function(i) {{
                i.style.background = '';
            }});
            el.style.background = '#e6f0ff';
            document.getElementById('codigo').value = el.getAttribute('data-codigo');
            document.getElementById('selecionado').innerText = '✅ ' + el.getAttribute('data-desc');
        }}

        function validar() {{
            if (!document.getElementById('codigo').value) {{
                alert('Selecione um material na lista antes de enviar.');
                return false;
            }}
            return true;
        }}
        </script>
    </body>
    </html>
    """

# =========================
# ENVIAR
# =========================

@app.post("/enviar")
def enviar(request: Request, codigo: str = Form(...), quantidade: int = Form(...)):
    if not request.session.get("user"):
        return RedirectResponse("/")

    if quantidade <= 0:
        return pagina_erro("Quantidade precisa ser maior que zero.")

    try:
        df = carregar_excel()
        cod, desc = pegar_colunas(df)
    except FileNotFoundError:
        return pagina_erro("Arquivo materiais.xlsx não encontrado.")
    except ValueError as e:
        return pagina_erro(str(e))

    df[cod] = df[cod].astype(str).str.strip().str.upper()
    codigo = codigo.strip().upper()

    item = df[df[cod] == codigo]

    if item.empty:
        return pagina_erro("Material não encontrado.")

    item = item.iloc[0]

    requisicoes.append({
        "id": proximo_id(),
        "user": request.session["user"],
        "codigo": codigo,
        "descricao": item[desc],
        "quantidade": quantidade,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "status": "PENDENTE"
    })

    salvar()
    return RedirectResponse("/minhas", status_code=303)

# =========================
# MINHAS REQUISIÇÕES
# =========================

@app.get("/minhas", response_class=HTMLResponse)
def minhas(request: Request):

    if not request.session.get("user"):
        return RedirectResponse("/")

    html = """
    <html>
    <body style="font-family:Arial; background:#f4f6f9; padding:20px;">
        <div style="text-align:center; margin-bottom:10px;">
            <img src="/static/logo.png" style="max-width:150px;">
        </div>
        <h2>📄 Minhas Requisições</h2>

        <table border="1" cellpadding="8" style="width:100%; background:white;">
        <tr style="background:#111; color:white;">
            <th>ID</th>
            <th>Código</th>
            <th>Descrição</th>
            <th>Qtd</th>
            <th>Data</th>
            <th>Status</th>
        </tr>
    """

    for r in requisicoes:
        if r["user"] == request.session["user"]:

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

    html += "</table><br><a href='/requisicao'>🧾 Nova Requisição</a> | <a href='/logout'>Sair</a></body></html>"
    return html

# =========================
# PAINEL ADMIN (COM FILTRO)
# =========================

@app.get("/painel", response_class=HTMLResponse)
def painel(request: Request, filtro: str = "TODOS"):

    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
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

    <div style="position:fixed; left:0; top:0; width:220px; height:100%; background:#111; color:white; padding:20px;">
        <img src="/static/logo.png" style="max-width:100%; margin-bottom:10px;">
        <h3>📦 Almox</h3>
        <a href="/painel" style="color:white; display:block; margin:10px 0;">📊 Dashboard</a>
        <a href="/logout" style="color:#ff6b6b; display:block; margin-top:20px;">🚪 Sair</a>
    </div>

    <div style="margin-left:240px; padding:20px;">
        <h2>📊 Dashboard</h2>

        <div style="display:flex; gap:10px;">
            <div style="background:white; padding:10px; flex:1;">Total<br><b>{total}</b></div>
            <div style="background:#fff3cd; padding:10px; flex:1;">Pendentes<br><b>{pend}</b></div>
            <div style="background:#d4edda; padding:10px; flex:1;">Atendidos<br><b>{ok}</b></div>
            <div style="background:#f8d7da; padding:10px; flex:1;">Recusados<br><b>{neg}</b></div>
        </div>

        <br>

        <div style="margin-bottom:15px;">
            <a href="/painel?filtro=TODOS">Todos</a> |
            <a href="/painel?filtro=PENDENTE">Pendentes</a> |
            <a href="/painel?filtro=ATENDIDO">Atendidos</a> |
            <a href="/painel?filtro=RECUSADO">Recusados</a>
        </div>

        <table style="width:100%; background:white; border-collapse:collapse;">
            <tr style="background:#111; color:white;">
                <th>ID</th><th>User</th><th>Cod</th><th>Desc</th><th>Qtd</th><th>Status</th><th>Ações</th><th>🖨️</th>
            </tr>
    """

    for r in lista:

        cor = ""
        if r["status"] == "PENDENTE":
            cor = "background:#fffbea;"
        elif r["status"] == "ATENDIDO":
            cor = "background:#e6f7ea;"
        elif r["status"] == "RECUSADO":
            cor = "background:#fdeaea;"

        html += f"""
        <tr style="{cor}">
            <td>{r['id']}</td>
            <td>{r['user']}</td>
            <td>{r['codigo']}</td>
            <td>{r['descricao']}</td>
            <td>{r['quantidade']}</td>
            <td>{r['status']}</td>
            <td>
                <a href="/atender/{r['id']}">✔️</a> |
                <a href="/recusar/{r['id']}">❌</a>
            </td>
            <td>
                <a href="/imprimir/{r['id']}">🖨️</a>
            </td>
        </tr>
        """

    html += "</table></div></body></html>"
    return html

# =========================
# IMPRIMIR
# =========================

@app.get("/imprimir/{id}", response_class=HTMLResponse)
def imprimir(id: int):

    req = None
    for r in requisicoes:
        if r["id"] == id:
            req = r
            break

    if not req:
        return pagina_erro("Requisição não encontrada.")

    return f"""
    <html>
    <head>
    <script>
        window.onload = function(){{
            window.print();
            window.onafterprint = function(){{
                window.location.href = "/painel";
            }}
        }}
    </script>
    </head>

    <body style="font-family:Arial; padding:30px;">
        <h2>REQUISIÇÃO DE MATERIAL</h2>
        <hr>

        <p><b>ID:</b> {req['id']}</p>
        <p><b>Setor:</b> {req['user']}</p>
        <p><b>Data:</b> {req['data']}</p>
        <p><b>Código:</b> {req['codigo']}</p>
        <p><b>Material:</b> {req['descricao']}</p>
        <p><b>Quantidade:</b> {req['quantidade']}</p>
        <p><b>Status:</b> {req['status']}</p>

        <br><br>
        _________
        <br>Almoxarifado
    </body>
    </html>
    """

# =========================
# STATUS
# =========================

@app.get("/atender/{id}")
def atender(request: Request, id: int):
    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
        return RedirectResponse("/")
    for r in requisicoes:
        if r["id"] == id:
            r["status"] = "ATENDIDO"
            salvar()
            break
    return RedirectResponse("/painel")

@app.get("/recusar/{id}")
def recusar(request: Request, id: int):
    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
        return RedirectResponse("/")
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
