from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
import pandas as pd
import unicodedata
from datetime import datetime, date, timedelta
import calendar
import os

from sqlalchemy import create_engine, Column, Integer, String, DateTime, inspect, text
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

# Unidade usada como padrão para requisições antigas que não tinham
# esse campo (gravadas antes da migração multi-unidade).
UNIDADE_PADRAO = "AREAL RECRIA"


class Requisicao(Base):
    __tablename__ = "requisicoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user = Column(String, nullable=False)
    unidade = Column(String, nullable=True)  # preenchido a partir da unidade do usuário que enviou
    codigo = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    quantidade = Column(Integer, nullable=False)
    data = Column(String, nullable=False)  # mantém o formato "%d/%m/%Y %H:%M" já usado no HTML
    status = Column(String, nullable=False, default="PENDENTE")

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user,
            "unidade": self.unidade,
            "codigo": self.codigo,
            "descricao": self.descricao,
            "quantidade": self.quantidade,
            "data": self.data,
            "status": self.status,
        }


# Cria a tabela no banco se ainda não existir (não apaga dados existentes)
Base.metadata.create_all(bind=engine)


def migrar_coluna_unidade():
    """
    Garante que a tabela 'requisicoes' tenha a coluna 'unidade'.
    Se o banco já existia antes dessa mudança (sem a coluna), ela é
    adicionada aqui via ALTER TABLE, e as linhas antigas (que ficariam
    com unidade NULL) são preenchidas com UNIDADE_PADRAO, para não
    "sumirem" dos painéis depois que o filtro por unidade entrar em vigor.
    """
    insp = inspect(engine)
    colunas = [c["name"] for c in insp.get_columns("requisicoes")]

    if "unidade" not in colunas:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE requisicoes ADD COLUMN unidade VARCHAR"))

    # Preenche linhas antigas (unidade NULL ou vazia) com a unidade padrão.
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE requisicoes SET unidade = :padrao "
                "WHERE unidade IS NULL OR unidade = ''"
            ),
            {"padrao": UNIDADE_PADRAO},
        )


migrar_coluna_unidade()


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
    return UNIDADES.get(unidade, UNIDADES[UNIDADE_PADRAO])["arquivo_materiais"]


def nome_unidade(unidade):
    return UNIDADES.get(unidade, UNIDADES[UNIDADE_PADRAO])["nome"]


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


def unidade_do_usuario(request: Request):
    """Unidade do usuário logado, lendo primeiro da sessão e caindo para o dicionário 'usuarios' se preciso."""
    unidade = request.session.get("unidade")
    if unidade:
        return unidade
    dados = usuarios.get(request.session.get("user"), {})
    return dados.get("unidade", UNIDADE_PADRAO)


# =========================
# UTIL
# =========================
def normalizar(txt):
    if not isinstance(txt, str):
        return str(txt)
    txt = txt.strip().upper()
    return unicodedata.normalize("NFKD", txt).encode("ASCII", "ignore").decode("ASCII")


def carregar_excel(unidade=None):
    """
    Carrega o catálogo de materiais correto para a unidade informada.
    Antes essa função sempre lia 'materiais.xlsx' fixo; agora ela usa
    o arquivo configurado em UNIDADES para a unidade do usuário logado.
    """
    arquivo = arquivo_materiais_da_unidade(unidade) if unidade else "materiais.xlsx"
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


def mapear_colunas_originais(arquivo):
    """
    Lê a planilha SEM normalizar os nomes de coluna (para não estragar o
    cabeçalho original ao salvar de novo) e devolve o DataFrame junto com
    um mapa {"codigo": <nome real da coluna>, "descricao": ..., "unidade": ...}.
    """
    df = pd.read_excel(arquivo)
    mapa = {}
    for c in df.columns:
        n = normalizar(c)
        if "COD" in n and "codigo" not in mapa:
            mapa["codigo"] = c
        elif "DESC" in n and "descricao" not in mapa:
            mapa["descricao"] = c
        elif "UNID" in n and "unidade" not in mapa:
            mapa["unidade"] = c
    return df, mapa


