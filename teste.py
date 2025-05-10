import streamlit as st
import sqlite3
from datetime import time, datetime, date, timedelta
import calendar
import os
from pathlib import Path
from PIL import Image

# CONFIG INICIAL
st.set_page_config(page_title="Casa de Repouso", page_icon="🏥", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    :root {
        --primary: #4a6fa5;
        --secondary: #166088;
        --accent: #4fc3f7;
        --background: #f5f9ff;
        --card: #ffffff;
    }
    
    .main {
        background-color: var(--background);
    }
    
    .titulo {
        font-size: 2.5rem;
        font-weight: bold;
        color: var(--secondary);
        margin-bottom: 1.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid var(--accent);
    }
    
    .bloco {
        background-color: var(--card);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    
    .bloco:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.12);
    }
    
    .status-tomou {
        color: #2e7d32;
        font-weight: bold;
        background-color: #e8f5e9;
        padding: 0.3rem 0.6rem;
        border-radius: 20px;
        display: inline-block;
    }
    
    .status-nao-tomou {
        color: #c62828;
        font-weight: bold;
        background-color: #ffebee;
        padding: 0.3rem 0.6rem;
        border-radius: 20px;
        display: inline-block;
    }
    
    .stButton>button {
        background-color: var(--primary);
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        background-color: var(--secondary);
        transform: scale(1.02);
    }
    
    .paciente-card {
        border-left: 4px solid var(--primary);
        padding-left: 1rem;
        margin-bottom: 1rem;
    }
    
    .dia-calendario {
        padding: 0.5rem;
        min-height: 80px;
        border: 1px solid #eee;
    }
    
    .dia-atual {
        background-color: #e3f2fd;
        font-weight: bold;
    }
    
    .com-medicamento {
        background-color: #e8f5e9;
    }
    </style>
