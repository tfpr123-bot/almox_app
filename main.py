from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
import pandas as pd
import unicodedata
from datetime import datetime, date, timedelta
import calendar
import os
import json

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
        <link rel="stylesheet" href="/static/style.css">
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
def login():
    corpo = f"""
    <div class="login-wrap">
        <div class="card login-card">
            <img src="/static/logo.png.png">
            <span class="eyebrow">Controle de almoxarifado</span>
            <h2>Entrar no sistema</h2>

            <form method="post" action="/login">
                <input class="field" name="usuario" placeholder="Usuário" autocomplete="off">
                <input class="field" name="senha" type="password" placeholder="Senha">
                <button class="btn btn-primary btn-block" type="submit">Entrar</button>
            </form>
        </div>
    </div>
    """
    return base_html("Login", corpo)

@app.post("/login")
def login_post(request: Request, usuario: str = Form(...), senha: str = Form(...)):
    if usuario in usuarios and usuarios[usuario]["senha"] == senha:
        request.session["user"] = usuario

        if usuarios[usuario]["tipo"] == "admin":
            return RedirectResponse("/painel", status_code=303)
        else:
            return RedirectResponse("/menu", status_code=303)

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

    try:
        df = carregar_excel()
    except FileNotFoundError:
        return pagina_erro("Arquivo materiais.xlsx não encontrado. Coloque a planilha na pasta do sistema.")
    except ValueError as e:
        return pagina_erro(str(e))

    tabela = df.to_html(index=False, classes="tbl", border=0)

    corpo = f"""
    {topbar(usuarios.get(request.session["user"], {}).get("tipo", "setor"))}
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

    linhas = ""
    tem_linha = False
    for r in requisicoes:
        if r["user"] == request.session["user"]:
            tem_linha = True
            linhas += f"""
            <tr>
                <td class="mono">#{r['id']}</td>
                <td class="mono">{r['codigo']}</td>
                <td>{r['descricao']}</td>
                <td>{r['quantidade']}</td>
                <td>{r['data']}</td>
                <td>{badge(r['status'])}</td>
            </tr>
            """

    if not tem_linha:
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

def sidebar(ativo="dashboard"):
    def item(href, label, chave):
        cls = "nav-link active" if ativo == chave else "nav-link"
        return f'<a class="{cls}" href="{href}">{label}</a>'
    return f"""
    <div class="sidebar">
        <img src="/static/logo.png.png">
        <span class="brand-tag">Painel admin</span>
        {item("/painel", "📊 Dashboard", "dashboard")}
        {item("/relatorio", "📈 Relatório", "relatorio")}
        {item("/materiais", "📦 Materiais", "materiais")}
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

    total = len(requisicoes)
    pend = len([r for r in requisicoes if r["status"] == "PENDENTE"])
    ok = len([r for r in requisicoes if r["status"] == "ATENDIDO"])
    neg = len([r for r in requisicoes if r["status"] == "RECUSADO"])

    lista = requisicoes
    if filtro != "TODOS":
        lista = [r for r in requisicoes if r["status"] == filtro]

    def chip(valor, label):
        ativo = "active" if filtro == valor else ""
        return f'<a class="filter-chip {ativo}" href="/painel?filtro={valor}">{label}</a>'

    linhas = ""
    for r in lista:
        linhas += f"""
        <tr>
            <td class="mono">#{r['id']}</td>
            <td>{r['user']}</td>
            <td class="mono">{r['codigo']}</td>
            <td>{r['descricao']}</td>
            <td>{r['quantidade']}</td>
            <td>{badge(r['status'])}</td>
            <td>
                <div class="row-actions">
                    <a class="btn btn-icon btn-approve" href="/atender/{r['id']}">✔️ Atender</a>
                    <a class="btn btn-icon btn-reject" href="/recusar/{r['id']}">❌ Recusar</a>
                </div>
            </td>
            <td><a class="btn btn-icon btn-print" href="/imprimir/{r['id']}">🖨️</a></td>
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
        {sidebar("dashboard")}

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

    filtradas = []
    for r in requisicoes:
        d = parse_data_req(r.get("data"))
        if d and inicio_d <= d <= fim_d:
            filtradas.append(r)

    resumo = {}
    for r in filtradas:
        setor = r["user"]
        if setor not in resumo:
            resumo[setor] = {"requisicoes": 0, "itens": 0}
        resumo[setor]["requisicoes"] += 1
        resumo[setor]["itens"] += int(r.get("quantidade") or 0)

    setores_ordenados = sorted(resumo.items(), key=lambda x: x[1]["requisicoes"], reverse=True)
    labels = [s for s, _ in setores_ordenados]
    valores_req = [v["requisicoes"] for _, v in setores_ordenados]
    valores_itens = [v["itens"] for _, v in setores_ordenados]

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
        {sidebar("relatorio")}

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
        const dadosItens = {valores_itens!r};
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
                            maxBarThickness: 42
                        }},
                        {{
                            label: 'Itens solicitados',
                            data: dadosItens,
                            backgroundColor: '#1E2128',
                            borderRadius: 6,
                            maxBarThickness: 42
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ position: 'top', labels: {{ font: {{ family: 'Inter' }} }} }}
                    }},
                    scales: {{
                        y: {{ beginAtZero: true, ticks: {{ precision: 0 }} }}
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

    req = None
    for r in requisicoes:
        if r["id"] == id:
            req = r
            break

    if not req:
        return pagina_erro("Requisição não encontrada.")

    status_classe = req["status"].lower()

    corpo = f"""
    <div class="ticket">
        <span class="stamp {status_classe}">{req['status']}</span>
        <span class="eyebrow">Ficha de requisição</span>
        <h2>REQUISIÇÃO DE MATERIAL</h2>

        <div class="row"><span class="k">ID</span><span class="v mono">#{req['id']}</span></div>
        <div class="row"><span class="k">Setor</span><span class="v">{req['user']}</span></div>
        <div class="row"><span class="k">Data</span><span class="v">{req['data']}</span></div>
        <div class="row"><span class="k">Código</span><span class="v mono">{req['codigo']}</span></div>
        <div class="row"><span class="k">Material</span><span class="v">{req['descricao']}</span></div>
        <div class="row"><span class="k">Quantidade</span><span class="v">{req['quantidade']}</span></div>

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
