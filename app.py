import streamlit as st
import psycopg2
import pandas as pd
import os
import time
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema Liga Vale", layout="wide", page_icon="📅")

# --- FUNÇÕES DE BANCO DE DADOS (SUPABASE / POSTGRES) ---
def pegar_conexao():
    # Conecta usando a URL que você salvou nos Secrets do Streamlit
    return psycopg2.connect(st.secrets["connections"]["postgresql"]["url"])

def criar_tabelas():
    try:
        con = pegar_conexao()
        cursor = con.cursor()
        
        # Criação de tabelas adaptada para PostgreSQL (SERIAL em vez de AUTOINCREMENT)
        cursor.execute('''CREATE TABLE IF NOT EXISTS itens 
            (id SERIAL PRIMARY KEY, nome_item TEXT, categoria TEXT, quantidade INTEGER, caminho_imagem TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS membros 
            (id SERIAL PRIMARY KEY, nome TEXT, cargo TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS eventos 
            (id SERIAL PRIMARY KEY, endereco TEXT, data_evento TEXT, status TEXT, equipe_nomes TEXT, prova_foto TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS movimentacoes 
            (id SERIAL PRIMARY KEY, id_evento INTEGER, id_item INTEGER, quantidade INTEGER, destino TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS album_fotos 
            (id SERIAL PRIMARY KEY, id_evento INTEGER, caminho_foto TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS lembretes 
            (id SERIAL PRIMARY KEY, data_lembrete TEXT, mensagem TEXT)''')
        
        con.commit()
        con.close()
    except Exception as e:
        st.error(f"Erro ao conectar no banco: {e}")

# Executa a criação das tabelas
criar_tabelas()

# --- MENU LATERAL ---
st.sidebar.title("Navegação")
opcao = st.sidebar.selectbox("Ir para:", ["🏠 Início", "📦 Estoque", "📅 Gestão de Eventos"])