def adicionar_material(arquivo, codigo, descricao, unidade_medida):
    """
    Acrescenta uma linha nova ao catálogo de materiais (xlsx) da unidade,
    preenchendo apenas as colunas de código/descrição/unidade que existirem
    na planilha. Retorna (ok, mensagem).
    """
    df, mapa = mapear_colunas_originais(arquivo)

    if "codigo" not in mapa or "descricao" not in mapa:
        return False, "A planilha precisa ter colunas de código e descrição para cadastrar materiais."

    codigo = str(codigo).strip().upper()
    col_codigo = mapa["codigo"]
    ja_existe = df[col_codigo].astype(str).str.strip().str.upper().eq(codigo).any()
    if ja_existe:
        return False, f"Já existe um material cadastrado com o código {codigo}."

    nova_linha = {c: "" for c in df.columns}
    nova_linha[col_codigo] = codigo
    nova_linha[mapa["descricao"]] = descricao.strip()
    if "unidade" in mapa:
        nova_linha[mapa["unidade"]] = unidade_medida.strip()

    df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
    df.to_excel(arquivo, index=False)
    return True, f"Material {codigo} cadastrado com sucesso."


def remover_material(arquivo, codigo):
    """
    Remove do catálogo (xlsx) a linha cujo código bate com o informado.
    Retorna (ok, mensagem).
    """
    df, mapa = mapear_colunas_originais(arquivo)

    if "codigo" not in mapa:
        return False, "A planilha precisa ter uma coluna de código para excluir materiais."

    col_codigo = mapa["codigo"]
    codigo = str(codigo).strip().upper()
    mascara = df[col_codigo].astype(str).str.strip().str.upper() == codigo

    if not mascara.any():
        return False, f"Material {codigo} não encontrado."

    df = df[~mascara]
    df.to_excel(arquivo, index=False)
    return True, f"Material {codigo} excluído."


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


def topbar(tipo="setor"):
    if tipo == "admin":
        nav = '<a class="link" href="/painel">📊 Painel</a><a class="link" href="/logout">Sair</a>'
    else:
        nav = '<a class="link" href="/menu">⬅️ Menu</a><a class="link" href="/logout">Sair</a>'
    return f"""
<div class="topbar">
    <div class="brand">
        <img src="/static/logo.png.png">
        <span>ALMOX</span>
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
def login(request: Request, erro: str = ""):
    usuario_salvo = request.cookies.get("usuario_salvo", "")
    checked = "checked" if usuario_salvo else ""

    aviso_html = ""
    if erro == "1":
        aviso_html = """
<div class="login-alert">
    ⚠️ Usuário ou senha incorretos. Tente novamente.
</div>
"""

    corpo = f"""
<style>
.password-wrap {{
    position: relative;
    width: 100%;
}}
.password-wrap .field {{
    width: 100%;
    padding-right: 42px;
    box-sizing: border-box;
}}
.toggle-senha {{
    position: absolute;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    color: #8a8a8a;
    opacity: 0.7;
}}
.toggle-senha:hover {{ opacity: 1; }}
.toggle-senha svg {{ width: 20px; height: 20px; }}
.toggle-senha .icon-off {{ display: none; }}
.login-alert {{
    background: #fdecea;
    color: #b3261e;
    border: 1px solid #f5c2c0;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    margin-bottom: 14px;
    text-align: center;
}}
</style>
<div class="login-wrap">
    <div class="card login-card">
        <img src="/static/logo.png.png">
        <h2 class="login-title">Gestão de Requisições</h2>
        <span class="login-subtitle">Grupo Alvorada</span>
        {aviso_html}
        <form method="post" action="/login">
            <input class="field" name="usuario" placeholder="Usuário" autocomplete="off" value="{usuario_salvo}">
            <div class="password-wrap">
                <input class="field" id="senha" name="senha" type="password" placeholder="Senha">
                <button type="button" class="toggle-senha" onclick="alternarSenha()" aria-label="Mostrar senha">
                    <svg class="icon-on" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7Z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                    <svg class="icon-off" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 19c-7 0-11-7-11-7a20.3 20.3 0 0 1 4.22-5.19M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 7 11 7a20.29 20.29 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                </button>
            </div>
            <label class="remember-check">
                <input type="checkbox" name="lembrar" value="1" {checked}>
                Lembrar meu usuário
            </label>
            <button class="btn btn-primary btn-block" type="submit">Entrar</button>
        </form>
    </div>
