import streamlit as st
from google import genai
import time
import re

# 1. Configuração visual
st.set_page_config(page_title="Assistente SGI - Moura Dubeux", page_icon="👷")
st.title("👷 Assistente SGI - Infinity")
st.markdown("Consulta com Inteligência Híbrida. Rápido e sem limites de cota!")

# 2. Conexão com o Google
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(
    api_key=API_KEY,
    http_options={'headers': {'x-goog-api-key': API_KEY}}
)

# 3. Carregamento e Fatiamento do Banco de Dados
@st.cache_data
def carregar_sgi():
    try:
        with open('SGI_Completo.txt', 'r', encoding='utf-8') as f:
            texto = f.read()
            # O Python corta o arquivão em uma lista, separando cada PES individualmente
            normas = texto.split("[ARQUIVO:")
            return normas
    except Exception as e:
        return []

lista_normas = carregar_sgi()

# =====================================================================
# O NOVO MOTOR DE BUSCA (REDUZ O GASTO DE TOKENS EM 95%)
# =====================================================================
def buscar_normas_relevantes(pergunta, normas):
    if not normas:
        return "Erro: Base de dados vazia."
        
    # Extrai as palavras principais da pergunta do usuário
    palavras_chave = [p.lower() for p in re.findall(r'\b\w+\b', pergunta) if len(p) > 2]
    
    pontuacoes = []
    for norma in normas:
        norma_lower = norma.lower()
        pontuacao = 0
        
        # Pontua a norma se ela tiver as palavras que o usuário digitou
        for palavra in palavras_chave:
            pontuacao += norma_lower.count(palavra)
        
        # Super-Bônus para buscas exatas (Resolve o problema da PES 28)
        if "pes 28" in pergunta.lower() and ("pes 28" in norma_lower or "pes_28" in norma_lower):
            pontuacao += 1000
            
        pontuacoes.append((pontuacao, norma))
        
    # Organiza o ranking e seleciona apenas as 3 PES mais relevantes
    pontuacoes.sort(key=lambda x: x[0], reverse=True)
    textos_selecionados = ""
    for pontuacao, norma in pontuacoes[:3]:
        if pontuacao > 0:
            textos_selecionados += "\n\n[ARQUIVO:" + norma
            
    # Fallback caso a pergunta seja muito genérica
    if not textos_selecionados.strip():
        textos_selecionados = "\n\n[ARQUIVO:" + (normas[1][:5000] if len(normas) > 1 else "Nada encontrado.")
        
    return textos_selecionados

# 4. Memória do Chat
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. Processamento da Pergunta
if pergunta := st.chat_input("Digite sua dúvida (Ex: PES 28 ou ramal de esgoto)..."):
    
    with st.chat_message("user"):
        st.markdown(pergunta)
    st.session_state.mensagens.append({"role": "user", "content": pergunta})

    # Reduzimos o histórico para as últimas 4 mensagens para economizar cota
    historico_formatado = ""
    for m in st.session_state.mensagens[-4:]:
        quem = "Usuário" if m["role"] == "user" else "Assistente"
        historico_formatado += f"\n{quem}: {m['content']}\n"

    with st.chat_message("assistant"):
        resposta_ui = st.empty()
        resposta_ui.markdown("🔎 *Garimpando as PES e analisando...*")
        
        # ACIONA O FILTRO ANTES DE MANDAR PARA A INTELIGÊNCIA ARTIFICIAL
        sgi_filtrado = buscar_normas_relevantes(pergunta, lista_normas)
        
        prompt = f"""
        Você é um Engenheiro de Produção Sênior, consultor de qualidade da obra.
        Responda à dúvida do usuário usando APENAS as NORMAS SGI FILTRADAS abaixo.
        Seja prático. Cite a PES.
        
        HISTÓRICO RECENTE:
        {historico_formatado}
        
        NORMAS SGI FILTRADAS PARA ESTA PERGUNTA:
        {sgi_filtrado}
        
        PERGUNTA DO USUÁRIO: {pergunta}
        """
        
        max_tentativas = 3
        resposta_final = ""
        
        for tentativa in range(max_tentativas):
            try:
                resposta = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                resposta_final = resposta.text
                break
            except Exception as e:
                erro_str = str(e)
                if ("503" in erro_str or "UNAVAILABLE" in erro_str) and tentativa < max_tentativas - 1:
                    time.sleep(3)
                    continue
                resposta_final = f"⚠️ Erro de API. Detalhe: {erro_str}\n\nPor favor, tente novamente."
                break
        
        resposta_ui.markdown(resposta_final)
        
    st.session_state.mensagens.append({"role": "assistant", "content": resposta_final})