# ==================================================
# TELA 0: INÍCIO (DASHBOARD)
# ==================================================
if opcao == "🏠 Início":
    
    # 1. CABEÇALHO
    c_img_esq, c_img_centro, c_img_dir = st.columns([3, 2, 3])
    with c_img_centro:
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        else:
            # Se não tiver logo, mostra título simples
            pass

    c_txt_esq, c_txt_centro, c_txt_dir = st.columns([1, 8, 1])
    with c_txt_centro:
        st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>SISTEMA DE GERENCIAMENTO</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; margin-top: 0px; color: #FFD700;'>EQUIPE DE MONTAGEM - LIGA VALE</h3>", unsafe_allow_html=True)
    
    st.divider()

    con = pegar_conexao()

    # --- LINHA DE CIMA ---
    col_sup_esq, col_sup_dir = st.columns(2, gap="large")

    # QUADRANTE 1: MEMBROS
    with col_sup_esq:
        st.subheader("👥 Equipe de Montagem")
        df_membros = pd.read_sql_query("SELECT nome as NOMES, cargo as CARGO FROM membros", con)
        if not df_membros.empty:
            st.dataframe(df_membros, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhum membro cadastrado. Vá em 'Gestão de Eventos' > 'Equipe'.")

    # QUADRANTE 2: CALENDÁRIO
    with col_sup_dir:
        st.subheader("📅 Calendário Interativo")
        data_cal = st.date_input("Selecione a data:", datetime.today())
        
        with st.expander(f"➕ Adicionar nota para {data_cal.strftime('%d/%m')}"):
            txt_lembrete = st.text_input("Lembrete:")
            if st.button("Salvar Nota"):
                cur = con.cursor()
                cur.execute("INSERT INTO lembretes (data_lembrete, mensagem) VALUES (%s, %s)", (str(data_cal), txt_lembrete))
                con.commit()
                cur.close()
                st.success("Salvo!")
                time.sleep(0.5)
                st.rerun()

        st.markdown("---")
        st.write(f"**Agenda de {data_cal.strftime('%d/%m')}:**")
        
        evs = pd.read_sql_query(f"SELECT endereco, status FROM eventos WHERE data_evento = '{data_cal}'", con)
        lembs = pd.read_sql_query(f"SELECT id, mensagem FROM lembretes WHERE data_lembrete = '{data_cal}'", con)

        if evs.empty and lembs.empty:
            st.caption("Nada agendado.")
        else:
            for _, r in evs.iterrows():
                icone = "✅" if r['status'] == 'Finalizado' else "🚀"
                st.info(f"{icone} Evento: **{r['endereco']}**")
            for _, r in lembs.iterrows():
                c1, c2 = st.columns([5,1])
                c1.warning(f"📌 {r['mensagem']}")
                if c2.button("X", key=f"del_l_{r['id']}"):
                    cur = con.cursor()
                    cur.execute("DELETE FROM lembretes WHERE id = %s", (r['id'],))
                    con.commit()
                    cur.close()
                    st.rerun()

    st.markdown("---")

    # --- LINHA DE BAIXO ---
    col_inf_esq, col_inf_dir = st.columns(2, gap="large")

    # QUADRANTE 3: ÚLTIMOS EVENTOS
    with col_inf_esq:
        st.subheader("⏮️ Últimos Realizados")
        ultimos = pd.read_sql_query("SELECT endereco, data_evento FROM eventos WHERE status = 'Finalizado' ORDER BY data_evento DESC LIMIT 5", con)
        if ultimos.empty:
            st.caption("Nenhum evento finalizado ainda.")
        else:
            for _, r in ultimos.iterrows():
                dt = datetime.strptime(r['data_evento'], '%Y-%m-%d').strftime('%d/%m/%Y')
                st.text(f"📍 {r['endereco']} ({dt})")
                st.divider()

    # QUADRANTE 4: PRÓXIMO EVENTO
    with col_inf_dir:
        st.subheader("🔜 Próximo da Lista")
        prox = pd.read_sql_query("SELECT * FROM eventos WHERE status != 'Finalizado' ORDER BY data_evento ASC LIMIT 1", con)
        
        if prox.empty:
            st.success("Agenda livre! Nenhum evento futuro.")
        else:
            p = prox.iloc[0]
            dt_p = datetime.strptime(p['data_evento'], '%Y-%m-%d').strftime('%d/%m/%Y')
            titulo_evento = p['endereco']
            
            st.markdown(f"""
                <div style="background-color: #e8f5e9; padding: 20px; border-radius: 10px; border-left: 5px solid #4CAF50; color: #000000;">
                    <h3 style="color: #000000; margin: 0;">📍 {titulo_evento}</h3>
                    <br>
                    <p style="color: #333333; font-size: 18px; margin: 5px 0;"><strong>📅 Data:</strong> {dt_p}</p>
                    <p style="color: #333333; font-size: 18px; margin: 5px 0;"><strong>🚧 Status:</strong> {p['status']}</p>
                    <hr style="border: 1px solid #4CAF50;">
                    <small style="color: #555555; font-size: 14px;"><strong>Equipe escalada:</strong> {p['equipe_nomes']}</small>
                </div>
            """, unsafe_allow_html=True)

    con.close()

# ==================================================
# TELA 1: ESTOQUE
# ==================================================
elif opcao == "📦 Estoque":
    st.title("📦 Gestão de Inventário")
    
    aba_ver, aba_cad = st.tabs(["📋 Ver Estoque Completo", "➕ Cadastrar Novo Item"])

    with aba_cad:
        st.subheader("Adicionar Novo Material")
        with st.form("form_cadastro_visual"):
            c1, c2 = st.columns(2)
            with c1:
                n = st.text_input("Nome do Item (ex: Cadeira)")
                c = st.selectbox("Categoria", ["Mobiliário", "Estrutura", "Eletrônicos", "Outros"])
            with c2:
                q = st.number_input("Quantidade Total", min_value=1, value=1)
                img = st.file_uploader("Foto", type=["jpg", "png"])
            
            if st.form_submit_button("Salvar Item"):
                path = "Sem foto"
                # OBS: Em produção real, salvar imagem localmente no servidor do Streamlit não dura muito.
                # O ideal seria salvar no Supabase Storage, mas vamos manter simples por enquanto.
                if img:
                    if not os.path.exists("fotos_itens"): os.makedirs("fotos_itens")
                    path = f"fotos_itens/{img.name}"
                    with open(path, "wb") as f: f.write(img.getbuffer())
                
                con = pegar_conexao()
                cur = con.cursor()
                cur.execute("INSERT INTO itens (nome_item, categoria, quantidade, caminho_imagem) VALUES (%s,%s,%s,%s)", (n, c, q, path))
                con.commit()
                cur.close()
                con.close()
                st.success("Item cadastrado com sucesso!")

    with aba_ver:
        st.subheader("📋 Estoque Atual")
        
        con = pegar_conexao()
        df_itens = pd.read_sql_query("SELECT * FROM itens", con)
        con.close()
        
        if df_itens.empty:
            st.info("Nenhum item cadastrado.")
        else:
            for index, row in df_itens.iterrows():
                with st.container():
                    col_foto, col_dados = st.columns([1, 4])
                    
                    with col_foto:
                        if row['caminho_imagem'] != "Sem foto" and os.path.exists(row['caminho_imagem']):
                            st.image(row['caminho_imagem'], use_container_width=True)
                        else:
                            st.markdown("<div style='font-size: 50px; text-align: center;'>📦</div>", unsafe_allow_html=True)

                    with col_dados:
                        st.subheader(f"{row['nome_item']}")
                        st.metric("Quantidade Total", row['quantidade'])
                        
                        with st.expander("🔎 Ver Detalhes e Editar"):
                            t_edit, t_onde, t_del = st.tabs(["📝 Editar", "📍 Onde está?", "⚠️ Excluir"])
                            
                            with t_edit:
                                with st.form(key=f"edit_vis_{row['id']}"):
                                    nn = st.text_input("Nome", value=row['nome_item'])
                                    nc = st.selectbox("Categoria", ["Mobiliário", "Estrutura", "Eletrônicos", "Outros"], index=0)
                                    nq = st.number_input("Quantidade", value=row['quantidade'])
                                    
                                    if st.form_submit_button("Salvar Alterações"):
                                        con = pegar_conexao()
                                        cur = con.cursor()
                                        cur.execute("UPDATE itens SET nome_item=%s, categoria=%s, quantidade=%s WHERE id=%s", (nn, nc, nq, row['id']))
                                        con.commit()
                                        cur.close()
                                        con.close()
                                        st.success("Atualizado!")
                                        time.sleep(0.5)
                                        st.rerun()

                            with t_onde:
                                con = pegar_conexao()
                                movs = pd.read_sql_query(f"SELECT * FROM movimentacoes WHERE id_item = {row['id']}", con)
                                con.close()

                                qtd_fora = movs['quantidade'].sum() if not movs.empty else 0
                                qtd_sede = row['quantidade'] - qtd_fora
                                
                                st.write(f"🏠 **Na Sede:** {qtd_sede}")
                                st.write(f"🚚 **Em Eventos:** {qtd_fora}")
                                
                                if row['quantidade'] > 0:
                                    st.progress(max(0.0, min(1.0, qtd_sede / row['quantidade'])))
                                
                                if not movs.empty:
                                    st.dataframe(movs[['destino', 'quantidade']], hide_index=True)

                            with t_del:
                                st.warning("Atenção: Exclusão permanente.")
                                chk = st.checkbox("Confirmar exclusão", key=f"check_vis_{row['id']}")
                                
                                if st.button("🗑️ Deletar Item", key=f"btn_vis_del_{row['id']}", disabled=not chk):
                                    con = pegar_conexao()
                                    cur = con.cursor()
                                    cur.execute("DELETE FROM movimentacoes WHERE id_item = %s", (row['id'],))
                                    cur.execute("DELETE FROM itens WHERE id = %s", (row['id'],))
                                    con.commit()
                                    cur.close()
                                    con.close()
                                    st.error("Item excluído.")
                                    time.sleep(0.5)
                                    st.rerun()
                st.markdown("---")

# ==================================================
# TELA 2: GESTÃO DE EVENTOS
# ==================================================
elif opcao == "📅 Gestão de Eventos":
    st.title("📅 Operação de Eventos")
    aba_painel, aba_equipe, aba_novo, aba_logistica, aba_retorno = st.tabs([
        "📋 Painel", "👥 Equipe", "➕ Novo", "🚚 Saída", "🔙 Retorno"
    ])

    # --- ABA PAINEL ---
    with aba_painel:
        st.subheader("📋 Quadro de Gestão de Eventos")
        
        con = pegar_conexao()
        df_evs = pd.read_sql_query("SELECT * FROM eventos", con)
        lista_membros_completa = pd.read_sql_query("SELECT nome FROM membros", con)['nome'].tolist()
        con.close()
        
        if df_evs.empty:
            st.info("Nenhum evento cadastrado.")
        else:
            col_andamento, col_agendado, col_finalizado = st.columns(3, gap="medium")
            
            configuracao = [
                ("🚀 Em Andamento", "Em Andamento", col_andamento, "#FF4B4B"),
                ("📅 Agendados", "Agendado", col_agendado, "#FFD700"),
                ("✅ Finalizados", "Finalizado", col_finalizado, "#4CAF50")
            ]

            for titulo, filtro, coluna, cor in configuracao:
                with coluna:
                    st.markdown(f"<h3 style='text-align: center; color: {cor};'>{titulo}</h3>", unsafe_allow_html=True)
                    st.divider()

                    df_filt = df_evs[df_evs['status'] == filtro]
                    
                    if df_filt.empty:
                        st.caption("Vazio.")
                    
                    for _, row in df_filt.iterrows():
                        with st.expander(f"📍 {row['endereco']}"):
                            st.caption(f"Data: {datetime.strptime(row['data_evento'], '%Y-%m-%d').strftime('%d/%m/%Y')}")
                            
                            t_info, t_acao = st.tabs(["📋 Detalhes", "⚙️ Gestão"])
                            
                            equipe_atual_lista = [x.strip() for x in row['equipe_nomes'].split(",")] if row['equipe_nomes'] else []
                            equipe_validada = [m for m in equipe_atual_lista if m in lista_membros_completa]

                            # --- ABA DETALHES ---
                            with t_info:
                                st.write(f"**👷 Equipe:** {row['equipe_nomes']}")
                                st.markdown("---")
                                con = pegar_conexao()
                                itens = pd.read_sql_query(f'''
                                    SELECT i.nome_item, m.quantidade FROM movimentacoes m 
                                    JOIN itens i ON m.id_item = i.id WHERE m.id_evento = {row['id']}
                                ''', con)
                                galeria = pd.read_sql_query(f"SELECT caminho_foto FROM album_fotos WHERE id_evento = {row['id']}", con)
                                con.close()
                                
                                if not itens.empty:
                                    st.write("**📦 Materiais:**")
                                    st.dataframe(itens, hide_index=True, use_container_width=True)
                                else:
                                    st.caption("Sem materiais.")
                                
                                st.markdown("---")
                                if len(galeria) > 0:
                                    if st.checkbox("👁️ Ver Fotos", key=f"v_f_{row['id']}"):
                                        fotos_reais = [f for f in galeria['caminho_foto'].tolist() if os.path.exists(f)]
                                        if fotos_reais: st.image(fotos_reais, width=200)

                            # --- ABA AÇÕES ---
                            with t_acao:
                                
                                # CENÁRIO 1: FINALIZADO
                                if row['status'] == 'Finalizado':
                                    st.markdown("""
                                        <div style='background-color: #e8f5e9; padding: 15px; border-radius: 8px; border-left: 5px solid #4CAF50; margin-bottom: 15px;'>
                                            <h4 style='color: #1b5e20; margin:0;'>🔒 Evento Finalizado</h4>
                                            <p style='color: #2e7d32; font-size: 14px; margin-top: 5px;'>
                                                <b>Registro Protegido:</b> Equipe e dados históricos não podem ser alterados.
                                            </p>
                                        </div>
                                    """, unsafe_allow_html=True)
                                    
                                    st.write(f"**Equipe Confirmada:** {row['equipe_nomes']}")
                                    
                                    with st.expander("🔐 Área Admin (Apenas Exclusão)"):
                                        senha_admin = st.text_input("Senha", type="password", key=f"pass_{row['id']}")
                                        if senha_admin == "admin123":
                                            check_del_fin = st.checkbox("Confirmar exclusão permanente", key=f"chk_fin_{row['id']}")
                                            if st.button("🗑️ APAGAR REGISTRO", key=f"btn_del_fin_{row['id']}", disabled=not check_del_fin):
                                                con = pegar_conexao()
                                                cur = con.cursor()
                                                cur.execute("DELETE FROM movimentacoes WHERE id_evento=%s", (row['id'],))
                                                cur.execute("DELETE FROM album_fotos WHERE id_evento=%s", (row['id'],))
                                                cur.execute("DELETE FROM eventos WHERE id=%s", (row['id'],))
                                                con.commit()
                                                cur.close()
                                                con.close()
                                                st.rerun()

                                # CENÁRIO 2: ATIVO
                                else:
                                    st.markdown("##### 👷 Editar Escalação")
                                    nova_equipe = st.multiselect("Membros da Equipe", lista_membros_completa, default=equipe_validada, key=f"edit_eq_{row['id']}")
                                    
                                    if st.button("Salvar Equipe", key=f"btn_save_eq_{row['id']}"):
                                        string_nova_equipe = ", ".join(nova_equipe)
                                        con = pegar_conexao()
                                        cur = con.cursor()
                                        cur.execute("UPDATE eventos SET equipe_nomes = %s WHERE id = %s", (string_nova_equipe, row['id']))
                                        con.commit()
                                        cur.close()
                                        con.close()
                                        st.success("Escalação atualizada!")
                                        time.sleep(0.5)
                                        st.rerun()

                                    st.divider()

                                    st.write("**Adicionar Fotos:**")
                                    novas_fotos = st.file_uploader("Upload", type=['jpg','png'], accept_multiple_files=True, key=f"up_{row['id']}", label_visibility="collapsed")
                                    if novas_fotos and st.button("Enviar Fotos", key=f"sf_{row['id']}"):
                                        con = pegar_conexao()
                                        cur = con.cursor()
                                        if not os.path.exists("fotos_eventos"): os.makedirs("fotos_eventos")
                                        for foto in novas_fotos:
                                            nome_arq = f"fotos_eventos/ev_{row['id']}_{int(time.time())}_{foto.name}"
                                            with open(nome_arq, "wb") as f: f.write(foto.getbuffer())
                                            cur.execute("INSERT INTO album_fotos (id_evento, caminho_foto) VALUES (%s, %s)", (row['id'], nome_arq))
                                        cur.execute("UPDATE eventos SET prova_foto = %s WHERE id = %s", ("Multiplas", row['id']))
                                        con.commit()
                                        cur.close()
                                        con.close()
                                        st.success("Fotos salvas!")
                                        st.rerun()

                                    st.divider()

                                    st.write("**Alterar Status:**")
                                    ops = ["Agendado", "Em Andamento", "Finalizado"]
                                    idx = ops.index(row['status'])
                                    n_st = st.selectbox("Status", ops, index=idx, key=f"st_{row['id']}", label_visibility="collapsed")
                                    
                                    if st.button("Confirmar Status", key=f"btn_{row['id']}"):
                                        con = pegar_conexao()
                                        pend = pd.read_sql_query(f"SELECT COUNT(*) as t FROM movimentacoes WHERE id_evento={row['id']}", con).iloc[0]['t']
                                        tem_album = pd.read_sql_query(f"SELECT COUNT(*) as t FROM album_fotos WHERE id_evento={row['id']}", con).iloc[0]['t']
                                        
                                        if n_st == "Finalizado":
                                            if pend > 0:
                                                st.error(f"🚫 Pendências: {pend} itens!")
                                                st.stop()
                                            if tem_album == 0 and not novas_fotos:
                                                st.error("🚫 É obrigatório ter fotos!")
                                                st.stop()
                                        
                                        cur = con.cursor()
                                        cur.execute("UPDATE eventos SET status = %s WHERE id = %s", (n_st, row['id']))
                                        con.commit()
                                        cur.close()
                                        con.close()
                                        st.rerun()
                                    
                                    st.write("---")
                                    chk_ex = st.checkbox("Confirmar exclusão", key=f"chk_del_{row['id']}")
                                    if st.button("🗑️ Excluir Evento", key=f"del_{row['id']}", disabled=not chk_ex):
                                        con = pegar_conexao()
                                        cur = con.cursor()
                                        cur.execute("DELETE FROM movimentacoes WHERE id_evento=%s", (row['id'],))
                                        cur.execute("DELETE FROM album_fotos WHERE id_evento=%s", (row['id'],))
                                        cur.execute("DELETE FROM eventos WHERE id=%s", (row['id'],))
                                        con.commit()
                                        cur.close()
                                        con.close()
                                        st.rerun()

    # --- ABA EQUIPE (VISUAL COMPACTO) ---
    with aba_equipe:
        st.subheader("👥 Gestão de Membros da Equipe")
        
        con = pegar_conexao()
        df_membros = pd.read_sql_query("SELECT * FROM membros", con)
        con.close()
        
        if df_membros.empty:
            st.info("Nenhum membro cadastrado.")
        else:
            st.markdown("##### 📋 Lista Atual de Colaboradores")
            c_esq, c_meio, c_dir = st.columns([1, 2, 1])
            with c_meio:
                st.dataframe(
                    df_membros,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "id": None,
                        "nome": st.column_config.TextColumn("👤 Nome do Colaborador", width="medium"),
                        "cargo": st.column_config.TextColumn("🛠️ Função / Cargo", width="small")
                    }
                )
        
        st.divider()
        c_add, c_del = st.columns(2, gap="large")
        
        with c_add:
            st.markdown("#### ➕ Adicionar Novo")
            with st.form("form_add_membro"):
                nm = st.text_input("Nome Completo")
                cg = st.selectbox("Função/Cargo", ["Montador", "Coordenador", "Motorista", "Auxiliar"])
                
                if st.form_submit_button("Cadastrar Membro", type="primary"):
                    if nm:
                        if not df_membros.empty and nm in df_membros['nome'].values:
                            st.warning("Esse nome já está na lista!")
                        else:
                            con = pegar_conexao()
                            cur = con.cursor()
                            cur.execute("INSERT INTO membros (nome, cargo) VALUES (%s, %s)", (nm, cg))
                            con.commit()
                            cur.close()
                            con.close()
                            st.success(f"✅ {nm} adicionado!")
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.warning("Preencha o nome.")

        with c_del:
            st.markdown("#### 🗑️ Remover Colaborador")
            if not df_membros.empty:
                me = st.selectbox("Selecione para excluir:", df_membros['nome'].tolist())
                if st.checkbox(f"Confirmar exclusão de {me}", key="chk_del_memb"):
                    if st.button("Confirmar Exclusão", type="primary"):
                        con = pegar_conexao()
                        cur = con.cursor()
                        cur.execute("DELETE FROM membros WHERE nome = %s", (me,))
                        con.commit()
                        cur.close()
                        con.close()
                        st.error("Membro removido!")
                        time.sleep(0.5)
                        st.rerun()
            else:
                st.caption("A lista está vazia.")

    # --- ABA NOVO EVENTO ---
    with aba_novo:
        st.subheader("📝 Agendar Novo Evento")
        with st.form("novo_ev"):
            c1, c2 = st.columns(2)
            with c1:
                nome_ev = st.text_input("Nome do Evento (ex: Casamento Silva)")
            with c2:
                end_ev = st.text_input("Endereço / Local")
            
            dt = st.date_input("Data do Evento")
            
            con = pegar_conexao()
            lista_m = pd.read_sql_query("SELECT nome FROM membros", con)['nome'].tolist()
            con.close()
            
            eq = st.multiselect("Equipe Escalada", lista_m)
            
            if st.form_submit_button("Criar Evento"):
                if nome_ev and end_ev:
                    identificacao_completa = f"{nome_ev} | {end_ev}"
                    con = pegar_conexao()
                    cur = con.cursor()
                    cur.execute("INSERT INTO eventos (endereco, data_evento, status, equipe_nomes) VALUES (%s, %s, 'Agendado', %s)", 
                                (identificacao_completa, str(dt), ", ".join(eq)))
                    con.commit()
                    cur.close()
                    con.close()
                    st.success(f"Evento '{nome_ev}' criado com sucesso!")
                else:
                    st.warning("Preencha o Nome e o Endereço.")

    # --- ABA SAÍDA (COM TRAVA DE ESTOQUE) ---
    with aba_logistica:
        st.subheader("🚚 Registrar Saída de Material")
        
        con = pegar_conexao()
        ev_a = pd.read_sql_query("SELECT id, endereco FROM eventos WHERE status != 'Finalizado'", con)
        its = pd.read_sql_query("SELECT * FROM itens", con)
        con.close()
        
        if ev_a.empty:
            st.warning("⚠️ Não há eventos ativos.")
        elif its.empty:
            st.warning("⚠️ Não há itens cadastrados.")
        else:
            col_out1, col_out2, col_out3 = st.columns(3)
            
            ev_sel = col_out1.selectbox("Para qual Evento?", ev_a['id'].tolist(), format_func=lambda x: ev_a[ev_a['id']==x]['endereco'].values[0])
            id_item_sel = col_out2.selectbox("Qual Item?", its['id'].tolist(), format_func=lambda x: its[its['id']==x]['nome_item'].values[0])
            qtd_saida = col_out3.number_input("Quantidade", min_value=1, value=1)
            
            if st.button("Registrar Saída 🚚", type="primary"):
                con = pegar_conexao()
                
                query_uso = f"SELECT SUM(quantidade) FROM movimentacoes WHERE id_item = {id_item_sel}"
                df_uso = pd.read_sql_query(query_uso, con)
                qtd_usada = df_uso.iloc[0,0]
                if qtd_usada is None: qtd_usada = 0
                
                qtd_total_item = its[its['id'] == id_item_sel]['quantidade'].values[0]
                qtd_disponivel = qtd_total_item - qtd_usada
                
                if qtd_saida > qtd_disponivel:
                    st.error(f"🚫 PROIBIDO: Estoque insuficiente!")
                    st.write(f"Você tentou enviar **{qtd_saida}**, mas só tem **{qtd_disponivel}** disponíveis.")
                else:
                    cur = con.cursor()
                    cur.execute("INSERT INTO movimentacoes (id_evento, id_item, quantidade, destino) VALUES (%s, %s, %s, %s)", (ev_sel, id_item_sel, qtd_saida, "Evento"))
                    con.commit()
                    cur.close()
                    st.success(f"✅ Sucesso! Saída registrada.")
                    time.sleep(1)
                    st.rerun()
                con.close()

    # --- ABA RETORNO (VISUAL MELHORADO) ---
    with aba_retorno:
        st.subheader("🔙 Retorno de Material")
        st.info("Abaixo estão os itens que ainda estão na rua. Selecione para devolver.")

        con = pegar_conexao()
        movs = pd.read_sql_query('''
            SELECT m.id, e.endereco, i.nome_item, m.quantidade 
            FROM movimentacoes m
            JOIN eventos e ON m.id_evento = e.id
            JOIN itens i ON m.id_item = i.id
        ''', con)
        con.close()
        
        if movs.empty:
            st.success("✅ Tudo limpo! Nenhum material pendente na rua.")
        else:
            st.markdown("##### 📋 Lista de Pendências")
            c_esq, c_meio, c_dir = st.columns([0.2, 4, 0.2])
            with c_meio:
                st.dataframe(
                    movs,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "id": None,
                        "endereco": st.column_config.TextColumn("📍 Evento / Local", width="large"),
                        "nome_item": st.column_config.TextColumn("📦 Material", width="medium"),
                        "quantidade": st.column_config.NumberColumn("🔢 Qtd Pendente", format="%d", width="small")
                    }
                )

            st.divider()
            col_dev1, col_dev2, col_dev3 = st.columns([3, 2, 2])
            
            with col_dev1:
                lista_opcoes = movs.apply(lambda x: f"{x['id']} - {x['nome_item']} (No local: {x['quantidade']}) em {x['endereco']}", axis=1).tolist()
                selecao = st.selectbox("Selecione a Movimentação:", lista_opcoes)
            
            id_mov_selecionado = int(selecao.split(" - ")[0])
            qtd_maxima_no_local = int(movs[movs['id'] == id_mov_selecionado]['quantidade'].values[0])

            with col_dev2:
                qtd_devolver = st.number_input("Qtd a Devolver", min_value=1, max_value=qtd_maxima_no_local, value=qtd_maxima_no_local)

            with col_dev3:
                st.write("") 
                st.write("") 
                if st.button("Confirmar Retorno 📥", type="primary"):
                    con = pegar_conexao()
                    cur = con.cursor()
                    
                    if qtd_devolver == qtd_maxima_no_local:
                        cur.execute("DELETE FROM movimentacoes WHERE id = %s", (id_mov_selecionado,))
                        msg = "✅ Devolução total! Item baixado."
                    else:
                        nova_qtd = qtd_maxima_no_local - qtd_devolver
                        cur.execute("UPDATE movimentacoes SET quantidade = %s WHERE id = %s", (nova_qtd, id_mov_selecionado))
                        msg = f"✅ Devolução parcial! {qtd_devolver} retornaram."
                    
                    con.commit()
                    cur.close()
                    con.close()
                    st.success(msg)
                    time.sleep(1.5)
                    st.rerun()