</div>
<script>
function alternarSenha() {{
    const campo = document.getElementById('senha');
    const btn = document.querySelector('.toggle-senha');
    const mostrando = campo.type === 'text';
    campo.type = mostrando ? 'password' : 'text';
    btn.querySelector('.icon-on').style.display = mostrando ? '' : 'none';
    btn.querySelector('.icon-off').style.display = mostrando ? 'none' : '';
}}
</script>
"""
    return base_html("Login", corpo)


@app.post("/login")
def login_post(request: Request, usuario: str = Form(...), senha: str = Form(...), lembrar: str = Form(None)):
    if usuario in usuarios and usuarios[usuario]["senha"] == senha:
        request.session["user"] = usuario
        request.session["unidade"] = usuarios[usuario]["unidade"]
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

    # usuário ou senha incorretos: volta pro login com aviso
    return RedirectResponse("/?erro=1", status_code=303)


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
def materiais(request: Request, ok: str = "", erro: str = ""):
    if not request.session.get("user"):
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)
    tipo = usuarios.get(request.session["user"], {}).get("tipo", "setor")

    try:
        df = carregar_excel(unidade)
        cod_col, desc_col = pegar_colunas(df)
    except FileNotFoundError:
        return pagina_erro(
            f"Arquivo {arquivo_materiais_da_unidade(unidade)} não encontrado. "
            "Coloque a planilha na pasta do sistema."
        )
    except ValueError as e:
        return pagina_erro(str(e))

    aviso_html = ""
    if ok:
        aviso_html = f'<div class="form-alert form-alert-ok">✅ {ok}</div>'
    elif erro:
        aviso_html = f'<div class="form-alert form-alert-erro">⚠️ {erro}</div>'

    cabecalho = "".join(f"<th>{c}</th>" for c in df.columns)
    if tipo == "admin":
        cabecalho += "<th></th>"

    linhas = ""
    for _, r in df.iterrows():
        celulas = "".join(f"<td>{r[c]}</td>" for c in df.columns)
        if tipo == "admin":
            codigo_val = str(r[cod_col]).strip()
            celulas += f"""
<td>
    <form method="post" action="/materiais/excluir" onsubmit="return confirm('Excluir o material {codigo_val}?');" style="margin:0;">
        <input type="hidden" name="codigo" value="{codigo_val}">
        <button class="btn btn-icon btn-reject" type="submit">🗑️ Excluir</button>
    </form>
</td>
"""
        linhas += f"<tr>{celulas}</tr>"

    tabela = f'<table class="tbl"><tr>{cabecalho}</tr>{linhas}</table>'

    corpo = f"""
<style>
.form-alert {{
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    margin-bottom: 16px;
}}
.form-alert-ok {{
    background: #e8f5e9;
    color: #1b6e2b;
    border: 1px solid #bfe3c4;
}}
.form-alert-erro {{
    background: #fdecea;
    color: #b3261e;
    border: 1px solid #f5c2c0;
}}
</style>
{topbar(tipo)}
<div class="page">
    <span class="eyebrow">Catálogo · {nome_unidade(unidade)}</span>
    <h2>📦 Materiais</h2>
    <p class="page-sub">Consulta geral de itens disponíveis no almoxarifado.</p>
    {aviso_html}

    <div class="table-wrap">
        {tabela}
    </div>
</div>
"""
    return base_html("Materiais", corpo)


@app.post("/materiais/excluir")
def excluir_material(request: Request, codigo: str = Form(...)):
    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)
    arquivo = arquivo_materiais_da_unidade(unidade)

    from urllib.parse import quote
    try:
        ok, msg = remover_material(arquivo, codigo)
    except FileNotFoundError:
        return RedirectResponse(f"/materiais?erro=Arquivo+{arquivo}+não+encontrado.", status_code=303)

    if ok:
        return RedirectResponse(f"/materiais?ok={quote(msg)}", status_code=303)
    return RedirectResponse(f"/materiais?erro={quote(msg)}", status_code=303)


# =========================
# CADASTRAR MATERIAL (somente admin)
# =========================
@app.get("/materiais/cadastrar", response_class=HTMLResponse)
def cadastrar_material_form(request: Request, ok: str = "", erro: str = ""):
    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)

    aviso_html = ""
    if ok:
        aviso_html = f'<div class="form-alert form-alert-ok">✅ {ok}</div>'
    elif erro:
        aviso_html = f'<div class="form-alert form-alert-erro">⚠️ {erro}</div>'

    corpo = f"""
