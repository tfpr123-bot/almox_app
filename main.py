from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
import pandas as pd
import unicodedata
from datetime import datetime, date, timedelta
import calendar
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    SessionMiddleware,
    secret_key="almox_app_chave_2026",
    max_age=60 * 60 * 24 * 30  # sessão dura 30 dias
)

# =========================
# BANCO DE DADOS (Postgres via SQLAlchemy)
# =========================
# DATABASE_URL vem de uma variável de ambiente (configure no Render).
# Se não existir (ex: rodando local sem configurar nada), cai para um
# arquivo sqlite local só para não quebrar o desenvolvimento.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./almox_local.db")

# Render/Supabase às vezes fornecem a URL como "postgres://", mas o
# SQLAlchemy moderno exige "postgresql://". Corrige automaticamente.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Requisicao(Base):
    __tablename__ = "requisicoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user = Column(String, nullable=False)
    codigo = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    quantidade = Column(Integer, nullable=False)
    data = Column(String, nullable=False)  # mantém o formato "%d/%m/%Y %H:%M" já usado no HTML
    status = Column(String, nullable=False, default="PENDENTE")

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user,
            "codigo": self.codigo,
            "descricao": self.descricao,
            "quantidade": self.quantidade,
            "data": self.data,
            "status": self.status,
        }


# Cria a tabela no banco se ainda não existir (não apaga dados existentes)
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # fechamos manualmente em cada rota para simplificar (app pequeno)


# =========================
# UNIDADES
# =========================
# Cada unidade tem um nome de exibição e o arquivo de catálogo de materiais
# que deve ser usado nas telas de requisição/materiais daquela unidade.
UNIDADES = {
    "AREAL RECRIA": {
        "nome": "Areal Recria",
        "arquivo_materiais": "materiais.xlsx",
    },
    "FABRICA RACAO": {
        "nome": "Fábrica de Ração",
        "arquivo_materiais": "materiais_fabrica.xlsx",
    },
    "FAZENDA VITORIA": {
        "nome": "Fazenda Vitória",
        "arquivo_materiais": "materiais_vitoria.xlsx",
    },
}


def arquivo_materiais_da_unidade(unidade):
    return UNIDADES.get(unidade, UNIDADES["AREAL RECRIA"])["arquivo_materiais"]


# =========================
# USUÁRIOS
# =========================
usuarios = {
    "admin": {"senha": "123", "tipo": "admin", "unidade": "AREAL RECRIA"},
    "A01": {"senha": "123", "tipo": "setor", "unidade": "AREAL RECRIA"},
    "A02": {"senha": "123", "tipo": "setor", "unidade": "AREAL RECRIA"},
    "A03": {"senha": "123", "tipo": "setor", "unidade": "AREAL RECRIA"},
    "A04": {"senha": "123", "tipo": "setor", "unidade": "AREAL RECRIA"},
    "A05": {"senha": "123", "tipo": "setor", "unidade": "AREAL RECRIA"},
    "A06": {"senha": "123", "tipo": "setor", "unidade": "AREAL RECRIA"},
    "A07": {"senha": "123", "tipo": "setor", "unidade": "AREAL RECRIA"},
    "A08": {"senha": "123", "tipo": "setor", "unidade": "AREAL RECRIA"},
    "BANHEIRO CENTRAL": {"senha": "123", "tipo": "setor", "unidade": "AREAL RECRIA"},

    # --- Fábrica de Ração ---
    "admin_fabrica": {"senha": "123", "tipo": "admin", "unidade": "FABRICA RACAO"},
    "LIDER PRODUCAO": {"senha": "123", "tipo": "setor", "unidade": "FABRICA RACAO"},
    "LIDER MANUTENCAO": {"senha": "123", "tipo": "setor", "unidade": "FABRICA RACAO"},

    # --- Fazenda Vitória ---
    "admin_vitoria": {"senha": "123", "tipo": "admin", "unidade": "FAZENDA VITORIA"},
    "AP03": {"senha": "123", "tipo": "setor", "unidade": "FAZENDA VITORIA"},
    "AP04": {"senha": "123", "tipo": "setor", "unidade": "FAZENDA VITORIA"},
    "AP05": {"senha": "123", "tipo": "setor", "unidade": "FAZENDA VITORIA"},
    "AP06": {"senha": "123", "tipo": "setor", "unidade": "FAZENDA VITORIA"},
    "AP07": {"senha": "123", "tipo": "setor", "unidade": "FAZENDA VITORIA"},
    "AP10": {"senha": "123", "tipo": "setor", "unidade": "FAZENDA VITORIA"},
    "AP11": {"senha": "123", "tipo": "setor", "unidade": "FAZENDA VITORIA"},
    "AP13": {"senha": "123", "tipo": "setor", "unidade": "FAZENDA VITORIA"},
    "MANUTENCAO-VIT": {"senha": "123", "tipo": "setor", "unidade": "FAZENDA VITORIA"},
    "BC VITORIA": {"senha": "123", "tipo": "setor", "unidade": "FAZENDA VITORIA"},
}