""", unsafe_allow_html=True)

# --- GERENCIAMENTO DO BANCO DE DADOS ---
def criar_conexao():
    """Cria e retorna uma conexão com o banco de dados"""
    try:
        # Garante que o diretório existe
        Path('data').mkdir(exist_ok=True)
        
        # Cria o arquivo do banco de dados se não existir
        db_path = Path('data/pacientes.db')
        if not db_path.exists():
            db_path.touch()
            
        conn = sqlite3.connect('data/pacientes.db', check_same_thread=False)
        
        # Configura para garantir que as chaves estrangeiras são respeitadas
        conn.execute("PRAGMA foreign_keys = ON")
        
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {str(e)}")
        return None

def inicializar_tabelas(conn):
    """Cria as tabelas necessárias se não existirem"""
    if conn is None:
        return
        
    try:
        c = conn.cursor()
        
        # Verifica se a tabela de pacientes já existe
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pacientes'")
        if not c.fetchone():
            # Tabela de pacientes
            c.execute('''CREATE TABLE pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                idade INTEGER,
                condicao TEXT,
                data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
            )''')
            
            # Tabela de medicamentos
            c.execute('''CREATE TABLE medicamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER NOT NULL,
                medicamento TEXT NOT NULL,
                horario TEXT NOT NULL,
                data TEXT NOT NULL,
                tomou INTEGER DEFAULT 0,
                observacoes TEXT,
                FOREIGN KEY(paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE
            )''')
            
            # Tabela de calendário
            c.execute('''CREATE TABLE calendario_medicamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medicamento_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                status TEXT CHECK(status IN ("pendente", "tomado", "nao_tomado", "adiado")),
                observacoes TEXT,
                FOREIGN KEY(medicamento_id) REFERENCES medicamentos(id) ON DELETE CASCADE
            )''')
            
            # Adiciona alguns dados de exemplo
            c.execute("INSERT INTO pacientes (nome, idade, condicao) VALUES (?, ?, ?)", 
                     ("Maria da Silva", 78, "Hipertensão, Diabetes"))
            c.execute("INSERT INTO pacientes (nome, idade, condicao) VALUES (?, ?, ?)", 
                     ("João Oliveira", 82, "Demência moderada"))
            
            # Medicamentos de exemplo
            hoje = date.today().strftime("%Y-%m-%d")
            amanha = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
            
            c.execute("""INSERT INTO medicamentos 
                        (paciente_id, medicamento, horario, data, observacoes) 
                        VALUES (?, ?, ?, ?, ?)""", 
                     (1, "Captopril 25mg", "08:00", hoje, "Tomar antes do café"))
            c.execute("""INSERT INTO medicamentos 
                        (paciente_id, medicamento, horario, data, observacoes) 
                        VALUES (?, ?, ?, ?, ?)""", 
                     (1, "Metformina 850mg", "12:00", hoje, "Tomar após almoço"))
            c.execute("""INSERT INTO medicamentos 
                        (paciente_id, medicamento, horario, data, observacoes) 
                        VALUES (?, ?, ?, ?, ?)""", 
                     (2, "Donepezila 10mg", "09:00", hoje, "Com leite"))
            
            conn.commit()
    except sqlite3.Error as e:
        st.error(f"Erro ao criar tabelas: {e}")

# --- FUNÇÕES PARA PACIENTES ---
def adicionar_paciente(conn, nome, idade, condicao):
    """Adiciona um novo paciente ao banco de dados"""
    if conn is None:
        st.error("Sem conexão com o banco de dados")
        return False
        
    try:
        if not nome.strip():
            st.error("O nome não pode estar vazio")
            return False
        if idade <= 0:
            st.error("Idade inválida")
            return False
            
        c = conn.cursor()
        c.execute("INSERT INTO pacientes (nome, idade, condicao) VALUES (?, ?, ?)", 
                 (nome.strip(), int(idade), condicao.strip()))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao adicionar paciente: {e}")
        return False

def listar_pacientes(conn):
    """Retorna todos os pacientes cadastrados"""
    if conn is None:
        return []
        
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM pacientes ORDER BY nome")
        return c.fetchall()
    except sqlite3.Error as e:
        st.error(f"Erro ao listar pacientes: {e}")
        return []

def atualizar_paciente(conn, id_paciente, nome, idade, condicao):
    """Atualiza os dados de um paciente existente"""
    if conn is None:
        st.error("Sem conexão com o banco de dados")
        return False
        
    try:
        c = conn.cursor()
        c.execute("UPDATE pacientes SET nome=?, idade=?, condicao=? WHERE id=?", 
                 (nome.strip(), int(idade), condicao.strip(), id_paciente))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao atualizar paciente: {e}")
        return False

def remover_paciente(conn, id_paciente):
    """Remove um paciente do banco de dados"""
    if conn is None:
        st.error("Sem conexão com o banco de dados")
        return False
        
    try:
        c = conn.cursor()
        c.execute("DELETE FROM pacientes WHERE id=?", (id_paciente,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao remover paciente: {e}")
        return False

# --- FUNÇÕES PARA MEDICAMENTOS ---
def adicionar_medicamento(conn, paciente_id, medicamento, horario, data, observacoes):
    """Adiciona um novo medicamento para um paciente"""
    if conn is None:
        st.error("Sem conexão com o banco de dados")
        return False
        
    try:
        if not medicamento.strip():
            st.error("O nome do medicamento não pode estar vazio")
            return False
            
        c = conn.cursor()
        c.execute("""INSERT INTO medicamentos 
                    (paciente_id, medicamento, horario, data, observacoes) 
                    VALUES (?, ?, ?, ?, ?)""", 
                 (paciente_id, medicamento.strip(), horario, data, observacoes.strip()))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao adicionar medicamento: {e}")
        return False

def listar_medicamentos_hoje(conn):
    """Retorna os medicamentos para o dia atual"""
    if conn is None:
        return []
        
    try:
        c = conn.cursor()
        hoje = date.today().strftime("%Y-%m-%d")
        c.execute("""SELECT m.id, p.nome, m.medicamento, m.horario, m.tomou, m.observacoes 
                     FROM medicamentos m
                     JOIN pacientes p ON m.paciente_id = p.id
                     WHERE m.data = ?
                     ORDER BY m.horario""", (hoje,))
        return c.fetchall()
    except sqlite3.Error as e:
        st.error(f"Erro ao listar medicamentos: {e}")
        return []

def listar_medicamentos_por_data(conn, data):
    """Retorna os medicamentos para uma data específica"""
    if conn is None:
        return []
        
    try:
        c = conn.cursor()
        c.execute("""SELECT m.id, p.nome, m.medicamento, m.horario, m.tomou, m.observacoes 
                     FROM medicamentos m
                     JOIN pacientes p ON m.paciente_id = p.id
                     WHERE m.data = ?
                     ORDER BY m.horario""", (data,))
        return c.fetchall()
    except sqlite3.Error as e:
        st.error(f"Erro ao listar medicamentos: {e}")
        return []

def atualizar_status_medicamento(conn, id_medicamento, status):
    """Atualiza o status de um medicamento (1 = tomou, 0 = não tomou)"""
    if conn is None:
        st.error("Sem conexão com o banco de dados")
        return False
        
    try:
        c = conn.cursor()
        c.execute("UPDATE medicamentos SET tomou=? WHERE id=?", (status, id_medicamento))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao atualizar status do medicamento: {e}")
        return False

def contar_medicamentos_por_data(conn, data):
    """Conta quantos medicamentos existem para uma data específica"""
    if conn is None:
        return 0
        
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM medicamentos WHERE data = ?", (data,))
        return c.fetchone()[0]
    except sqlite3.Error as e:
        st.error(f"Erro ao contar medicamentos: {e}")
        return 0

# --- INTERFACE DO USUÁRIO ---
def main():
    # Cabeçalho
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.markdown('<div class="titulo">🏥 Gestão de Medicamentos - Casa de Repouso</div>', unsafe_allow_html=True)
    
    # Conexão com o banco de dados
    conn = criar_conexao()
    if conn is None:
        st.error("Não foi possível conectar ao banco de dados. O aplicativo não pode continuar.")
        return
    
    inicializar_tabelas(conn)
    
    # Abas principais
    abas = st.tabs(["📅 Calendário", "💊 Hoje", "👴 Pacientes", "➕ Novo Medicamento", "📊 Relatórios"])
    
    with abas[0]:  # Aba Calendário
        st.subheader("📅 Calendário de Medicamentos")
        hoje = date.today()
        
        # Seletor de mês/ano
        col1, col2 = st.columns(2)
        with col1:
            mes = st.selectbox("Mês", list(calendar.month_name[1:]), index=hoje.month-1)
        with col2:
            ano = st.selectbox("Ano", range(hoje.year-1, hoje.year+3), index=1)
        
        # Gerar calendário
        mes_num = list(calendar.month_name).index(mes)
        cal = calendar.monthcalendar(ano, mes_num)
        
        # Exibir calendário
        st.markdown(f"### {mes} {ano}")
        
        # Cabeçalho dos dias da semana
        dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        cols = st.columns(7)
        for i, dia in enumerate(dias_semana):
            cols[i].write(f"**{dia}**")
        
        # Dias do mês
        for semana in cal:
            cols = st.columns(7)
            for i, dia in enumerate(semana):
                if dia == 0:
                    cols[i].write(" ")
                else:
                    data_str = f"{ano}-{mes_num:02d}-{dia:02d}"
                    data_completa = date(ano, mes_num, dia)
                    
                    # Verifica se é o dia atual
                    classe_css = "dia-calendario"
                    if data_completa == hoje:
                        classe_css += " dia-atual"
                    
                    # Verifica se há medicamentos para este dia
                    num_meds = contar_medicamentos_por_data(conn, data_str)
                    if num_meds > 0:
                        classe_css += " com-medicamento"
                    
                    with cols[i]:
                        st.markdown(f"""<div class="{classe_css}">
                            <strong>{dia}</strong>
                            {f'<br><small>{num_meds} meds</small>' if num_meds > 0 else ''}
                        </div>""", unsafe_allow_html=True)
                        
                        # Mostrar detalhes ao clicar
                        if num_meds > 0:
                            with st.expander("Ver medicamentos"):
                                medicamentos = listar_medicamentos_por_data(conn, data_str)
                                for med in medicamentos:
                                    st.write(f"**{med[1]}** - {med[2]} às {med[3]}")
                                    if med[5]:
                                        st.caption(f"Obs: {med[5]}")
                        else:
                            cols[i].write(" macaososo ")
            
    
    with abas[1]:  # Aba Hoje
        st.subheader("💊 Medicamentos para Hoje")
        hoje_str = date.today().strftime("%d/%m/%Y")
        st.markdown(f"### {hoje_str}")
        
        medicamentos_hoje = listar_medicamentos_hoje(conn)
        
        if not medicamentos_hoje:
            st.info("Nenhum medicamento agendado para hoje.")
        else:
            for med in medicamentos_hoje:
                with st.container():
                    st.markdown(f"<div class='paciente-card'>", unsafe_allow_html=True)
                    
                    cols = st.columns([0.3, 0.3, 0.2, 0.2])
                    with cols[0]: st.write(f"**Paciente:** {med[1]}")
                    with cols[1]: st.write(f"**Medicamento:** {med[2]}")
                    with cols[2]: st.write(f"**Horário:** {med[3]}")
                    with cols[3]: 
                        status = "✅ Tomou" if med[4] else "❌ Não tomou"
                        st.write(f"**Status:** {status}")
                    
                    if med[5]:  # Observações
                        with st.expander("Observações"):
                            st.write(med[5])
                    
                    # Botões para marcar como tomado/não tomado
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Marcar como tomado - {med[2]}", key=f"tomou_{med[0]}"):
                            if atualizar_status_medicamento(conn, med[0], 1):
                                st.success("Status atualizado!")
                                st.rerun()
                    with col2:
                        if st.button(f"Marcar como não tomado - {med[2]}", key=f"nao_tomou_{med[0]}"):
                            if atualizar_status_medicamento(conn, med[0], 0):
                                st.success("Status atualizado!")
                                st.rerun()
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("---")
    
    with abas[2]:  # Aba Pacientes
        st.subheader("👴 Cadastro de Pacientes")
        
        with st.expander("➕ Adicionar Novo Paciente", expanded=True):
            with st.form("form_paciente", clear_on_submit=True):
                nome = st.text_input("Nome completo*", help="Obrigatório")
                idade = st.number_input("Idade*", 0, 120, help="Obrigatório")
                condicao = st.text_area("Condições médicas e observações")
                
                if st.form_submit_button("💾 Salvar Paciente"):
                    if nome and idade:
                        if adicionar_paciente(conn, nome, idade, condicao):
                            st.success("Paciente cadastrado com sucesso!")
                            st.rerun()
                    else:
                        st.error("Por favor, preencha pelo menos o nome e a idade do paciente.")
        
        st.markdown("---")
        st.subheader("📋 Lista de Pacientes")
        pacientes = listar_pacientes(conn)
        
        if not pacientes:
            st.info("Nenhum paciente cadastrado ainda.")
        else:
            # Cabeçalho da tabela
            cols = st.columns([0.4, 0.2, 0.2, 0.2])
            with cols[0]: st.write("**Nome**")
            with cols[1]: st.write("**Idade**")
            with cols[2]: st.write("**Condição**")
            with cols[3]: st.write("**Ações**")
            
            for paciente in pacientes:
                col1, col2, col3, col4 = st.columns([0.4, 0.2, 0.2, 0.2])
                with col1: st.write(paciente[1])
                with col2: st.write(paciente[2])
                with col3: st.write(paciente[3] if paciente[3] else "-")
                
                with col4:
                    with st.expander("⚙️"):
                        with st.form(f"editar_{paciente[0]}"):
                            novo_nome = st.text_input("Nome", paciente[1])
                            nova_idade = st.number_input("Idade", value=paciente[2])
                            nova_condicao = st.text_area("Condição", paciente[3] if paciente[3] else "")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("Atualizar"):
                                    if atualizar_paciente(conn, paciente[0], novo_nome, nova_idade, nova_condicao):
                                        st.success("Paciente atualizado!")
                                        st.rerun()
                            with col2:
                                if st.form_submit_button("❌ Remover"):
                                    if remover_paciente(conn, paciente[0]):
                                        st.success("Paciente removido!")
                                        st.rerun()
    
    with abas[3]:  # Aba Novo Medicamento
        st.subheader("➕ Adicionar Novo Medicamento")
        
        pacientes = listar_pacientes(conn)
        if not pacientes:
            st.warning("Cadastre pacientes antes de adicionar medicamentos.")
        else:
            with st.form("form_medicamento", clear_on_submit=True):
                paciente_id = st.selectbox(
                    "Paciente*",
                    options=pacientes,
                    format_func=lambda x: f"{x[1]} (ID: {x[0]})",
                    help="Obrigatório"
                )
                medicamento = st.text_input("Medicamento*", help="Obrigatório")
                
                col1, col2 = st.columns(2)
                with col1:
                    horario = st.time_input("Horário*", time(8, 0), help="Obrigatório")
                with col2:
                    data = st.date_input("Data*", help="Obrigatório")
                
                observacoes = st.text_area("Observações")
                
                if st.form_submit_button("💾 Salvar Medicamento"):
                    if medicamento and paciente_id:
                        if adicionar_medicamento(
                            conn, 
                            paciente_id[0], 
                            medicamento, 
                            horario.strftime("%H:%M"), 
                            data.strftime("%Y-%m-%d"), 
                            observacoes
                        ):
                            st.success("Medicamento cadastrado com sucesso!")
                            st.rerun()
                    else:
                        st.error("Por favor, preencha todos os campos obrigatórios.")
    
    with abas[4]:  # Aba Relatórios
        st.subheader("📊 Relatórios")
        
        st.markdown("### Estatísticas")
        col1, col2, col3 = st.columns(3)
        
        try:
            c = conn.cursor()
            
            # Total de pacientes
            c.execute("SELECT COUNT(*) FROM pacientes")
            total_pacientes = c.fetchone()[0]
            col1.metric("Total de Pacientes", total_pacientes)
            
            # Total de medicamentos hoje
            hoje = date.today().strftime("%Y-%m-%d")
            c.execute("SELECT COUNT(*) FROM medicamentos WHERE data = ?", (hoje,))
            meds_hoje = c.fetchone()[0]
            col2.metric("Medicamentos Hoje", meds_hoje)
            
            # Taxa de adesão
            c.execute("SELECT COUNT(*) FROM medicamentos WHERE tomou = 1 AND data = ?", (hoje,))
            meds_tomados = c.fetchone()[0]
            taxa = (meds_tomados / meds_hoje * 100) if meds_hoje > 0 else 0
            col3.metric("Taxa de Adesão Hoje", f"{taxa:.1f}%")
            
            # Gráfico de medicamentos por dia (últimos 7 dias)
            st.markdown("---")
            st.markdown("### Medicamentos dos Últimos 7 Dias")
            
            datas = []
            counts = []
            for i in range(7):
                data = (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
                c.execute("SELECT COUNT(*) FROM medicamentos WHERE data = ?", (data,))
                count = c.fetchone()[0]
                datas.append(data)
                counts.append(count)
            
            # Inverter para mostrar do mais recente para o mais antigo
            datas.reverse()
            counts.reverse()
            
            st.bar_chart(dict(zip([datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m") for d in datas], counts)))
            
        except sqlite3.Error as e:
            st.error(f"Erro ao gerar relatórios: {e}")
    
    # Fechar conexão ao final
    conn.close()

if __name__ == "__main__":
    main()