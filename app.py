import streamlit as st
import sqlite3
import pandas as pd
import os
import time
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema Liga Vale ", layout="wide", page_icon="🏅")

# --- FUNÇÕES DE BANCO DE DADOS ---
def pegar_conexao():
    return sqlite3.connect('estoque.db')

def criar_tabelas():
    # Esta função cria o banco do zero se ele não existir
    con = pegar_conexao()
    cursor = con.cursor()
    
    # Tabela 1: Itens
    cursor.execute('''CREATE TABLE IF NOT EXISTS itens 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_item TEXT, categoria TEXT, quantidade INTEGER, caminho_imagem TEXT)''')
    
    # Tabela 2: Membros
    cursor.execute('''CREATE TABLE IF NOT EXISTS membros 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cargo TEXT)''')
    
    # Tabela 3: Eventos (Já com a coluna de foto)
    cursor.execute('''CREATE TABLE IF NOT EXISTS eventos 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, endereco TEXT, data_evento TEXT, status TEXT, equipe_nomes TEXT, prova_foto TEXT)''')
    
    # Tabela 4: Movimentações
    cursor.execute('''CREATE TABLE IF NOT EXISTS movimentacoes 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, id_evento INTEGER, id_item INTEGER, quantidade INTEGER, origem TEXT, destino TEXT)''')
    
    # Tabela 5: Lembretes (Calendário)
    cursor.execute('''CREATE TABLE IF NOT EXISTS lembretes 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, data_lembrete TEXT, mensagem TEXT)''')
    
    con.commit()
    con.close()

# Executa a criação das tabelas assim que o app abre
criar_tabelas()

# --- MENU LATERAL ---
st.sidebar.title("Navegação")
opcao = st.sidebar.selectbox("Ir para:", ["🏠 Início", "📦 Estoque", "📅 Gestão de Eventos"])