# =========================
# UTIL
# =========================
def normalizar(txt):
    if not isinstance(txt, str):
        return str(txt)
    txt = txt.strip().upper()
    return unicodedata.normalize("NFKD", txt).encode("ASCII", "ignore").decode("ASCII")


def carregar_excel(arquivo="materiais.xlsx"):
    df = pd.read_excel(arquivo)
    df.columns = [normalizar(c) for c in df.columns]
    return df


def pegar_colunas(df):
    cods = [c for c in df.columns if "COD" in c]
    descs = [c for c in df.columns if "DESC" in c]
    if not cods or not descs:
        raise ValueError(
            "A planilha de materiais precisa ter uma coluna com 'CODIGO' e outra com 'DESCRICAO' no nome."
        )
    return cods[0], descs[0]


def unidade_do_usuario(request: Request):
    return usuarios.get(request.session.get("user"), {}).get("unidade", "AREAL RECRIA")


# =========================
# TEMA / LAYOUT BASE
# =========================
FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
"""


def base_html(titulo, corpo, extra_head=""):
    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{titulo} · Almox</title>
        {FONTS}
        <link rel="stylesheet" href="/static/style.css?v=3">
        {extra_head}
    </head>
    <body>
        {corpo}
    </body>
    </html>
    """


def topbar(tipo="setor", unidade=None):
    if tipo == "admin":
        nav = '<a class="link" href="/painel">📊 Painel</a><a class="link" href="/logout">Sair</a>'
    else:
        nav = '<a class="link" href="/menu">⬅️ Menu</a><a class="link" href="/logout">Sair</a>'

    nome_unidade = UNIDADES.get(unidade, {}).get("nome", "")
    tag_unidade = f'<span class="unit-tag">{nome_unidade}</span>' if nome_unidade else ""

    return f"""
    <div class="topbar">
        <div class="brand">
            <img src="/static/logo.png.png">
            <span>ALMOX</span>
            {tag_unidade}
        </div>
        <nav>
            {nav}
        </nav>
    </div>
    """


def pagina_erro(msg):
    corpo = f"""
    <div class="error-wrap">
        <div class="card error-card">
            <div class="icon">⚠️</div>
            <h2>Ops, deu um problema</h2>
            <p>{msg}</p>
            <a class="btn btn-dark btn-block" href="/materiais">Voltar</a>
        </div>
    </div>
    """
    return HTMLResponse(base_html("Erro", corpo))


def badge(status):
    classe = {
        "PENDENTE": "badge-pendente",
        "ATENDIDO": "badge-atendido",
        "RECUSADO": "badge-recusado",
    }.get(status, "badge-pendente")
    return f'<span class="badge {classe}">{status}</span>'


