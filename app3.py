import streamlit as st
import pandas as pd
import requests
from io import StringIO
import json
import os
from collections import defaultdict

# Configuração da página com layout amplo
st.set_page_config(page_title="Dashboard Lotofácil Pro", layout="wide")

# Arquivos locais para congelar jogos e histórico
ARQUIVO_JOGOS = "jogos_salvos.json"
ARQUIVO_HISTORICO = "historico_conferencia.json"

# 🎨 INJEÇÃO DE CSS COMPLETO (LIGHT MODE DE ALTO CONTRASTE E CORREÇÃO DE FONTE)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600;700&display=swap');
    
    .stApp {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'Inter', sans-serif;
    }
    
    .main-title {
        font-size: 30px; font-weight: 700; color: #0F172A; margin-bottom: 2px;
    }
    .sub-title {
        font-size: 14px; color: #475569; margin-bottom: 20px; font-weight: 500;
    }
    
    .light-card {
        background-color: #FFFFFF !important; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #E2E8F0 !important; 
        margin-bottom: 20px;
        box-shadow: 0px 4px 10px rgba(15, 23, 42, 0.02);
    }
    
    /* Correção de fontes claras em componentes nativos do Streamlit */
    [data-testid="stMetricValue"] {
        color: #0F172A !important;
    }
    [data-testid="stMetricLabel"] {
        color: #475569 !important;
    }
    div[data-testid="stMarkdownContainer"] p {
        color: #0F172A !important;
    }
    .stAlert p {
        color: #78350F !important;
    }
    
    .block-header {
        font-size: 14px; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 12px;
    }
    
    .trend-box {
        padding: 12px 5px; 
        text-align: center; 
        border-radius: 8px; 
        line-height: 1.3;
        box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.05);
        font-family: 'Inter', sans-serif;
    }
    .trend-text-main {
        font-size: 24px; font-weight: 800; display: block; margin-bottom: 2px;
    }
    .trend-text-sub {
        font-size: 11px; font-weight: 700; display: block; margin-bottom: 6px;
    }
    
    .stTabs [data-baseweb="tab"] p {
        color: #475569 !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] p {
        color: #2563EB !important;
    }

    .div-botao-salvar {
        text-align: center;
        margin-top: 30px;
        margin-bottom: 30px;
    }
    </style>
    """, unsafe_allow_html=True
)

st.markdown("<div class='main-title'>📊 Dashboard de Análise Preditiva</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Estatísticas completas, distribuição tática por tendências e persistência de histórico.</div>", unsafe_allow_html=True)

# Funções de persistência
def salvar_jogos_atuais(concurso, jogos_list, fixos_list, excluidos_list):
    dados = {
        "concurso_gerado": int(concurso), 
        "jogos": [list(j) for j in jogos_list],
        "fixos": list(fixos_list),
        "excluidos": list(excluidos_list)
    }
    with open(ARQUIVO_JOGOS, "w") as f:
        json.dump(dados, f)

def carregar_jogos_salvos():
    if os.path.exists(ARQUIVO_JOGOS):
        with open(ARQUIVO_JOGOS, "r") as f:
            dados = json.load(f)
            dados["jogos"] = [set(j) for j in dados["jogos"]]
            dados["fixos"] = set(dados.get("fixos", []))
            dados["excluidos"] = set(dados.get("excluidos", []))
            return dados
    return None

def salvar_no_historico(concurso_conferido, resultados_volantes, dezenas_sorteadas, analise_filtros):
    historico = []
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, "r") as f:
            historico = json.load(f)
    if any(h["concurso"] == concurso_conferido for h in historico):
        return
    historico.append({
        "concurso": concurso_conferido, 
        "sorteio": dezenas_sorteadas, 
        "desempenho": resultados_volantes,
        "analise_filtros": analise_filtros
    })
    with open(ARQUIVO_HISTORICO, "w") as f:
        json.dump(historico, f)

def carregar_historico():
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, "r") as f:
            return json.load(f)
    return []

def calcular_matriz_probabilidades(df):
    df_concursos = df[df.iloc[:, 0].astype(str).str.strip().str.isnumeric()].copy()
    df_cronologico = df_concursos.iloc[::-1].reset_index(drop=True)
    
    Gatilhos_seq, Sucessos_seq = {k:0 for k in range(1,7)}, {k:0 for k in range(1,7)}
    Gatilhos_atr, Sucessos_atr = {k:0 for k in range(1,5)}, {k:0 for k in range(1,5)}
    
    for col in range(1, 26):
        seq_atual, atr_atual = 0, 0
        for i in range(len(df_cronologico)):
            celula = df_cronologico.iloc[i, col]
            foi_sorteado = pd.notna(celula) and str(celula).strip() != ""
            
            if seq_atual in Gatilhos_seq:
                Gatilhos_seq[seq_atual] += 1
                if foi_sorteado: Sucessos_seq[seq_atual] += 1
            if atr_atual in Gatilhos_atr:
                Gatilhos_atr[atr_atual] += 1
                if not foi_sorteado: Sucessos_atr[atr_atual] += 1
            
            if foi_sorteado:
                seq_atual += 1; atr_atual = 0
            else:
                atr_atual += 1; seq_atual = 0
                
    prob_retorno_seq = {k: (Sucessos_seq[k] / Gatilhos_seq[k] * 100 if Gatilhos_seq[k] > 0 else 50.0) for k in Gatilhos_seq}
    prob_retorno_atr = {k: (100 - (Sucessos_atr[k] / Gatilhos_atr[k] * 100) if Gatilhos_atr[k] > 0 else 50.0) for k in Gatilhos_atr}
    return prob_retorno_seq, prob_retorno_atr

# 🧠 FUNÇÃO DO CICLO REESTRUTURADA E FILTRADA CRONOLOGICAMENTE
def mapear_ciclo_atual(df):
    # Filtra mantendo apenas os concursos reais numéricos
    df_concursos = df[df.iloc[:, 0].astype(str).str.strip().str.isnumeric()].copy()
    
    sorteados_no_ciclo = set()
    concursos_no_ciclo = 0
    
    # Inverte para ler do concurso mais antigo para o mais recente (ordem cronológica de fatos)
    df_cronologico = df_concursos.iloc[::-1].reset_index(drop=True)
    
    for i in range(len(df_cronologico)):
        linha = df_cronologico.iloc[i]
        
        # Coleta dezenas sorteadas na linha atual
        dezenas_sorteadas = set([
            col for col in range(1, 26) 
            if pd.notna(linha.iloc[col]) and str(linha.iloc[col]).strip() != ""
        ])
        
        sorteados_no_ciclo.update(dezenas_sorteadas)
        concursos_no_ciclo += 1
        
        # Se atingiu as 25 dezenas, o ciclo fechou. Reseta para começar a contar o próximo ciclo aberto
        if len(sorteados_no_ciclo) == 25:
            sorteados_no_ciclo = set()
            concursos_no_ciclo = 0
            
    # O que restar em "sorteados_no_ciclo" após o fim do loop pertence ao ciclo inacabado atual
    dezenas_faltantes = sorted([d for d in range(1, 26) if d not in sorteados_no_ciclo])
    return concursos_no_ciclo, dezenas_faltantes

@st.cache_data(ttl=3600)
def carregar_dados_base():
    url = "https://www.mazusoft.com.br/lotofacil/tabela-comportamento.php"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # Usamos o requests para pegar o conteúdo bruto
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return f"Erro na conexão: {r.status_code}", False
            
        # O segredo: especificar o parser 'html5lib' ou 'lxml' explicitamente
        df_list = pd.read_html(StringIO(r.text), flavor='bs4')
        if not df_list:
            return "Nenhuma tabela encontrada na página", False
            
        return df_list[0], True
    except Exception as e:
        return f"Erro técnico: {str(e)}", False

df_bruto, sucesso_carga = carregar_dados_base()

if sucesso_carga:
    ultimo_concurso_num = df_bruto.iloc[0, 0]
    prob_seq, prob_atr = calcular_matriz_probabilidades(df_bruto)
    concursos_ciclo_atual, dezenas_faltantes_ciclo = mapear_ciclo_atual(df_bruto)
    
    linha_seq = df_bruto[df_bruto.iloc[:, 0] == "Sequência"].index[0]
    linha_atr = df_bruto[df_bruto.iloc[:, 0] == "Atrasos"].index[0]
    
    lista_dezenas_analise = []
    for col in range(1, 26):
        sf = int(df_bruto.iloc[linha_seq, col])
        af = int(df_bruto.iloc[linha_atr, col])
        status_t = f"{sf} Seg." if sf > 0 else f"{af} Atr."
        peso = sf if sf > 0 else -af
        probabilidade_sorteio = prob_seq.get(sf, 50.0) if sf > 0 else prob_atr.get(af, 50.0)
        lista_dezenas_analise.append({
            "dezena": col, "prob_retorno": probabilidade_sorteio, "prob_falha": 100.0 - probabilidade_sorteio,
            "peso": peso, "status": status_t, "tipo": "Sorteada" if sf > 0 else "Ausente"
        })
        
    df_score_global = pd.DataFrame(lista_dezenas_analise)
    df_sorteadas = df_score_global[df_score_global["tipo"] == "Sorteada"].sort_values(by="peso", ascending=False)
    df_ausentes = df_score_global[df_score_global["tipo"] == "Ausente"].sort_values(by="peso", ascending=True)

    def obter_estilo_tendencia(status):
        if "Seg." in status:
            num_seg = int(status.split()[0])
            if num_seg == 1: return "#16A34A", "#FFFFFF", "background:#22C55E; color:white;", "background:#EF4444; color:white;"
            elif num_seg == 2: return "#14532D", "#FFFFFF", "background:#16A34A; color:white;", "background:#EF4444; color:white;"
            elif num_seg == 3: return "#0891B2", "#FFFFFF", "background:#06B6D4; color:white;", "background:#EF4444; color:white;"
            elif num_seg == 4: return "#2563EB", "#FFFFFF", "background:#3B82F6; color:white;", "background:#EF4444; color:white;"
            else: return "#4338CA", "#FFFFFF", "background:#4F46E5; color:white;", "background:#EF4444; color:white;"
        elif "Atr." in status:
            num_atr = int(status.split()[0])
            if num_atr <= 1: return "#D97706", "#FFFFFF", "background:#F59E0B; color:white;", "background:#EF4444; color:white;"
            elif num_atr == 2: return "#EA580C", "#FFFFFF", "background:#F97316; color:white;", "background:#EF4444; color:white;"
            elif num_atr == 3: return "#78350F", "#FFFFFF", "background:#92400E; color:white;", "background:#EF4444; color:white;"
            else: return "#DC2626", "#FFFFFF", "background:#EF4444; color:white;", "background:#FCA5A5; color:#7F1D1D;"
        return "#FFFFFF", "#0F172A", "background:#E2E8F0; color:#0F172A;", "background:#E2E8F0; color:#0F172A;"

    # 1. Seleção estrita de Fixos e Excluídos por linha
    fixos, excluidos = set(), set()
    linhas_lotofacil = [{"faixa": range(1, 6)}, {"faixa": range(6, 11)}, {"faixa": range(11, 16)}, {"faixa": range(16, 21)}, {"faixa": range(21, 26)}]
    
    dados_justificativa_escolhas = []
    for item in linhas_lotofacil:
        df_linha = df_score_global[df_score_global["dezena"].isin(item["faixa"])].copy()
        
        df_linha_fixos = df_linha.sort_values(by=["prob_retorno", "peso"], ascending=[False, False])
        b_fixa = int(df_linha_fixos.iloc[0]["dezena"])
        fixos.add(b_fixa)
        
        df_linha_excluidos = df_linha[df_linha["dezena"] != b_fixa].sort_values(by=["prob_retorno", "peso"], ascending=[True, True])
        b_excluida = int(df_linha_excluidos.iloc[0]["dezena"])
        excluidos.add(b_excluida)
        
        for d in item["faixa"]:
            row_d = df_linha[df_linha["dezena"] == d].iloc[0]
            status_escolha = "📌 FIXA (Maior Prob. da Linha)" if d == b_fixa else ("❌ EXCLUÍDA (Menor Prob. da Linha)" if d == b_excluida else "🔄 NEUTRA")
            dados_justificativa_escolhas.append({
                "Linha": f"Faixa {item['faixa'].start} a {item['faixa'].stop-1}",
                "Dezena": f"{d:02d}",
                "Prob. Sair": f"{row_d['prob_retorno']:.1f}%",
                "Estado": row_d["status"],
                "Definição Estratégica": status_escolha
            })

    neutros = [d for d in range(1, 26) if d not in fixos and d not in excluidos]
    
    grupos_tendencia = defaultdict(list)
    for n in neutros:
        status_n = df_score_global[df_score_global["dezena"] == n].iloc[0]["status"]
        grupos_tendencia[status_n].append(n)
        
    bloco_A, bloco_B, bloco_C = [], [], []
    ponteiro_bloco = 0
    
    for status_grupo, dezenas_grupo in grupos_tendencia.items():
        for d in dezenas_grupo:
            if ponteiro_bloco == 0: bloco_A.append(d)
            elif ponteiro_bloco == 1: bloco_B.append(d)
            else: bloco_C.append(d)
            ponteiro_bloco = (ponteiro_bloco + 1) % 3

    todos_blocos = [bloco_A, bloco_B, bloco_C]
    dezenas_removidas = []
    
    for b in todos_blocos:
        while len(b) > 5:
            dezenas_removidas.append(b.pop())
            
    for b in todos_blocos:
        while len(b) < 5 and dezenas_removidas:
            b.append(dezenas_removidas.pop())

    jogos_finais = [
        set(bloco_A + bloco_B),  
        set(bloco_A + bloco_C),  
        set(bloco_B + bloco_C)   
    ]

    jogos_completos_atuais = [fixos.union(j) for j in jogos_finais]
    jogos_salvos_memoria = carregar_jogos_salvos()
    if not jogos_salvos_memoria or jogos_salvos_memoria["concurso_gerado"] != int(ultimo_concurso_num):
        salvar_jogos_atuais(ultimo_concurso_num, jogos_completos_atuais, fixos, excluidos)

    tab_analise, tab_historico = st.tabs(["🎯 Análise e Volantes de Hoje", "💾 Histórico & Auditoria"])
    
    with tab_analise:
        st.markdown("<div class='light-card' style='border-left: 5px solid #2563EB;'>", unsafe_allow_html=True)
        st.write(f"📌 **Concurso Base:** {ultimo_concurso_num} | **Regra Ativa:** Fechamento Matemático Estrito 2/3 (Cada uma das 15 neutras aparece em exatamente 2 jogos).")
        st.markdown("</div>", unsafe_allow_html=True)

        # 🔄 CARD DO CICLO ATUALIZADO (VISUAL BLINDADO CONTRA CONTRASTE RUIM)
        st.markdown("<div class='light-card' style='border-left: 5px solid #06B6D4;'>", unsafe_allow_html=True)
        st.markdown("<h3 style='color: #0F172A; margin-top:0;'>🔄 Rastreamento de Status do Ciclo Atual</h3>", unsafe_allow_html=True)
        col_ciclo1, col_ciclo2 = st.columns([1, 3])
        with col_ciclo1:
            st.metric("Duração do Ciclo", f"{concursos_ciclo_atual} Concursos")
        with col_ciclo2:
            if dezenas_faltantes_ciclo:
                texto_faltantes = ", ".join([f"{d:02d}" for d in dezenas_faltantes_ciclo])
                st.markdown(
                    f"""
                    <div style='background-color: #FEF3C7; border: 1px solid #FCD34D; padding: 15px; border-radius: 8px;'>
                        <strong style='color: #92400E; font-size: 15px; display: block; margin-bottom: 4px;'>⚠️ Dezenas pendentes para fechar o Ciclo:</strong>
                        <span style='color: #78350F; font-size: 22px; font-weight: 800; display: block; margin-bottom: 6px;'>{texto_faltantes}</span>
                        <p style='color: #B45309; font-size: 12px; margin: 0;'>Nota: À medida que o ciclo avança, essas dezenas ganham um peso crítico de urgência para sorteio.</p>
                    </div>
                    """, unsafe_allow_html=True
                )
            else:
                st.markdown(
                    """
                    <div style='background-color: #DCFCE7; border: 1px solid #BBF7D0; padding: 15px; border-radius: 8px;'>
                        <strong style='color: #166534; font-size: 15px; display: block;'>🎉 O Ciclo fechou totalmente no concurso anterior!</strong>
                        <p style='color: #15803D; font-size: 12px; margin: 4px 0 0 0;'>Um novo ciclo inicia hoje com todas as 25 dezenas zeradas.</p>
                    </div>
                    """, unsafe_allow_html=True
                )
        st.markdown("</div>", unsafe_allow_html=True)

        # 🔥 LINE-UP DE TENDÊNCIAS
        st.markdown("<div class='light-card'>", unsafe_allow_html=True)
        st.subheader("📌 Linha de Referência de Tendência Atual")
        
        st.markdown("<div class='block-header' style='color: #0284C7;'>🔥 DEZENAS EM ALTA (SORTEIO RECENTE)</div>", unsafe_allow_html=True)
        if not df_sorteadas.empty:
            cols_sort = st.columns(len(df_sorteadas))
            for idx, row in enumerate(df_sorteadas.itertuples()):
                bg_color, text_color, tag_s, tag_f = obter_estilo_tendencia(row.status)
                with cols_sort[idx]:
                    st.markdown(
                        f"""
                        <div class='trend-box' style='background-color: {bg_color}; border: 1px solid {bg_color};'>
                            <span class='trend-text-main' style='color: {text_color} !important;'>{row.dezena:02d}</span>
                            <span class='trend-text-sub' style='color: {text_color} !important; opacity: 0.9;'>{row.status}</span>
                            <div style='margin-top: 4px; font-size: 10px;'>
                                <span style='{tag_s} padding: 2px 4px; border-radius: 4px; font-weight:700;'>S:{row.prob_retorno:.0f}%</span>
                            </div>
                            <div style='margin-top: 3px; font-size: 10px;'>
                                <span style='{tag_f} padding: 2px 4px; border-radius: 4px; font-weight:700;'>F:{row.prob_falha:.0f}%</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True
                    )
                    
        st.write("")
        st.markdown("<div class='block-header' style='color: #4F46E5;'>❄️ DEZENAS EM BAIXA (AUSENTES / ATRASADAS)</div>", unsafe_allow_html=True)
        if not df_ausentes.empty:
            cols_aus = st.columns(len(df_ausentes))
            for idx, row in enumerate(df_ausentes.itertuples()):
                bg_color, text_color, tag_s, tag_f = obter_estilo_tendencia(row.status)
                with cols_aus[idx]:
                    st.markdown(
                        f"""
                        <div class='trend-box' style='background-color: {bg_color}; border: 1px solid {bg_color};'>
                            <span class='trend-text-main' style='color: {text_color} !important;'>{row.dezena:02d}</span>
                            <span class='trend-text-sub' style='color: {text_color} !important; opacity: 0.9;'>{row.status}</span>
                            <div style='margin-top: 4px; font-size: 10px;'>
                                <span style='{tag_s} padding: 2px 4px; border-radius: 4px; font-weight:700;'>S:{row.prob_retorno:.0f}%</span>
                            </div>
                            <div style='margin-top: 3px; font-size: 10px;'>
                                <span style='{tag_f} padding: 2px 4px; border-radius: 4px; font-weight:700;'>F:{row.prob_falha:.0f}%</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True
                    )
        st.markdown("</div>", unsafe_allow_html=True)

        # 📈 ESTATÍSTICAS INDIVIDUAIS POR DEZENA
        st.markdown("<div class='light-card'>", unsafe_allow_html=True)
        st.subheader("📈 Estatísticas Individuais por Dezena (Completo)")
        df_ranking_exibicao = df_score_global.sort_values(by="dezena", ascending=True).copy()
        df_ranking_exibicao["Dezena"] = df_ranking_exibicao["dezena"].apply(lambda x: f"Dezena {x:02d}")
        df_ranking_exibicao["Chance de Sair (S)"] = df_ranking_exibicao["prob_retorno"].apply("{:.1f}%".format)
        df_ranking_exibicao["Chance de Falhar (F)"] = df_ranking_exibicao["prob_falha"].apply("{:.1f}%".format)
        df_ranking_exibicao["Frequência / Estado Atual"] = df_ranking_exibicao["status"]
        st.dataframe(df_ranking_exibicao[["Dezena", "Chance de Sair (S)", "Chance de Falhar (F)", "Frequência / Estado Atual"]], use_container_width=True, hide_index=True, height=280)
        st.markdown("</div>", unsafe_allow_html=True)

        # 📋 PAINEL DE DEFINIÇÃO E JUSTIFICATIVA DE ESCOLHAS
        st.markdown("<div class='light-card'>", unsafe_allow_html=True)
        st.subheader("📋 Painel de Justificativa Teórica (Fixos, Excluídos e Neutros por Linha)")
        st.dataframe(pd.DataFrame(dados_justificativa_escolhas), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # 📋 AUDITORIA DE FREQUÊNCIA DAS DEZENAS NEUTRAS
        st.markdown("<div class='light-card'>", unsafe_allow_html=True)
        st.subheader("⚖️ Auditoria de Dispersão Balanceada (Regra de Ouro: Neutras em 2/3 dos Jogos)")
        dados_just_neutros = []
        for n in sorted(neutros):
            row_n = df_score_global[df_score_global["dezena"] == n].iloc[0]
            volantes_alocados = [f"Volante {i+1}" for i, j in enumerate(jogos_finais) if n in j]
            dados_just_neutros.append({
                "Dezena": f"{n:02d}", 
                "Estado Comportamental": row_n["status"], 
                "Total Aparições nos Jogos": f"{len(volantes_alocados)} vezes",
                "Onde foi Alocada": " & ".join(volantes_alocados)
            })
        st.dataframe(pd.DataFrame(dados_just_neutros), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # 🎰 SEUS 3 VOLANTES
        st.subheader("🎰 Seus 3 Volantes com Matriz 2/3 Perfeita")
        col_jogo1, col_jogo2, col_jogo3 = st.columns(3)
        quadros_jogos = [col_jogo1, col_jogo2, col_jogo3]
        for idx, col_painel in enumerate(quadros_jogos):
            with col_painel:
                jogo_atual = jogos_finais[idx]
                fixos_impares = sum(1 for d in fixos if d % 2 != 0)
                tot_imp = fixos_impares + sum(1 for d in jogo_atual if d % 2 != 0)
                st.markdown(f"<div style='background-color: #FFFFFF; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; font-weight: 700; color: #2563EB; font-size:15px;'>🎮 VOLANTE COMBINAÇÃO {idx + 1}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align: center; font-size: 12px; color: #64748B; margin-bottom: 16px;'><b>{tot_imp} Ímpares</b> / {15 - tot_imp} Pares</div>", unsafe_allow_html=True)
                for row in range(5):
                    cols_cartela = st.columns(5)
                    for col_idx in range(5):
                        numero = row * 5 + col_idx + 1
                        num_formatado = f"{numero:02d}"
                        if numero in fixos: cor_bg, cor_txt, borda = "#22C55E", "#FFFFFF", "1px solid #16A34A"
                        elif numero in excluidos: cor_bg, cor_txt, borda = "#EF4444", "#FFFFFF", "1px dashed #DC2626"
                        elif numero in jogo_atual: cor_bg, cor_txt, borda = "#2563EB", "#FFFFFF", "1px solid #1D4ED8"
                        else: cor_bg, cor_txt, borda = "#F1F5F9", "#94A3B8", "1px solid #E2E8F0"
                        with cols_cartela[col_idx]:
                            st.markdown(f"<div style='background-color: {cor_bg}; color: {cor_txt}; border: {borda}; padding: 8px 0px; text-align: center; font-weight: 700; border-radius: 6px; font-size: 13px; margin: 3px 0;'>{num_formatado}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='div-botao-salvar'>", unsafe_allow_html=True)
        if "clicou_salvar" not in st.session_state: st.session_state.clicou_salvar = False
        if st.session_state.clicou_salvar:
            st.button("✓ JOGOS SALVOS COM SUCESSO!", type="primary", key="btn_sucesso")
        else:
            if st.button("💾 CONGELAR E SALVAR ESTES JOGOS PARA CONFERIR AMANHÃ", key="btn_salvar"):
                salvar_jogos_atuais(ultimo_concurso_num, jogos_completos_atuais, fixos, excluidos)
                st.session_state.clicou_salvar = True
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_historico:
        st.subheader("💾 Conferência Automatizada e Diagnóstico Crítico de Performance")
        
        jogos_salvos_dados = carregar_jogos_salvos()
        if jogos_salvos_dados:
            concurso_origem = jogos_salvos_dados["concurso_gerado"]
            proximo_concurso_esperado = concurso_origem + 1
            st.info(f"📌 Existe um jogo salvo na memória gerado no **Concurso {concurso_origem}**.")
            
            if str(ultimo_concurso_num).isnumeric() and int(ultimo_concurso_num) >= proximo_concurso_esperado:
                st.success(f"🎉 Resultado do **Concurso {ultimo_concurso_num}** processado!")
                linha_resultado = df_bruto[df_bruto.iloc[:,0].astype(str).str.strip().str.isnumeric()].iloc[0]
                dezenas_sorteadas_no_concurso = [col for col in range(1, 26) if pd.notna(linha_resultado.iloc[col]) and str(linha_resultado.iloc[col]).strip() != ""]
                set_sorteados = set(dezenas_sorteadas_no_concurso)
                
                fixos_salvos = jogos_salvos_dados["fixos"] if jogos_salvos_dados["fixos"] else fixos
                excluidos_salvos = jogos_salvos_dados["excluidos"] if jogos_salvos_dados["excluidos"] else excluidos
                neutros_salvos = set([d for d in range(1, 26) if d not in fixos_salvos and d not in excluidos_salvos])
                
                acertos_fixos = len(fixos_salvos.intersection(set_sorteados))
                acertos_excluidos = len(excluidos_salvos.intersection(set_sorteados))
                acertos_neutros = len(neutros_salvos.intersection(set_sorteados))
                
                dados_analise_filtros = {
                    "acertos_fixos": acertos_fixos,
                    "acertos_excluidos": acertos_excluidos,
                    "acertos_neutros": acertos_neutros
                }
                
                resultados_auditoria = {}
                cols_auditoria = st.columns(3)
                for idx, jogo_antigo in enumerate(jogos_salvos_dados["jogos"]):
                    acertos = jogo_antigo.intersection(set_sorteados)
                    qtd_acertos = len(acertos)
                    resultados_auditoria[f"Volante {idx+1}"] = qtd_acertos
                    with cols_auditoria[idx]:
                        st.metric(label=f"🎯 Pontos no Volante {idx+1}", value=f"{qtd_acertos} acertos")
                        st.write(f"Acertou: {sorted(list(acertos))}")
                        
                salvar_no_historico(int(ultimo_concurso_num), resultados_auditoria, sorted(list(set_sorteados)), dados_analise_filtros)
            else:
                st.warning(f"⏳ Aguardando resultado do Concurso {proximo_concurso_esperado}. Atual no servidor: {ultimo_concurso_num}")
        else:
            st.write("Nenhum jogo foi salvo ainda.")
            
        lista_historico_acumulado = carregar_historico()
        
        if lista_historico_acumulado:
            st.markdown("<div class='light-card' style='border-top: 4px solid #EA580C;'>", unsafe_allow_html=True)
            st.subheader("🧠 Centro de Diagnóstico e Otimização de Filtros")
            
            total_concursos = len(lista_historico_acumulado)
            soma_fixos = sum(h.get("analise_filtros", {}).get("acertos_fixos", 0) for h in lista_historico_acumulado)
            soma_excluidos = sum(h.get("analise_filtros", {}).get("acertos_excluidos", 0) for h in lista_historico_acumulado)
            
            media_fixos = soma_fixos / total_concursos
            media_excluidos = soma_excluidos / total_concursos
            
            c_med1, c_med2, c_med3 = st.columns(3)
            with c_med1:
                st.metric("🎯 Média de Acertos nos 5 Fixos", f"{media_fixos:.1f} / 5")
            with c_med2:
                st.metric("🛑 Média de Acertos nos 5 Excluídos", f"{media_excluidos:.1f} / 5")
            with c_med3:
                st.metric("📊 Amostragem Auditada", f"{total_concursos} Concursos")
                
            st.markdown("##### 📝 Parecer Técnico para Engenharia de Melhoria:")
            if media_excluidos > 2.0:
                st.warning(f"⚠️ **Alerta no Filtro de Exclusão:** Suas dezenas excluídas estão saindo mais do que o esperado (média {media_excluidos:.1f}). Dica: Cruze os dados com o 'Rastreador de Ciclo' para checar se as dezenas excluídas não estão muito atrasadas cronologicamente.")
            elif media_fixos < 3.0:
                st.warning("⚠️ **Alerta no Filtro de Fixação:** Suas dezenas fixas estão com aproveitamento abaixo da zona matemática de conforto. Monitore dezenas pendentes de fim de ciclo para balancear esses pilares.")
            else:
                st.success("✅ **Filtros Estáveis:** Seus critérios matemáticos de linha estão performando dentro da zona de eficiência estatística.")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.write("##### 📋 Histórico Completo de Extrações")
            dados_tabela_hist = []
            for h in lista_historico_acumulado:
                f_ana = h.get("analise_filtros", {})
                dados_tabela_hist.append({
                    "Concurso Auditado": h["concurso"], 
                    "Números Sorteados": str(h["sorteio"]),
                    "Fixos Sorteados": f"{f_ana.get('acertos_fixos', '-')} / 5",
                    "Excluídos Sorteados": f"{f_ana.get('acertos_excluidos', '-')} / 5",
                    "Volante 1": f"{h['desempenho']['Volante 1']} pts", 
                    "Volante 2": f"{h['desempenho']['Volante 2']} pts", 
                    "Volante 3": f"{h['desempenho']['Volante 3']} pts"
                })
            
            df_exportar = pd.DataFrame(dados_tabela_hist)
            st.dataframe(df_exportar, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            csv_dados = df_exportar.to_csv(index=False).encode('utf-8-sig') 
            st.download_button(
                label="📥 EXPORTAR HISTÓRICO COMPLETO (BACKUP EXCEL)",
                data=csv_dados,
                file_name="backup_historico_lotofacil.csv",
                mime="text/csv",
                key="btn_download_backup"
            )
else:
    st.error(f"Erro no processamento dos dados: {df_bruto}")