<style>
.form-alert {{
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    margin-bottom: 16px;
}}
.form-alert-ok {{
    background: #e8f5e9;
    color: #1b6e2b;
    border: 1px solid #bfe3c4;
}}
.form-alert-erro {{
    background: #fdecea;
    color: #b3261e;
    border: 1px solid #f5c2c0;
}}
</style>
<div class="admin-shell">
    {sidebar("cadastrar", unidade)}
    <div class="admin-content">
        <span class="eyebrow">Catálogo · {nome_unidade(unidade)}</span>
        <h2>➕ Cadastrar material</h2>
        <p class="page-sub">O material entra direto na planilha de materiais desta unidade.</p>

        <div class="card" style="padding:20px; max-width:480px;">
            {aviso_html}
            <form method="post" action="/materiais/cadastrar">
                <input class="field" name="codigo" placeholder="Código" required>
                <input class="field" name="descricao" placeholder="Descrição do material" required>
                <input class="field" name="unidade_medida" placeholder="Unidade (ex: UN, CX, KG)">
                <button class="btn btn-primary btn-block" type="submit">Cadastrar</button>
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
    unidade_medida: str = Form(""),
):
    if not request.session.get("user") or usuarios.get(request.session["user"], {}).get("tipo") != "admin":
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)
    arquivo = arquivo_materiais_da_unidade(unidade)

    if not codigo.strip() or not descricao.strip():
        return RedirectResponse("/materiais/cadastrar?erro=Preencha+código+e+descrição.", status_code=303)

    try:
        ok, msg = adicionar_material(arquivo, codigo, descricao, unidade_medida)
    except FileNotFoundError:
        return RedirectResponse(
            f"/materiais/cadastrar?erro=Arquivo+{arquivo}+não+encontrado.", status_code=303
        )

    from urllib.parse import quote
    if ok:
        return RedirectResponse(f"/materiais/cadastrar?ok={quote(msg)}", status_code=303)
    return RedirectResponse(f"/materiais/cadastrar?erro={quote(msg)}", status_code=303)


# =========================
# REQUISIÇÃO
# =========================
@app.get("/requisicao", response_class=HTMLResponse)
def req(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/")

    unidade = unidade_do_usuario(request)

    try:
        df = carregar_excel(unidade)
        cod, desc = pegar_colunas(df)
    except FileNotFoundError:
        return pagina_erro(f"Arquivo {arquivo_materiais_da_unidade(unidade)} não encontrado.")
    except ValueError as e:
        return pagina_erro(str(e))

    unidades_cols = [c for c in df.columns if "UNID" in c]
    col_un = unidades_cols[0] if unidades_cols else None

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
{topbar("setor")}
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

    try:
        df = carregar_excel(unidade)
        cod, desc = pegar_colunas(df)
    except FileNotFoundError:
        return pagina_erro(f"Arquivo {arquivo_materiais_da_unidade(unidade)} não encontrado.")
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
            unidade=unidade,
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
{topbar("setor")}
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

    tag_unidade = f'<span class="brand-tag">{nome_unidade(unidade)}</span>' if unidade else '<span class="brand-tag">Painel admin</span>'

    return f"""
<div class="sidebar">
    <div class="sidebar-logo">
        <img src="/static/logo.png.png">
    </div>
    {tag_unidade}
    {item("/painel", "📊 Dashboard", "dashboard")}
    {item("/relatorio", "📈 Relatório", "relatorio")}
    {item("/materiais", "📦 Materiais", "materiais")}
    {item("/materiais/cadastrar", "➕ Cadastrar material", "cadastrar")}
    <a class="nav-link logout" href="/logout">🚪 Sair</a>
</div>
"""


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
        # cada admin só vê as requisições da própria unidade
        todas = (
            db.query(Requisicao)
            .filter(Requisicao.unidade == unidade)
            .order_by(Requisicao.id.desc())
            .all()
        )
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
        <span class="eyebrow">Visão geral · {nome_unidade(unidade)}</span>
        <h2>📊 Dashboard de requisições</h2>
        <p class="page-sub">Acompanhe, atenda e recuse os pedidos dos setores da sua unidade.</p>

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
        # cada admin só vê o relatório da própria unidade
        todas = db.query(Requisicao).filter(Requisicao.unidade == unidade).all()
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
        <span class="eyebrow">Comparativo por período · {nome_unidade(unidade)}</span>
        <h2>📈 Relatório de requisições</h2>
        <p class="page-sub">Compare a quantidade de requisições feitas por cada setor da sua unidade no período selecionado.</p>

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