# =========================
# LOGIN
# =========================
@app.get("/", response_class=HTMLResponse)
def login(request: Request):
    usuario_salvo = request.cookies.get("usuario_salvo", "")
    checked = "checked" if usuario_salvo else ""

    corpo = f"""
    <div class="login-wrap">
        <div class="card login-card">
            <img src="/static/logo.png.png">
            <h2 class="login-title">Gestão de Requisições</h2>
            <span class="login-subtitle login-subtitle-center">Grupo Alvorada</span>
            <form method="post" action="/login">
                <input class="field" name="usuario" placeholder="Usuário" autocomplete="off" value="{usuario_salvo}">
                <input class="field" name="senha" type="password" placeholder="Senha">
                <label class="remember-check">
                    <input type="checkbox" name="lembrar" value="1" {checked}>
                    Lembrar meu usuário
                </label>
                <button class="btn btn-primary btn-block" type="submit">Entrar</button>
            </form>
        </div>
    </div>
    """
    return base_html("Login", corpo)


@app.post("/login")
def login_post(request: Request, usuario: str = Form(...), senha: str = Form(...), lembrar: str = Form(None)):
    if usuario in usuarios and usuarios[usuario]["senha"] == senha:
        request.session["user"] = usuario
        destino = "/painel" if usuarios[usuario]["tipo"] == "admin" else "/menu"
        resposta = RedirectResponse(destino, status_code=303)
        if lembrar:
            resposta.set_cookie(
                "usuario_salvo",
                usuario,
                max_age=60 * 60 * 24 * 30,
                httponly=True,
                samesite="lax",
            )
        else:
            resposta.delete_cookie("usuario_salvo")
        return resposta
    return RedirectResponse("/", status_code=303)