# ==================================================
# TELA 0: INÍCIO (DASHBOARD)
# ==================================================
if opcao == "🏠 Início":
    
    # 1. CABEÇALHO
    
    # --- PARTE DA LOGO ---
    # Criamos 3 colunas para centralizar a imagem no meio
    c_img_esq, c_img_centro, c_img_dir = st.columns([3, 2, 3])
    with c_img_centro:
        # Verifica se a imagem existe para não dar erro se esquecer de salvar
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        else:
            st.warning("⚠️ Imagem 'logo.png' não encontrada na pasta do projeto.")

    # --- PARTE DOS TÍTULOS ---
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
                con.execute("INSERT INTO lembretes (data_lembrete, mensagem) VALUES (?, ?)", (str(data_cal), txt_lembrete))
                con.commit()
                st.success("Salvo!")
                time.sleep(0.5)
                st.rerun()

        st.markdown("---")
        st.write(f"**Agenda de {data_cal.strftime('%d/%m')}:**")
        
        # Busca
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
                    con.execute("DELETE FROM lembretes WHERE id = ?", (r['id'],))
                    con.commit()
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
        # Busca o primeiro evento que NÃO está finalizado
        prox = pd.read_sql_query("SELECT * FROM eventos WHERE status != 'Finalizado' ORDER BY data_evento ASC LIMIT 1", con)
        
        if prox.empty:
            st.success("Agenda livre! Nenhum evento futuro.")
        else:
            p = prox.iloc[0]
            
            # Formata a data e divide o endereço/nome se tiver o separador "|"
            dt_p = datetime.strptime(p['data_evento'], '%Y-%m-%d').strftime('%d/%m/%Y')
            titulo_evento = p['endereco']
            
            # HTML com cores forçadas para PRETO (#000000) e CINZA ESCURO (#333333)
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
# TELA 1: ESTOQUE (LAYOUT VISUAL TIPO "CARD")
# ==================================================
elif opcao == "📦 Estoque":
    st.title("📦 Gestão de Inventário")
    
    # Abas principais
    aba_ver, aba_cad = st.tabs(["📋 Ver Estoque Completo", "➕ Cadastrar Novo Item"])

    # --- ABA DE CADASTRO (Mantemos igual) ---
    with aba_cad:
        st.subheader("Adicionar Novo Material")
        with st.form("form_cadastro_visual"):
            c1, c2 = st.columns(2)
            with c1:
                n = st.text_input("Nome do Item (ex: Cadeira)")
                c = st.selectbox("Categoria", ["Mobiliário", "Estrutura", "Eletrônicos","Proteções", "Banners", "Outros"])
            with c2:
                q = st.number_input("Quantidade Total", min_value=1, value=1)
                img = st.file_uploader("Foto", type=["jpg", "png"])
            
            if st.form_submit_button("Salvar Item"):
                path = "Sem foto"
                if img:
                    if not os.path.exists("fotos_itens"): os.makedirs("fotos_itens")
                    path = f"fotos_itens/{img.name}"
                    with open(path, "wb") as f: f.write(img.getbuffer())
                
                con = pegar_conexao()
                con.execute("INSERT INTO itens (nome_item, categoria, quantidade, caminho_imagem) VALUES (?,?,?,?)", (n, c, q, path))
                con.commit()
                con.close()
                st.success("Item cadastrado com sucesso!")

    # --- ABA DE VISUALIZAÇÃO (AQUI MUDAMOS O DESIGN) ---
    with aba_ver:
        st.subheader("📋 Estoque Atual")
        
        con = pegar_conexao()
        df_itens = pd.read_sql_query("SELECT * FROM itens", con)
        con.close()
        
        if df_itens.empty:
            st.info("Nenhum item cadastrado.")
        else:
            # Loop pelos itens
            for index, row in df_itens.iterrows():
                
                # Container cria um bloco visual para cada item
                with st.container():
                    # Criamos colunas: Imagem (menor) | Dados (maior)
                    col_foto, col_dados = st.columns([1, 4])
                    
                    # --- COLUNA DA ESQUERDA: FOTO ---
                    with col_foto:
                        if row['caminho_imagem'] != "Sem foto" and os.path.exists(row['caminho_imagem']):
                            # Mostra a imagem grande e bonita
                            st.image(row['caminho_imagem'], use_container_width=True)
                        else:
                            # Se não tiver foto, mostra um ícone grande
                            st.markdown("<div style='font-size: 50px; text-align: center;'>📦</div>", unsafe_allow_html=True)

                    # --- COLUNA DA DIREITA: INFORMAÇÕES ---
                    with col_dados:
                        # Título Grande (Nome do Item)
                        st.subheader(f"{row['nome_item']}")
                        
                        # Quantidade em destaque (Metric)
                        st.metric("Quantidade Total", row['quantidade'])
                        
                        # O Expander agora é apenas um botão para "Ver Mais"
                        with st.expander("🔎 Ver Detalhes e Editar"):
                            
                            # Abas internas de ação
                            t_edit, t_onde, t_del = st.tabs(["📝 Editar", "📍 Onde está?", "⚠️ Excluir"])
                            
                            # 1. EDITAR
                            with t_edit:
                                with st.form(key=f"edit_vis_{row['id']}"):
                                    nn = st.text_input("Nome", value=row['nome_item'])
                                    nc = st.selectbox("Categoria", ["Mobiliário", "Estrutura", "Eletrônicos","Proteções", "Banners", "Outros"], index=0)
                                    nq = st.number_input("Quantidade", value=row['quantidade'])
                                    
                                    if st.form_submit_button("Salvar Alterações"):
                                        con = pegar_conexao()
                                        con.execute("UPDATE itens SET nome_item=?, categoria=?, quantidade=? WHERE id=?", (nn, nc, nq, row['id']))
                                        con.commit()
                                        con.close()
                                        st.success("Atualizado!")
                                        time.sleep(0.5)
                                        st.rerun()

                            # 2. ONDE ESTÁ?
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

                            # 3. EXCLUIR
                            with t_del:
                                st.warning("Atenção: Exclusão permanente.")
                                chk = st.checkbox("Confirmar exclusão", key=f"check_vis_{row['id']}")
                                
                                if st.button("🗑️ Deletar Item", key=f"btn_vis_del_{row['id']}", disabled=not chk):
                                    con = pegar_conexao()
                                    con.execute("DELETE FROM movimentacoes WHERE id_item = ?", (row['id'],))
                                    con.execute("DELETE FROM itens WHERE id = ?", (row['id'],))
                                    con.commit()
                                    con.close()
                                    st.error("Item excluído.")
                                    time.sleep(0.5)
                                    st.rerun()
                
                # Linha divisória entre os itens (igual à foto)
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
    # --- ABA PAINEL (COM TRAVA DE SEGURANÇA E GALERIA DE FOTOS) ---
    with aba_painel:
        st.subheader("📋 Quadro de Gestão de Eventos")
        
        # 1. GARANTIA DO BANCO DE DADOS (Cria tabela de fotos múltiplas se não existir)
        con_temp = pegar_conexao()
        con_temp.execute("CREATE TABLE IF NOT EXISTS album_fotos (id INTEGER PRIMARY KEY AUTOINCREMENT, id_evento INTEGER, caminho_foto TEXT)")
        con_temp.commit()
        con_temp.close()
        
        con = pegar_conexao()
        df_evs = pd.read_sql_query("SELECT * FROM eventos", con)
        con.close()
        
        if df_evs.empty:
            st.info("Nenhum evento cadastrado.")
        else:
            # Kanban: 3 Colunas
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
                        # O Cartão do Evento
                        with st.expander(f"📍 {row['endereco']}"):
                            st.caption(f"Data: {datetime.strptime(row['data_evento'], '%Y-%m-%d').strftime('%d/%m/%Y')}")
                            
                            # Separamos em abas para organizar
                            t_info, t_acao = st.tabs(["📋 Detalhes", "⚙️ Gestão"])
                            
                            # --- ABA 1: INFORMAÇÕES (VISÍVEL PARA TODOS) ---
                            with t_info:
                                st.write(f"**👷 Equipe:** {row['equipe_nomes']}")
                                st.markdown("---")
                                
                                # Materiais
                                con = pegar_conexao()
                                itens = pd.read_sql_query(f'''
                                    SELECT i.nome_item, m.quantidade FROM movimentacoes m 
                                    JOIN itens i ON m.id_item = i.id WHERE m.id_evento = {row['id']}
                                ''', con)
                                # Busca as fotos do álbum
                                galeria = pd.read_sql_query(f"SELECT caminho_foto FROM album_fotos WHERE id_evento = {row['id']}", con)
                                con.close()
                                
                                if not itens.empty:
                                    st.write("**📦 Materiais:**")
                                    st.dataframe(itens, hide_index=True, use_container_width=True)
                                else:
                                    st.caption("Sem materiais registrados.")

                                st.markdown("---")
                                
                                # GALERIA DE FOTOS (NOVIDADE)
                                qtd_fotos = len(galeria)
                                if qtd_fotos > 0:
                                    st.success(f"📸 Este evento possui {qtd_fotos} fotos registradas.")
                                    # Botão para expandir a galeria
                                    if st.checkbox("👁️ Ver Galeria de Fotos", key=f"ver_fotos_{row['id']}"):
                                        lista_caminhos = galeria['caminho_foto'].tolist()
                                        # Filtra para garantir que arquivos existem
                                        fotos_reais = [f for f in lista_caminhos if os.path.exists(f)]
                                        
                                        if fotos_reais:
                                            # Mostra as fotos em grade
                                            st.image(fotos_reais, width=200, caption=[f"Foto {i+1}" for i in range(len(fotos_reais))])
                                        else:
                                            st.warning("Arquivos de foto não encontrados na pasta.")
                                else:
                                    st.caption("Nenhuma foto anexada.")

                            # --- ABA 2: AÇÕES (AQUI APLICAMOS A TRAVA "FINALIZADO") ---
                            with t_acao:
                                
                                # SE ESTIVER FINALIZADO: MOSTRA APENAS AVISO
                                if row['status'] == 'Finalizado':
                                    st.markdown("""
                                        <div style='background-color: #e8f5e9; padding: 10px; border-radius: 5px; border: 1px solid #4CAF50;'>
                                            <h4 style='color: #2e7d32; margin:0;'>🔒 Evento Finalizado</h4>
                                            <p style='font-size: 14px; margin:0;'>Edição bloqueada para segurança.</p>
                                        </div>
                                    """, unsafe_allow_html=True)
                                    st.info("Para alterar este evento, contate o administrador do banco de dados.")
                                
                                # SE ESTIVER ATIVO: LIBERA TUDO
                                else:
                                    # 1. Upload de Múltiplas Fotos
                                    st.write("**Adicionar Fotos:**")
                                    # accept_multiple_files=True permite selecionar 15 fotos de uma vez
                                    novas_fotos = st.file_uploader("Selecione fotos", type=['jpg','png'], accept_multiple_files=True, key=f"up_{row['id']}")
                                    
                                    if novas_fotos:
                                        if st.button(f"Salvar {len(novas_fotos)} Fotos", key=f"sf_{row['id']}"):
                                            if not os.path.exists("fotos_eventos"): os.makedirs("fotos_eventos")
                                            
                                            con = pegar_conexao()
                                            for foto in novas_fotos:
                                                # Gera nome único para não sobrescrever
                                                nome_arquivo = f"fotos_eventos/ev_{row['id']}_{int(time.time())}_{foto.name}"
                                                with open(nome_arquivo, "wb") as f: f.write(foto.getbuffer())
                                                
                                                # Salva na tabela nova (album_fotos)
                                                con.execute("INSERT INTO album_fotos (id_evento, caminho_foto) VALUES (?, ?)", (row['id'], nome_arquivo))
                                            
                                            # Atualiza a coluna antiga só para ter uma capa (opcional)
                                            con.execute("UPDATE eventos SET prova_foto = ? WHERE id = ?", ("Multiplas", row['id']))
                                            con.commit()
                                            con.close()
                                            st.success("Fotos adicionadas ao álbum!")
                                            time.sleep(1)
                                            st.rerun()

                                    st.markdown("---")
                                    
                                    # 2. Mudar Status
                                    st.write("**Atualizar Situação:**")
                                    ops = ["Agendado", "Em Andamento", "Finalizado"]
                                    idx = ops.index(row['status'])
                                    n_st = st.selectbox("Status", ops, index=idx, key=f"st_{row['id']}", label_visibility="collapsed")
                                    
                                    if st.button("Gravar Status", key=f"btn_{row['id']}"):
                                        con = pegar_conexao()
                                        # Trava: Pendências de Material
                                        pend = pd.read_sql_query(f"SELECT COUNT(*) as t FROM movimentacoes WHERE id_evento={row['id']}", con).iloc[0]['t']
                                        
                                        # Trava: Pelo menos 1 foto no álbum
                                        tem_album = pd.read_sql_query(f"SELECT COUNT(*) as t FROM album_fotos WHERE id_evento={row['id']}", con).iloc[0]['t']
                                        
                                        if n_st == "Finalizado":
                                            if pend > 0:
                                                st.error(f"🚫 Bloqueado: Há {pend} itens na rua!")
                                                st.stop()
                                            if tem_album == 0 and not novas_fotos:
                                                st.error("🚫 Bloqueado: É obrigatório ter pelo menos 1 foto no álbum!")
                                                st.stop()
                                        
                                        con.execute("UPDATE eventos SET status = ? WHERE id = ?", (n_st, row['id']))
                                        con.commit()
                                        con.close()
                                        st.success("Status atualizado!")
                                        st.rerun()
                                    
                                    st.markdown("---")
                                    # 3. Excluir
                                    if st.button("🗑️ Excluir Evento", key=f"del_{row['id']}"):
                                        con = pegar_conexao()
                                        con.execute("DELETE FROM movimentacoes WHERE id_evento=?", (row['id'],))
                                        con.execute("DELETE FROM album_fotos WHERE id_evento=?", (row['id'],)) # Limpa fotos também
                                        con.execute("DELETE FROM eventos WHERE id=?", (row['id'],))
                                        con.commit()
                                        con.close()
                                        st.rerun()
        con.close()

    # --- ABA EQUIPE ---
    with aba_equipe:
        c1, c2 = st.columns(2)
        with c1:
            nm = st.text_input("Nome")
            cg = st.selectbox("Cargo", ["Montador", "Coordenador", "Motorista"])
            if st.button("Adicionar Membro"):
                con = pegar_conexao()
                con.execute("INSERT INTO membros (nome, cargo) VALUES (?, ?)", (nm, cg))
                con.commit()
                con.close()
                st.success("Adicionado!")
                st.rerun()
        with c2:
            con = pegar_conexao()
            membros = pd.read_sql_query("SELECT * FROM membros", con)
            con.close()
            if not membros.empty:
                me = st.selectbox("Remover quem?", membros['nome'].tolist())
                if st.button("🗑️ Remover Membro"):
                    con = pegar_conexao()
                    con.execute("DELETE FROM membros WHERE nome = ?", (me,))
                    con.commit()
                    con.close()
                    st.rerun()

    # --- ABA NOVO EVENTO ---
    with aba_novo:
        st.subheader("📝 Agendar Novo Evento")
        with st.form("novo_ev"):
            c1, c2 = st.columns(2)
            with c1:
                nome_ev = st.text_input("Nome do Evento (ex: Copa Vale Paraibana)")
            with c2:
                end_ev = st.text_input("Endereço / Local")
            
            dt = st.date_input("Data do Evento")
            
            con = pegar_conexao()
            lista_m = pd.read_sql_query("SELECT nome FROM membros", con)['nome'].tolist()
            con.close()
            
            eq = st.multiselect("Equipe Escalada", lista_m)
            
            if st.form_submit_button("Criar Evento"):
                if nome_ev and end_ev:
                    # Juntamos Nome e Endereço para facilitar a visualização no resto do sistema
                    identificacao_completa = f"{nome_ev} | {end_ev}"
                    
                    con = pegar_conexao()
                    con.execute("INSERT INTO eventos (endereco, data_evento, status, equipe_nomes) VALUES (?, ?, 'Agendado', ?)", 
                                (identificacao_completa, str(dt), ", ".join(eq)))
                    con.commit()
                    con.close()
                    st.success(f"Evento '{nome_ev}' criado com sucesso!")
                else:
                    st.warning("Preencha o Nome e o Endereço.")

    # --- ABA SAÍDA (AGORA COM TRAVA DE ESTOQUE) ---
    with aba_logistica:
        st.subheader("🚚 Registrar Saída de Material")
        
        con = pegar_conexao()
        # Buscamos eventos ativos e a lista de itens completa
        ev_a = pd.read_sql_query("SELECT id, endereco FROM eventos WHERE status != 'Finalizado'", con)
        its = pd.read_sql_query("SELECT * FROM itens", con)
        con.close()
        
        if ev_a.empty:
            st.warning("⚠️ Não há eventos ativos (Agendados ou Em Andamento).")
        elif its.empty:
            st.warning("⚠️ Não há itens cadastrados no estoque.")
        else:
            col_out1, col_out2, col_out3 = st.columns(3)
            
            # Seletor de Evento
            ev_sel = col_out1.selectbox("Para qual Evento?", ev_a['id'].tolist(), format_func=lambda x: ev_a[ev_a['id']==x]['endereco'].values[0])
            
            # Seletor de Item
            id_item_sel = col_out2.selectbox("Qual Item?", its['id'].tolist(), format_func=lambda x: its[its['id']==x]['nome_item'].values[0])
            
            # Input de Quantidade
            qtd_saida = col_out3.number_input("Quantidade", min_value=1, value=1)
            
            # Botão de Enviar com verificação
            if st.button("Registrar Saída 🚚", type="primary"):
                con = pegar_conexao()
                
                # 1. CÁLCULO DE DISPONIBILIDADE
                # Descobre quanto desse item já está na rua (em outros eventos)
                query_uso = f"SELECT SUM(quantidade) FROM movimentacoes WHERE id_item = {id_item_sel}"
                qtd_usada = pd.read_sql_query(query_uso, con).iloc[0,0]
                
                # Se não tiver nada na rua, considera 0
                if qtd_usada is None: qtd_usada = 0
                
                # Pega a quantidade total do cadastro
                qtd_total_item = its[its['id'] == id_item_sel]['quantidade'].values[0]
                
                # Conta final
                qtd_disponivel = qtd_total_item - qtd_usada
                
                # 2. A TRAVA DE SEGURANÇA
                if qtd_saida > qtd_disponivel:
                    st.error(f"🚫 PROIBIDO: Estoque insuficiente!")
                    st.write(f"Você tentou enviar **{qtd_saida}**, mas só tem **{qtd_disponivel}** disponíveis na sede.")
                    st.info(f"Total Cadastrado: {qtd_total_item} | Já em uso: {qtd_usada}")
                else:
                    # Se tiver saldo, libera a gravação
                    con.execute("INSERT INTO movimentacoes (id_evento, id_item, quantidade, destino) VALUES (?, ?, ?, ?)", (ev_sel, id_item_sel, qtd_saida, "Evento"))
                    con.commit()
                    st.success(f"✅ Sucesso! Saída registrada.")
                    time.sleep(1)
                    st.rerun()
                
                con.close()

    # --- ABA RETORNO (CORRIGIDA: ERRO DE TIPO BYTES) ---
    with aba_retorno:
        st.subheader("🔙 Retorno de Material")
        st.info("Selecione o item e diga a quantidade que voltou para a base.")

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
            st.dataframe(movs, use_container_width=True)
            st.divider()

            col_dev1, col_dev2, col_dev3 = st.columns([3, 2, 2])
            
            with col_dev1:
                # Lista explicativa
                lista_opcoes = movs.apply(lambda x: f"{x['id']} - {x['nome_item']} (No local: {x['quantidade']}) em {x['endereco']}", axis=1).tolist()
                selecao = st.selectbox("Selecione a Movimentação:", lista_opcoes)
            
            # --- AQUI ESTAVA O ERRO ---
            # Pegamos o ID
            id_mov_selecionado = int(selecao.split(" - ")[0])
            
            # CORREÇÃO: Envolvemos tudo num int() para garantir que é número, não bytes
            qtd_maxima_no_local = int(movs[movs['id'] == id_mov_selecionado]['quantidade'].values[0])

            with col_dev2:
                # Agora o Streamlit não vai reclamar, pois max_value é int
                qtd_devolver = st.number_input("Qtd a Devolver", min_value=1, max_value=qtd_maxima_no_local, value=qtd_maxima_no_local)

            with col_dev3:
                st.write("") 
                st.write("") 
                if st.button("Confirmar Retorno 📥", type="primary"):
                    con = pegar_conexao()
                    
                    if qtd_devolver == qtd_maxima_no_local:
                        con.execute("DELETE FROM movimentacoes WHERE id = ?", (id_mov_selecionado,))
                        msg = "Devolução total concluída! Item removido da lista."
                    else:
                        nova_qtd = qtd_maxima_no_local - qtd_devolver
                        con.execute("UPDATE movimentacoes SET quantidade = ? WHERE id = ?", (nova_qtd, id_mov_selecionado))
                        msg = f"Devolução parcial! {qtd_devolver} voltaram, {nova_qtd} continuam lá."
                    
                    con.commit()
                    con.close()
                    st.success(msg)
                    time.sleep(1.5)
                    st.rerun()