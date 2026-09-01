import streamlit as st
from google import genai
import time

# 1. Configuração visual do aplicativo
st.set_page_config(page_title="Assistente SGI - Moura Dubeux", page_icon="👷")
st.title("👷 Assistente SGI - Infinity")
st.markdown("Consulte as normas do Sistema de Gestão Integrada. Sistema com auto-retry e leitura integral.")

# 2. Conexão com a API do Google
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(
    api_key=API_KEY,
    http_options={'headers': {'x-goog-api-key': API_KEY}}
)

# 3. Carregamento Inteligente (O @st.cache_data impede que o arquivo seja lido a cada pergunta, tornando-o super rápido)
@st.cache_data
def carregar_sgi():
    try:
        with open('SGI_Completo.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Erro ao ler o arquivo SGI_Completo.txt: {e}"

sgi_texto_integral = carregar_sgi()

# 4. Criação da memória contínua do chat
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

# Exibe o histórico de conversa na tela
for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. Caixa de entrada e processamento
if pergunta := st.chat_input("Digite sua dúvida (Ex: PES 28 ou Escavação da piscina)..."):
    
    # Mostra a pergunta na tela e salva na memória
    with st.chat_message("user"):
        st.markdown(pergunta)
    st.session_state.mensagens.append({"role": "user", "content": pergunta})

    # Formata o histórico para a inteligência artificial entender a linha de raciocínio
    historico_formatado = ""
    for m in st.session_state.mensagens:
        quem = "Usuário" if m["role"] == "user" else "Assistente"
        historico_formatado += f"\n{quem}: {m['content']}\n"

    prompt = f"""
    Você é um Engenheiro de Produção Sênior, atuando como mentor e consultor de qualidade da obra.
    Você tem acesso integral ao documento do Sistema de Gestão Integrada (SGI).
    
    SUA MISSÃO É ALIAR PRECISÃO COM INTELIGÊNCIA:
    1. PRECISÃO CIRÚRGICA: Se o usuário perguntar sobre um termo exato, PES específica ou métrica, rastreie o documento, entregue o dado real e cite o [ARQUIVO] de origem.
    2. INTELIGÊNCIA SEMÂNTICA: Se o serviço for atípico (ex: piscina) ou necessitar de interpretação, aja como engenheiro. Cruze as normas e justifique tecnicamente como o SGI ampara o serviço.
    3. TOM E FORMATO: Seja cordial, didático e consultivo. Explique o "porquê" das coisas. Organize suas respostas com listas e tópicos.
    
    HISTÓRICO DA CONVERSA:
    {historico_formatado}
    
    ARQUIVO DO SGI:
    {sgi_texto_integral}
    
    PERGUNTA DO USUÁRIO: {pergunta}
    """

    with st.chat_message("assistant"):
        resposta_ui = st.empty()
        resposta_ui.markdown("⏳ *Analisando a base do SGI...*")
        
        # Sistema de Auto-Retry Invisível
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
                resposta_final = f"⚠️ Instabilidade no servidor do Google. Erro: {erro_str}\n\nPor favor, tente novamente."
                break
        
        # Atualiza a tela com a resposta definitiva
        resposta_ui.markdown(resposta_final)
        
    # Salva a resposta da IA na memória
    st.session_state.mensagens.append({"role": "assistant", "content": resposta_final})