# =========================
# MENU PRINCIPAL (usuário de setor)
# =========================
@app.get("/menu", response_class=HTMLResponse)
def menu(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/")
    if usuarios.get(request.session["user"], {}).get("tipo") == "admin":
        return RedirectResponse("/painel")

    corpo = f"""
    <div class="menu-wrap">
        <div class="menu-shell">
            <img src="/static/logo.png.png">
            <span class="eyebrow">Setor: {request.session['user']}</span>
            <h2>O que você precisa fazer?</h2>
            <p class="page-sub">Toque em uma das opções abaixo.</p>

            <a class="menu-btn primary" href="/requisicao">
                <span class="icon">🧾</span>
                <span class="text">
                    <span class="title">Nova requisição</span>
                    <span class="sub">Pedir um material ao almoxarifado</span>
                </span>
                <span class="arrow">›</span>
            </a>

            <a class="menu-btn secondary" href="/minhas">
                <span class="icon">📄</span>
                <span class="text">
                    <span class="title">Status da requisição</span>
                    <span class="sub">Ver o andamento dos seus pedidos</span>
                </span>
                <span class="arrow">›</span>
            </a>

            <a class="menu-btn exit" href="/logout">
                <span class="icon">🚪</span>
                <span class="text">
                    <span class="title">Sair</span>
                    <span class="sub">Voltar para a tela de login</span>
                </span>
                <span class="arrow">›</span>
            </a>
        </div>
    </div>
    """
    return base_html("Menu", corpo)


# =========================
# MATERIAIS
# =========================
@app.get("/materiais", response_class=HTMLResponse)
def materiais(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)
    arquivo = arquivo_materiais_da_unidade(unidade)

    try:
        df = carregar_excel(arquivo)
    except FileNotFoundError:
        return pagina_erro(f"Arquivo {arquivo} não encontrado. Coloque a planilha na pasta do sistema.")
    except ValueError as e:
        return pagina_erro(str(e))

    tabela = df.to_html(index=False, classes="tbl", border=0)

    corpo = f"""
    {topbar(usuarios.get(request.session["user"], {}).get("tipo", "setor"), unidade)}
    <div class="page">
        <span class="eyebrow">Catálogo</span>
        <h2>📦 Materiais</h2>
        <p class="page-sub">Consulta geral de itens disponíveis no almoxarifado.</p>
        <div class="table-wrap">
            {tabela}
        </div>
    </div>
    """
    return base_html("Materiais", corpo)


# =========================
# REQUISIÇÃO
# =========================
@app.get("/requisicao", response_class=HTMLResponse)
def req(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)
    arquivo = arquivo_materiais_da_unidade(unidade)

    try:
        df = carregar_excel(arquivo)
        cod, desc = pegar_colunas(df)
    except FileNotFoundError:
        return pagina_erro(f"Arquivo {arquivo} não encontrado.")
    except ValueError as e:
        return pagina_erro(str(e))

    unidades_medida = [c for c in df.columns if "UNID" in c]
    col_un = unidades_medida[0] if unidades_medida else None

    itens_html = ""
    for _, r in df.iterrows():
        un = f" ({r[col_un]})" if col_un else ""
        itens_html += f"""
        <div class="item" data-codigo="{r[cod]}" data-desc="{r[desc]}{un}"
             onclick="selecionar(this)">
            <span class="code">{r[cod]}</span>{r[desc]}{un}
        </div>
        """

    corpo = f"""
    {topbar("setor", unidade)}
    <div class="page page-narrow">
        <span class="eyebrow">Setor: {request.session['user']}</span>
        <h2>🧾 Nova requisição</h2>
        <p class="page-sub">Busque o material, selecione na lista e informe a quantidade.</p>

        <div class="search-wrap">
            <input class="field" id="busca" type="text" placeholder="Buscar material por nome ou código..."
                   oninput="filtrar()" autocomplete="off">
        </div>

        <div id="lista" class="item-list">
            {itens_html}
        </div>

        <form method="post" action="/enviar" onsubmit="return validar()" style="margin-top:16px;">
            <div id="selecionado" class="selected-box empty">Nenhum item selecionado</div>
            <input type="hidden" name="codigo" id="codigo">
            <input class="field" type="number" name="quantidade" min="1" placeholder="Quantidade" required>
            <button class="btn btn-primary btn-block" type="submit">Enviar requisição</button>
        </form>
    </div>

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
            i.classList.remove('is-selected');
        }});
        el.classList.add('is-selected');
        document.getElementById('codigo').value = el.getAttribute('data-codigo');
        const box = document.getElementById('selecionado');
        box.classList.remove('empty');
        box.innerText = '✅ ' + el.getAttribute('data-desc');
    }}

    function validar() {{
        if (!document.getElementById('codigo').value) {{
            alert('Selecione um material na lista antes de enviar.');
            return false;
        }}
        return true;
    }}
    </script>
    """
    return base_html("Nova requisição", corpo)


# =========================
# ENVIAR
# =========================
@app.post("/enviar")
def enviar(request: Request, codigo: str = Form(...), quantidade: int = Form(...)):
    if not request.session.get("user"):
        return RedirectResponse("/")

    if quantidade <= 0:
        return pagina_erro("Quantidade precisa ser maior que zero.")

    unidade = unidade_do_usuario(request)
    arquivo = arquivo_materiais_da_unidade(unidade)

    try:
        df = carregar_excel(arquivo)
        cod, desc = pegar_colunas(df)
    except FileNotFoundError:
        return pagina_erro(f"Arquivo {arquivo} não encontrado.")
    except ValueError as e:
        return pagina_erro(str(e))

    df[cod] = df[cod].astype(str).str.strip().str.upper()
    codigo = codigo.strip().upper()
    item = df[df[cod] == codigo]
    if item.empty:
        return pagina_erro("Material não encontrado.")
    item = item.iloc[0]

    db = get_db()
    try:
        nova = Requisicao(
            user=request.session["user"],
            codigo=codigo,
            descricao=str(item[desc]),
            quantidade=quantidade,
            data=datetime.now().strftime("%d/%m/%Y %H:%M"),
            status="PENDENTE",
        )
        db.add(nova)
        db.commit()
    finally:
        db.close()

    return RedirectResponse("/minhas", status_code=303)


# =========================
# MINHAS REQUISIÇÕES
# =========================
@app.get("/minhas", response_class=HTMLResponse)
def minhas(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)

    db = get_db()
    try:
        minhas_reqs = (
            db.query(Requisicao)
            .filter(Requisicao.user == request.session["user"])
            .order_by(Requisicao.id.desc())
            .all()
        )
    finally:
        db.close()

    linhas = ""
    for r in minhas_reqs:
        linhas += f"""
        <tr>
            <td class="mono">#{r.id}</td>
            <td class="mono">{r.codigo}</td>
            <td>{r.descricao}</td>
            <td>{r.quantidade}</td>
            <td>{r.data}</td>
            <td>{badge(r.status)}</td>
        </tr>
        """

    if not minhas_reqs:
        conteudo_tabela = '<div class="empty-state">Você ainda não enviou nenhuma requisição.</div>'
    else:
        conteudo_tabela = f"""
        <table class="tbl">
            <tr>
                <th>ID</th><th>Código</th><th>Descrição</th><th>Qtd</th><th>Data</th><th>Status</th>
            </tr>
            {linhas}
        </table>
        """

    corpo = f"""
    {topbar("setor", unidade)}
    <div class="page">
        <span class="eyebrow">Setor: {request.session['user']}</span>
        <h2>📄 Minhas requisições</h2>
        <p class="page-sub">Acompanhe o status de tudo o que você já solicitou.</p>
        <div class="table-wrap">
            {conteudo_tabela}
        </div>
    </div>
    """
    return base_html("Minhas requisições", corpo)


def sidebar(ativo="dashboard", unidade=None):
    def item(href, label, chave):
        cls = "nav-link active" if ativo == chave else "nav-link"
        return f'<a class="{cls}" href="{href}">{label}</a>'

    nome_unidade = UNIDADES.get(unidade, {}).get("nome", "")
    tag_unidade = f'<span class="unit-tag">{nome_unidade}</span>' if nome_unidade else ""

    return f"""
    <div class="sidebar">
        <div class="sidebar-logo">
            <img src="/static/logo.png.png">
        </div>
        <span class="brand-tag">Painel admin</span>
        {tag_unidade}
        {item("/painel", "📊 Dashboard", "dashboard")}
        {item("/relatorio", "📈 Relatório", "relatorio")}
        {item("/materiais", "📦 Materiais", "materiais")}
        {item("/materiais/cadastrar", "➕ Cadastrar material", "cadastrar")}
        <a class="nav-link logout" href="/logout">🚪 Sair</a>
    </div>
    """


# =========================
# CADASTRO DE MATERIAL
# =========================
@app.get("/materiais/cadastrar", response_class=HTMLResponse)
def cadastrar_material_form(request: Request):
    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)

    corpo = f"""
    <div class="admin-shell">
        {sidebar("cadastrar", unidade)}
        <div class="admin-content">
            <span class="eyebrow">Catálogo · {UNIDADES.get(unidade, {}).get("nome", "")}</span>
            <h2>➕ Cadastrar material</h2>
            <p class="page-sub">Adicione um novo item ao catálogo desta unidade.</p>

            <div class="card" style="padding:20px; max-width:420px;">
                <form method="post" action="/materiais/cadastrar">
                    <input class="field" name="codigo" placeholder="Código" required>
                    <input class="field" name="descricao" placeholder="Descrição do material" required>
                    <input class="field" name="unidade_medida" placeholder="Unidade (ex: UN, KG, CX)" required>
                    <button class="btn btn-primary btn-block" type="submit">Cadastrar material</button>
                </form>
            </div>
        </div>
    </div>
    """
    return base_html("Cadastrar material", corpo)


