import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import os
from io import BytesIO

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(
    page_title="Controle de Chips - Laerty",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# SENHA DE ACESSO (troque se quiser)
SENHA_CORRETA = "laerty2026"

DB_PATH = "chip_estoque.db"

def check_password():
    """Tela de login simples"""
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if st.session_state.autenticado:
        return True

    st.title("🔐 Controle de Chips - Acesso")
    st.write("Digite a senha para entrar no sistema")
    
    senha = st.text_input("Senha", type="password")
    
    if st.button("Entrar", type="primary"):
        if senha == SENHA_CORRETA:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta!")
    
    st.caption("Sistema de controle de estoque de chips • Equipe Laerty")
    return False

# ============================================================
# BANCO DE DADOS
# ============================================================
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    # Tabela de chips (estoque unitário por ICCID/barcode)
    c.execute('''
        CREATE TABLE IF NOT EXISTS chips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            iccid TEXT,
            produto TEXT,
            status TEXT DEFAULT 'disponivel',  -- disponivel, com_promotor, vendido, defeito, perdido
            promotor_atual TEXT,
            data_entrada TIMESTAMP,
            data_ultima_mov TIMESTAMP,
            observacao TEXT
        )
    ''')
    
    # Tabela de movimentos (histórico completo)
    c.execute('''
        CREATE TABLE IF NOT EXISTS movimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,
            tipo TEXT NOT NULL,  -- entrada, entrega, venda, defeito, remanejamento, devolucao
            promotor_origem TEXT,
            promotor_destino TEXT,
            produto TEXT,
            quantidade INTEGER DEFAULT 1,
            data_mov TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario TEXT,
            observacao TEXT
        )
    ''')
    
    # Tabela de promotores
    c.execute('''
        CREATE TABLE IF NOT EXISTS promotores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            cpf TEXT,
            ativo INTEGER DEFAULT 1,
            telefone TEXT
        )
    ''')
    
    # Tabela de produtos
    c.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            preco REAL DEFAULT 0,
            ativo INTEGER DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()

def seed_data():
    """Popula promotores e produtos padrão da equipe Laerty"""
    conn = get_conn()
    c = conn.cursor()
    
    promotores = [
        "JOAO PAULO MEDEIROS DE ARAUJO",
        "CEZIMAR ANDRADE DA COSTA FILHO",
        "FRANCILIANO CAMILO DE OLIVEIRA",
        "KARLA CAROLINE ANDRADE MARTINS",
        "YASMIM MARIANA DA SILVA PEREIRA",
        "LIANA TASSIA ANDRADE DA CRUZ",
        "MARIA DA PIEDADE FERREIRA DOS SANTOS",
        "RUTILENE FERREIRA BARBOSA",
        "VILIANE KATIANE BEZERRA DE SOUZA",
        "SERGIO AUGUSTO DA SILVA",
        "ANDREZA DIAS",
        "JENNIFER MAYSE DA SILVA GALVAO FERREIRA",
    ]
    
    for p in promotores:
        c.execute("INSERT OR IGNORE INTO promotores (nome) VALUES (?)", (p,))
    
    produtos = [
        ("CHIP COMBO OUT - 18", 18.0),
        ("CHIP COMBO OUT - 15", 15.0),
        ("CHIP COMBO OUT - 13", 13.0),
        ("TESTE ABILITY - 10", 10.0),
        ("TIM PRÉ BRUTO", 0.0),
        ("CHIP PORTABILIDADE NE - 13", 13.0),
    ]
    
    for nome, preco in produtos:
        c.execute("INSERT OR IGNORE INTO produtos (nome, preco) VALUES (?, ?)", (nome, preco))
    
    conn.commit()
    conn.close()

# ============================================================
# FUNÇÕES DE NEGÓCIO
# ============================================================
def registrar_entrada(barcode, produto, observacao=""):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO chips (barcode, produto, status, data_entrada, data_ultima_mov, observacao)
            VALUES (?, ?, 'disponivel', ?, ?, ?)
        ''', (barcode, produto, datetime.now(), datetime.now(), observacao))
        
        c.execute('''
            INSERT INTO movimentos (barcode, tipo, produto, observacao, usuario)
            VALUES (?, 'entrada', ?, ?, 'sistema')
        ''', (barcode, produto, observacao))
        
        conn.commit()
        return True, "Chip registrado com sucesso!"
    except sqlite3.IntegrityError:
        return False, "❌ Este código de barras já existe no sistema!"
    finally:
        conn.close()

def entregar_chip(barcode, promotor, observacao=""):
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("SELECT status, produto, promotor_atual FROM chips WHERE barcode = ?", (barcode,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return False, "❌ Código de barras não encontrado!"
    
    status, produto, promotor_atual = row
    
    if status == 'vendido':
        conn.close()
        return False, "❌ Este chip já foi vendido!"
    if status == 'defeito':
        conn.close()
        return False, "❌ Este chip está marcado como defeito!"
    
    c.execute('''
        UPDATE chips 
        SET status = 'com_promotor', promotor_atual = ?, data_ultima_mov = ?
        WHERE barcode = ?
    ''', (promotor, datetime.now(), barcode))
    
    c.execute('''
        INSERT INTO movimentos (barcode, tipo, promotor_origem, promotor_destino, produto, observacao, usuario)
        VALUES (?, 'entrega', ?, ?, ?, ?, 'sistema')
    ''', (barcode, promotor_atual or 'ESTOQUE', promotor, produto, observacao))
    
    conn.commit()
    conn.close()
    return True, f"✅ Chip entregue para {promotor}"

def registrar_venda(barcode, observacao=""):
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("SELECT status, produto, promotor_atual FROM chips WHERE barcode = ?", (barcode,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return False, "❌ Código de barras não encontrado!"
    
    status, produto, promotor = row
    
    if status != 'com_promotor':
        conn.close()
        return False, f"❌ Chip não está com promotor (status atual: {status})"
    
    c.execute('''
        UPDATE chips 
        SET status = 'vendido', data_ultima_mov = ?
        WHERE barcode = ?
    ''', (datetime.now(), barcode))
    
    c.execute('''
        INSERT INTO movimentos (barcode, tipo, promotor_origem, produto, observacao, usuario)
        VALUES (?, 'venda', ?, ?, ?, 'sistema')
    ''', (barcode, promotor, produto, observacao))
    
    conn.commit()
    conn.close()
    return True, f"✅ Venda registrada! Promotor: {promotor}"

def registrar_defeito(barcode, observacao=""):
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("SELECT status, produto, promotor_atual FROM chips WHERE barcode = ?", (barcode,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return False, "❌ Código de barras não encontrado!"
    
    status, produto, promotor = row
    
    c.execute('''
        UPDATE chips 
        SET status = 'defeito', data_ultima_mov = ?
        WHERE barcode = ?
    ''', (datetime.now(), barcode))
    
    c.execute('''
        INSERT INTO movimentos (barcode, tipo, promotor_origem, produto, observacao, usuario)
        VALUES (?, 'defeito', ?, ?, ?, 'sistema')
    ''', (barcode, promotor or 'ESTOQUE', produto, observacao))
    
    conn.commit()
    conn.close()
    return True, "✅ Defeito registrado!"

def remanejar(barcode, promotor_destino, observacao=""):
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("SELECT status, produto, promotor_atual FROM chips WHERE barcode = ?", (barcode,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return False, "❌ Código de barras não encontrado!"
    
    status, produto, promotor_origem = row
    
    if status != 'com_promotor':
        conn.close()
        return False, f"❌ Chip não está com promotor (status: {status})"
    
    c.execute('''
        UPDATE chips 
        SET promotor_atual = ?, data_ultima_mov = ?
        WHERE barcode = ?
    ''', (promotor_destino, datetime.now(), barcode))
    
    c.execute('''
        INSERT INTO movimentos (barcode, tipo, promotor_origem, promotor_destino, produto, observacao, usuario)
        VALUES (?, 'remanejamento', ?, ?, ?, ?, 'sistema')
    ''', (barcode, promotor_origem, promotor_destino, produto, observacao))
    
    conn.commit()
    conn.close()
    return True, f"✅ Remanejado de {promotor_origem} para {promotor_destino}"

def devolver_ao_estoque(barcode, observacao=""):
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("SELECT status, produto, promotor_atual FROM chips WHERE barcode = ?", (barcode,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return False, "❌ Código de barras não encontrado!"
    
    status, produto, promotor = row
    
    c.execute('''
        UPDATE chips 
        SET status = 'disponivel', promotor_atual = NULL, data_ultima_mov = ?
        WHERE barcode = ?
    ''', (datetime.now(), barcode))
    
    c.execute('''
        INSERT INTO movimentos (barcode, tipo, promotor_origem, promotor_destino, produto, observacao, usuario)
        VALUES (?, 'devolucao', ?, 'ESTOQUE', ?, ?, 'sistema')
    ''', (barcode, promotor or '-', produto, observacao))
    
    conn.commit()
    conn.close()
    return True, "✅ Chip devolvido ao estoque central!"

# ============================================================
# CONSULTAS
# ============================================================
def get_estoque_resumo():
    conn = get_conn()
    df = pd.read_sql_query('''
        SELECT 
            COALESCE(promotor_atual, 'ESTOQUE CENTRAL') as Local,
            produto,
            status,
            COUNT(*) as Qtd
        FROM chips
        GROUP BY 1, 2, 3
        ORDER BY 1, 2
    ''', conn)
    conn.close()
    return df

def get_estoque_por_promotor():
    conn = get_conn()
    df = pd.read_sql_query('''
        SELECT 
            promotor_atual as Promotor,
            produto as Produto,
            COUNT(*) as Quantidade
        FROM chips
        WHERE status = 'com_promotor' AND promotor_atual IS NOT NULL
        GROUP BY promotor_atual, produto
        ORDER BY promotor_atual, produto
    ''', conn)
    conn.close()
    return df

def get_historico(limit=100):
    conn = get_conn()
    df = pd.read_sql_query(f'''
        SELECT 
            data_mov as Data,
            barcode as Código,
            tipo as Tipo,
            promotor_origem as De,
            promotor_destino as Para,
            produto as Produto,
            observacao as Obs
        FROM movimentos
        ORDER BY data_mov DESC
        LIMIT {limit}
    ''', conn)
    conn.close()
    return df

def get_promotores():
    conn = get_conn()
    df = pd.read_sql_query("SELECT nome FROM promotores WHERE ativo = 1 ORDER BY nome", conn)
    conn.close()
    return df['nome'].tolist()

def get_produtos():
    conn = get_conn()
    df = pd.read_sql_query("SELECT nome FROM produtos WHERE ativo = 1 ORDER BY nome", conn)
    conn.close()
    return df['nome'].tolist()

def buscar_chip(barcode):
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM chips WHERE barcode = ?", conn, params=(barcode,))
    conn.close()
    return df

# ============================================================
# INTERFACE
# ============================================================
def main():
    init_db()
    seed_data()
    
    st.title("📱 Controle de Chips & Estoque")
    st.caption("Equipe Laerty • SmartRader Integration • Código de Barras")
    
    menu = st.sidebar.radio(
        "Menu Principal",
        [
            "🏠 Dashboard",
            "📥 Entrada de Chips",
            "🚚 Entrega para Promotor",
            "💰 Registrar Venda",
            "🔄 Remanejamento",
            "⚠️ Defeito / Devolução",
            "📊 Estoque por Promotor",
            "📜 Histórico",
            "📁 Importar SmartRader",
            "⚙️ Configurações"
        ]
    )
    
    # ========== DASHBOARD ==========
    if menu == "🏠 Dashboard":
        st.header("Dashboard Geral")
        
        col1, col2, col3, col4 = st.columns(4)
        
        conn = get_conn()
        total = pd.read_sql_query("SELECT COUNT(*) as t FROM chips", conn).iloc[0]['t']
        disponivel = pd.read_sql_query("SELECT COUNT(*) as t FROM chips WHERE status='disponivel'", conn).iloc[0]['t']
        com_promotor = pd.read_sql_query("SELECT COUNT(*) as t FROM chips WHERE status='com_promotor'", conn).iloc[0]['t']
        vendidos = pd.read_sql_query("SELECT COUNT(*) as t FROM chips WHERE status='vendido'", conn).iloc[0]['t']
        defeitos = pd.read_sql_query("SELECT COUNT(*) as t FROM chips WHERE status='defeito'", conn).iloc[0]['t']
        conn.close()
        
        col1.metric("Total de Chips", total)
        col2.metric("Disponíveis (Estoque)", disponivel)
        col3.metric("Com Promotores", com_promotor)
        col4.metric("Vendidos", vendidos)
        
        st.subheader("Resumo por Status")
        df_resumo = get_estoque_resumo()
        if not df_resumo.empty:
            st.dataframe(df_resumo, use_container_width=True)
        else:
            st.info("Nenhum chip cadastrado ainda.")
    
    # ========== ENTRADA ==========
    elif menu == "📥 Entrada de Chips":
        st.header("📥 Entrada de Chips no Estoque")
        st.info("Use o leitor de código de barras (ou digite). O leitor geralmente envia o código + Enter automaticamente.")
        
        with st.form("form_entrada", clear_on_submit=True):
            barcode = st.text_input("Código de Barras / ICCID", placeholder="Aponte o leitor aqui...", key="ent_barcode")
            produto = st.selectbox("Produto", get_produtos())
            obs = st.text_input("Observação (opcional)")
            submitted = st.form_submit_button("Registrar Entrada", type="primary")
            
            if submitted and barcode:
                ok, msg = registrar_entrada(barcode.strip(), produto, obs)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # ========== ENTREGA ==========
   elif menu == "🚚 Entrega para Promotor":
        st.header("🚚 Entrega de Chip para Promotor")

        # Scanner de código de barras com câmera
        st.subheader("📷 Ler código de barras com câmera")

        scanner_html = """
        <div>
            <button onclick="startScanner()" style="background-color:#ff4b4b;color:white;padding:10px 20px;border:none;border-radius:8px;font-size:16px;">
                📷 Abrir Câmera e Ler Código
            </button>
            <div id="scanner-container" style="margin-top:15px;"></div>
            <script src="https://cdn.jsdelivr.net/npm/quagga@0.12.1/dist/quagga.min.js"></script>
            <script>
                function startScanner() {
                    const container = document.getElementById('scanner-container');
                    container.innerHTML = '<div id="interactive" style="width:100%;max-width:400px;height:300px;border:2px solid #ccc;"></div>';
                    
                    Quagga.init({
                        inputStream: {
                            name: "Live",
                            type: "LiveStream",
                            target: document.querySelector('#interactive'),
                            constraints: {
                                facingMode: "environment"
                            }
                        },
                        decoder: {
                            readers: ["code_128_reader", "ean_reader", "ean_8_reader"]
                        }
                    }, function(err) {
                        if (err) {
                            console.log(err);
                            return;
                        }
                        Quagga.start();
                    });

                    Quagga.onDetected(function(result) {
                        const code = result.codeResult.code;
                        Quagga.stop();
                        container.innerHTML = '';
                        
                        // Envia o valor para o Streamlit
                        window.parent.postMessage({
                            type: "streamlit:setComponentValue",
                            value: code
                        }, "*");
                    });
                }
            </script>
        </div>
        """

        barcode_from_camera = st.components.v1.html(scanner_html, height=400)

        # Campo de texto (pode ser preenchido manualmente ou pela câmera)
        barcode = st.text_input(
            "ICCID / Código de Barras",
            value=barcode_from_camera if barcode_from_camera else "",
            key="barcode_entrega"
        )

        promotor = st.selectbox("Promotor que vai receber", get_promotores())

        if st.button("Confirmar Entrega", type="primary"):
            if barcode:
                ok, msg = entregar_chip(barcode.strip(), promotor)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Por favor, leia ou digite o código de barras.")
    
    # ========== VENDA ==========
    elif menu == "💰 Registrar Venda":
        st.header("💰 Registrar Venda (Baixa de Estoque)")
        st.caption("Quando o promotor vende, baixa o chip do estoque dele.")
        
        with st.form("form_venda", clear_on_submit=True):
            barcode = st.text_input("Código de Barras vendido", placeholder="Aponte o leitor...")
            obs = st.text_input("Observação / Nº da venda")
            submitted = st.form_submit_button("Confirmar Venda", type="primary")
            
            if submitted and barcode:
                ok, msg = registrar_venda(barcode.strip(), obs)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # ========== REMANEJAMENTO ==========
    elif menu == "🔄 Remanejamento":
        st.header("🔄 Remanejamento entre Promotores")
        
        with st.form("form_remanejo", clear_on_submit=True):
            barcode = st.text_input("Código de Barras", placeholder="Aponte o leitor...")
            promotor_destino = st.selectbox("Promotor Destino", get_promotores())
            obs = st.text_input("Motivo do remanejamento")
            submitted = st.form_submit_button("Remanejar", type="primary")
            
            if submitted and barcode:
                ok, msg = remanejar(barcode.strip(), promotor_destino, obs)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
    
    # ========== DEFEITO / DEVOLUÇÃO ==========
    elif menu == "⚠️ Defeito / Devolução":
        st.header("⚠️ Defeito ou Devolução ao Estoque")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Marcar como Defeito")
            with st.form("form_defeito", clear_on_submit=True):
                barcode = st.text_input("Código de Barras com defeito")
                obs = st.text_input("Descrição do defeito")
                if st.form_submit_button("Registrar Defeito", type="primary"):
                    if barcode:
                        ok, msg = registrar_defeito(barcode.strip(), obs)
                        if ok: st.success(msg)
                        else: st.error(msg)
        
        with col2:
            st.subheader("Devolver ao Estoque Central")
            with st.form("form_devolucao", clear_on_submit=True):
                barcode2 = st.text_input("Código de Barras a devolver")
                obs2 = st.text_input("Motivo da devolução")
                if st.form_submit_button("Devolver ao Estoque"):
                    if barcode2:
                        ok, msg = devolver_ao_estoque(barcode2.strip(), obs2)
                        if ok: st.success(msg)
                        else: st.error(msg)
    
    # ========== ESTOQUE POR PROMOTOR ==========
    elif menu == "📊 Estoque por Promotor":
        st.header("📊 Estoque Atual por Promotor")
        
        df = get_estoque_por_promotor()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            # Pivot
            st.subheader("Visão em Tabela (Pivot)")
            pivot = df.pivot_table(index='Promotor', columns='Produto', values='Quantidade', fill_value=0, aggfunc='sum')
            st.dataframe(pivot, use_container_width=True)
            
            # Total por promotor
            st.subheader("Total de chips por promotor")
            total_prom = df.groupby('Promotor')['Quantidade'].sum().sort_values(ascending=False)
            st.bar_chart(total_prom)
        else:
            st.info("Nenhum chip com promotores no momento.")
    
    # ========== HISTÓRICO ==========
    elif menu == "📜 Histórico":
        st.header("📜 Histórico de Movimentações")
        limit = st.slider("Quantidade de registros", 50, 500, 100)
        df = get_historico(limit)
        st.dataframe(df, use_container_width=True)
        
        # Download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Baixar CSV", csv, "historico_chips.csv", "text/csv")
    
 
       # ========== IMPORTAR SMARTRADER ==========
    elif menu == "📁 Importar SmartRader":
        st.header("📁 Importar Planilha de Vendas (SmartRader)")
        st.info("Faça upload da planilha de vendas exportada do SmartRader. O sistema vai dar baixa automática nos chips vendidos (se o ICCID estiver cadastrado).")

        uploaded = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx", "xls"])

        if uploaded:
            try:
                # === CORREÇÃO PRINCIPAL ===
                df = pd.read_excel(uploaded, dtype=str)

                st.write("Pré-visualização dos dados:")
                st.dataframe(df.head(10))

                colunas = df.columns.tolist()

                col_iccid = st.selectbox(
                    "Selecione a coluna que contém o **ICCID / Código de Barras**",
                    colunas
                )

                col_status = st.selectbox(
                    "Selecione a coluna que contém o **Status** (Vendido / Aprovado)",
                    colunas
                )

                if st.button("Processar Vendas e Dar Baixa", type="primary"):
                    processados = 0
                    nao_encontrados = 0
                    erros = []

                    for _, row in df.iterrows():
                        status = str(row[col_status]).strip().upper()
                        if status not in ['VENDIDO', 'APROVADO']:
                            continue

                        barcode = str(row[col_iccid]).strip()
                        if not barcode or barcode == 'nan' or barcode == '':
                            continue

                        ok, msg = registrar_venda(barcode, f"Importado via SmartRader")
                        if ok:
                            processados += 1
                        else:
                            nao_encontrados += 1
                            erros.append(f"{barcode}: {msg}")

                    st.success(f"✅ {processados} vendas processadas com sucesso!")
                    if nao_encontrados > 0:
                        st.warning(f"⚠️ {nao_encontrados} chips não foram encontrados no estoque.")
                        with st.expander("Ver detalhes dos erros"):
                            for e in erros[:30]:
                                st.text(e)

            except Exception as e:
                st.error(f"Erro ao processar o arquivo: {e}")
    # ========== CONFIGURAÇÕES ==========
    elif menu == "⚙️ Configurações":
        st.header("⚙️ Configurações")
        
        tab1, tab2 = st.tabs(["Promotores", "Produtos"])
        
        with tab1:
            st.subheader("Lista de Promotores")
            st.write(get_promotores())
            
            novo = st.text_input("Adicionar novo promotor")
            if st.button("Adicionar Promotor") and novo:
                conn = get_conn()
                try:
                    conn.execute("INSERT INTO promotores (nome) VALUES (?)", (novo.upper().strip(),))
                    conn.commit()
                    st.success("Promotor adicionado!")
                    st.rerun()
                except:
                    st.error("Já existe ou erro")
                finally:
                    conn.close()
        
        with tab2:
            st.subheader("Lista de Produtos")
            st.write(get_produtos())
            
            col_a, col_b = st.columns(2)
            novo_prod = col_a.text_input("Novo produto")
            novo_preco = col_b.number_input("Preço", min_value=0.0, value=0.0)
            if st.button("Adicionar Produto") and novo_prod:
                conn = get_conn()
                try:
                    conn.execute("INSERT INTO produtos (nome, preco) VALUES (?, ?)", (novo_prod.strip(), novo_preco))
                    conn.commit()
                    st.success("Produto adicionado!")
                    st.rerun()
                except:
                    st.error("Já existe")
                finally:
                    conn.close()
        
        st.divider()
        st.subheader("⚠️ Zona de Perigo")
        if st.button("Zerar todo o banco de dados (cuidado!)", type="secondary"):
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
                init_db()
                seed_data()
                st.success("Banco zerado e recriado!")
                st.rerun()

if __name__ == "__main__":
    if check_password():
        main()