@app.post("/materiais/cadastrar")
def cadastrar_material_post(
    request: Request,
    codigo: str = Form(...),
    descricao: str = Form(...),
    unidade_medida: str = Form(...),
):
    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)
    arquivo = arquivo_materiais_da_unidade(unidade)

    try:
        df = pd.read_excel(arquivo)
        df.columns = [normalizar(c) for c in df.columns]
    except FileNotFoundError:
        df = pd.DataFrame(columns=["CODIGO", "DESCRICAO", "UNIDADE"])

    cod_col = next((c for c in df.columns if "COD" in c), "CODIGO")
    desc_col = next((c for c in df.columns if "DESC" in c), "DESCRICAO")
    unid_col = next((c for c in df.columns if "UNID" in c), "UNIDADE")

    codigo_norm = codigo.strip().upper()

    if not df.empty and (df[cod_col].astype(str).str.strip().str.upper() == codigo_norm).any():
        return pagina_erro(f"Já existe um material cadastrado com o código {codigo_norm}.")

    novo = {
        cod_col: codigo_norm,
        desc_col: descricao.strip().upper(),
        unid_col: unidade_medida.strip().upper(),
    }
    df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
    df.to_excel(arquivo, index=False)

    return RedirectResponse("/materiais", status_code=303)


# =========================
# PAINEL ADMIN (COM FILTRO)
# =========================
@app.get("/painel", response_class=HTMLResponse)
def painel(request: Request, filtro: str = "TODOS"):
    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)

    db = get_db()
    try:
        todas = db.query(Requisicao).order_by(Requisicao.id.desc()).all()
    finally:
        db.close()

    total = len(todas)
    pend = len([r for r in todas if r.status == "PENDENTE"])
    ok = len([r for r in todas if r.status == "ATENDIDO"])
    neg = len([r for r in todas if r.status == "RECUSADO"])

    lista = todas
    if filtro != "TODOS":
        lista = [r for r in todas if r.status == filtro]

    def chip(valor, label):
        ativo = "active" if filtro == valor else ""
        return f'<a class="filter-chip {ativo}" href="/painel?filtro={valor}">{label}</a>'

    linhas = ""
    for r in lista:
        linhas += f"""
        <tr>
            <td class="mono">#{r.id}</td>
            <td>{r.user}</td>
            <td class="mono">{r.codigo}</td>
            <td>{r.descricao}</td>
            <td>{r.quantidade}</td>
            <td>{badge(r.status)}</td>
            <td>
                <div class="row-actions">
                    <a class="btn btn-icon btn-approve" href="/atender/{r.id}">✔️ Atender</a>
                    <a class="btn btn-icon btn-reject" href="/recusar/{r.id}">❌ Recusar</a>
                </div>
            </td>
            <td><a class="btn btn-icon btn-print" href="/imprimir/{r.id}">🖨️</a></td>
        </tr>
        """

    if not lista:
        tabela_html = '<div class="empty-state">Nenhuma requisição encontrada para este filtro.</div>'
    else:
        tabela_html = f"""
        <table class="tbl">
            <tr>
                <th>ID</th><th>Setor</th><th>Código</th><th>Descrição</th><th>Qtd</th><th>Status</th><th>Ações</th><th></th>
            </tr>
            {linhas}
        </table>
        """

    corpo = f"""
    <div class="admin-shell">
        {sidebar("dashboard", unidade)}
        <div class="admin-content">
            <span class="eyebrow">Visão geral</span>
            <h2>📊 Dashboard de requisições</h2>
            <p class="page-sub">Acompanhe, atenda e recuse os pedidos dos setores.</p>

            <div class="stat-row">
                <div class="stat-card">
                    <span class="label">Total</span>
                    <span class="num">{total}</span>
                </div>
                <div class="stat-card accent-pendente">
                    <span class="label">Pendentes</span>
                    <span class="num">{pend}</span>
                </div>
                <div class="stat-card accent-atendido">
                    <span class="label">Atendidos</span>
                    <span class="num">{ok}</span>
                </div>
                <div class="stat-card accent-recusado">
                    <span class="label">Recusados</span>
                    <span class="num">{neg}</span>
                </div>
            </div>

            <div class="filter-row">
                {chip("TODOS", "Todos")}
                {chip("PENDENTE", "Pendentes")}
                {chip("ATENDIDO", "Atendidos")}
                {chip("RECUSADO", "Recusados")}
            </div>

            <div class="table-wrap">
                {tabela_html}
            </div>
        </div>
    </div>
    """
    return base_html("Painel admin", corpo)


# =========================
# RELATÓRIO (GRÁFICO POR PERÍODO)
# =========================
@app.get("/relatorio", response_class=HTMLResponse)
def relatorio(request: Request, inicio: str = "", fim: str = ""):
    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)
    hoje = date.today()

    def parse_data_req(s):
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                return datetime.strptime(str(s), fmt).date()
            except Exception:
                continue
        return None

    def primeiro_dia_mes(d):
        return d.replace(day=1)

    def ultimo_dia_mes(d):
        return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])

    # período padrão: mês atual
    inicio_d = primeiro_dia_mes(hoje)
    fim_d = hoje

    if inicio:
        try:
            inicio_d = date.fromisoformat(inicio)
        except Exception:
            pass
    if fim:
        try:
            fim_d = date.fromisoformat(fim)
        except Exception:
            pass

    if inicio_d > fim_d:
        inicio_d, fim_d = fim_d, inicio_d

    db = get_db()
    try:
        todas = db.query(Requisicao).all()
    finally:
        db.close()

    filtradas = []
    for r in todas:
        d = parse_data_req(r.data)
        if d and inicio_d <= d <= fim_d:
            filtradas.append(r)

    resumo = {}
    for r in filtradas:
        setor = r.user
        if setor not in resumo:
            resumo[setor] = {"requisicoes": 0, "itens": 0}
        resumo[setor]["requisicoes"] += 1
        resumo[setor]["itens"] += int(r.quantidade or 0)

    setores_ordenados = sorted(resumo.items(), key=lambda x: x[1]["requisicoes"], reverse=True)
    labels = [s for s, _ in setores_ordenados]
    valores_req = [v["requisicoes"] for _, v in setores_ordenados]

    linhas_tabela = ""
    for setor, v in setores_ordenados:
        linhas_tabela += f"""
        <tr>
            <td>{setor}</td>
            <td class="mono">{v['requisicoes']}</td>
            <td class="mono">{v['itens']}</td>
        </tr>
        """

    if not setores_ordenados:
        tabela_html = '<div class="empty-state">Nenhuma requisição encontrada nesse período.</div>'
        grafico_html = '<div class="empty-state">Sem dados para exibir no gráfico.</div>'
    else:
        tabela_html = f"""
        <table class="tbl">
            <tr><th>Setor</th><th>Requisições</th><th>Itens solicitados</th></tr>
            {linhas_tabela}
        </table>
        """
        grafico_html = '<canvas id="graficoSetores" height="110"></canvas>'

    def periodo(dias_ini, dias_fim, chave):
        ativo = "active" if inicio == dias_ini.isoformat() and fim == dias_fim.isoformat() else ""
        return f'<a class="filter-chip {ativo}" href="/relatorio?inicio={dias_ini.isoformat()}&fim={dias_fim.isoformat()}">{chave}</a>'

    mes_passado_ref = (primeiro_dia_mes(hoje) - timedelta(days=1))

    corpo = f"""
    <div class="admin-shell">
        {sidebar("relatorio", unidade)}
        <div class="admin-content">
            <span class="eyebrow">Comparativo por período</span>
            <h2>📈 Relatório de requisições</h2>
            <p class="page-sub">Compare a quantidade de requisições feitas por cada setor no período selecionado.</p>

            <form method="get" action="/relatorio" class="card" style="padding:16px 18px; margin-bottom:16px; display:flex; gap:12px; align-items:flex-end; flex-wrap:wrap;">
                <div>
                    <span class="label" style="font-family:'IBM Plex Mono',monospace; font-size:11px; color:var(--ink-soft); display:block; margin-bottom:4px;">De</span>
                    <input class="field" style="margin-bottom:0;" type="date" name="inicio" value="{inicio_d.isoformat()}">
                </div>
                <div>
                    <span class="label" style="font-family:'IBM Plex Mono',monospace; font-size:11px; color:var(--ink-soft); display:block; margin-bottom:4px;">Até</span>
                    <input class="field" style="margin-bottom:0;" type="date" name="fim" value="{fim_d.isoformat()}">
                </div>
                <button class="btn btn-dark" type="submit">Aplicar</button>
            </form>

            <div class="filter-row">
                {periodo(primeiro_dia_mes(hoje), hoje, "Este mês")}
                {periodo(primeiro_dia_mes(mes_passado_ref), ultimo_dia_mes(mes_passado_ref), "Mês passado")}
                {periodo(date(hoje.year, 1, 1), hoje, "Este ano")}
                {periodo(date(2000, 1, 1), hoje, "Todos")}
            </div>

            <div class="card" style="padding:20px; margin-bottom:20px;">
                {grafico_html}
            </div>

            <div class="table-wrap">
                {tabela_html}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <script>
    const labels = {labels!r};
    const dadosReq = {valores_req!r};

    const canvas = document.getElementById('graficoSetores');
    if (canvas) {{
        new Chart(canvas, {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: 'Requisições',
                        data: dadosReq,
                        backgroundColor: '#E85D1F',
                        borderRadius: 6,
                        maxBarThickness: 56
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: (ctx) => ctx.parsed.y + ' requisição(ões)'
                        }}
                    }}
                }},
                scales: {{
                    y: {{ beginAtZero: true, ticks: {{ precision: 0, stepSize: 1 }} }}
                }}
            }}
        }});
    }}
    </script>
    """
    return base_html("Relatório", corpo)


# =========================
# IMPRIMIR
# =========================
@app.get("/imprimir/{id}", response_class=HTMLResponse)
def imprimir(request: Request, id: int):
    if not request.session.get("user"):
        return RedirectResponse("/")

    db = get_db()
    try:
        req = db.query(Requisicao).filter(Requisicao.id == id).first()
    finally:
        db.close()

    if not req:
        return pagina_erro("Requisição não encontrada.")

    status_classe = req.status.lower()

    corpo = f"""
    <div class="ticket">
        <span class="stamp {status_classe}">{req.status}</span>
        <span class="eyebrow">Ficha de requisição</span>
        <h2>REQUISIÇÃO DE MATERIAL</h2>

        <div class="row"><span class="k">ID</span><span class="v mono">#{req.id}</span></div>
        <div class="row"><span class="k">Setor</span><span class="v">{req.user}</span></div>
        <div class="row"><span class="k">Data</span><span class="v">{req.data}</span></div>
        <div class="row"><span class="k">Código</span><span class="v mono">{req.codigo}</span></div>
        <div class="row"><span class="k">Material</span><span class="v">{req.descricao}</span></div>
        <div class="row"><span class="k">Quantidade</span><span class="v">{req.quantidade}</span></div>

        <div class="sig">
            <div class="line"></div>
            Almoxarifado
        </div>
    </div>
    """

    extra = """
    <script>
    window.onload = function(){
        window.print();
        window.onafterprint = function(){
            window.location.href = "/painel";
        }
    }
    </script>
    """
    return base_html("Imprimir requisição", corpo, extra_head=extra)


# =========================
# STATUS
# =========================
@app.get("/atender/{id}")
def atender(request: Request, id: int):
    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
        return RedirectResponse("/")

    db = get_db()
    try:
        r = db.query(Requisicao).filter(Requisicao.id == id).first()
        if r:
            r.status = "ATENDIDO"
            db.commit()
    finally:
        db.close()

    return RedirectResponse("/painel")


@app.get("/recusar/{id}")
def recusar(request: Request, id: int):
    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
        return RedirectResponse("/")

    db = get_db()
    try:
        r = db.query(Requisicao).filter(Requisicao.id == id).first()
        if r:
            r.status = "RECUSADO"
            db.commit()
    finally:
        db.close()

    return RedirectResponse("/painel")


# =========================
# LOGOUT
# =========================
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
