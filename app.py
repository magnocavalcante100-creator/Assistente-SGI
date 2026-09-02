import streamlit as st
from google import genai
import time

# 1. Configuração visual
st.set_page_config(page_title="Assistente SGI - Moura Dubeux", page_icon="👷", layout="wide")
st.title("👷 Assistente SGI - Infinity (Potência Máxima)")
st.markdown("Visão Panorâmica Ativada: O assistente analisa todas as 63 PES simultaneamente com Inteligência Semântica.")

# 2. Conexão com o Google (Sem limitador de velocidade)
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(
    api_key=API_KEY,
    http_options={'headers': {'x-goog-api-key': API_KEY}}
)

# 3. LEITURA INTEGRAL (A Máquina Sênior)
@st.cache_data
def carregar_sgi_completo():
    try:
        with open('SGI_Completo.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Erro Crítico: Não foi possível ler a base de dados. Detalhe: {e}"

sgi_integral = carregar_sgi_completo()

# 4. Interface de Chat
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if pergunta := st.chat_input("Ex: Qual PES fala sobre ramal de esgoto? Pode cruzar as normas?"):
    
    with st.chat_message("user"):
        st.markdown(pergunta)
    st.session_state.mensagens.append({"role": "user", "content": pergunta})

    # O histórico salva as últimas 6 mensagens para ele lembrar do contexto perfeitamente
    historico_formatado = ""
    for m in st.session_state.mensagens[-6:]: 
        quem = "Usuário" if m["role"] == "user" else "Assistente"
        historico_formatado += f"\n{quem}: {m['content']}\n"

    with st.chat_message("assistant"):
        resposta_ui = st.empty()
        resposta_ui.markdown("🧠 *Analisando todo o SGI e elaborando o parecer técnico...*")
        
        # O SUPER PROMPT: Mente de Engenheiro Sênior
        prompt = f"""
        Você é um Engenheiro de Produção Sênior, especialista em Qualidade e processos da construção civil.
        Você atua como Consultor Técnico Sênior do Sistema de Gestão Integrada (SGI) no canteiro de obras.
        
        Abaixo, você receberá a BASE DE DADOS COMPLETA, contendo TODAS AS NORMAS (PES).
        
        SUA MISSÃO - LEIA COM ATENÇÃO:
        1. PRECISÃO EXTREMA: Jamais invente dados. Se a resposta não estiver na base de dados, diga que o SGI não cobre essa especificidade.
        2. CONTEXTO E SEMÂNTICA: Não seja um robô que apenas cospe o texto. Interprete o que foi pedido. Se o usuário perguntar de um serviço complexo, cruze informações de mais de uma PES se necessário (ex: fundação + impermeabilização).
        3. CITAÇÃO OBRIGATÓRIA: É terminantemente obrigatório começar a sua explicação informando o(s) [ARQUIVO(S)] da PES que você utilizou para fundamentar a resposta.
        4. DIDÁTICA DE ENGENHARIA: Explique o "porquê" das exigências. Organize suas ideias com listas, tópicos e formatação em negrito para facilitar a leitura no canteiro de obras. Fale como um engenheiro experiente orientando sua equipe.
        
        HISTÓRICO RECENTE DA CONVERSA:
        {historico_formatado}
        
        BASE DE DADOS INTEGRAL DO SGI:
        {sgi_integral}
        
        PERGUNTA DA EQUIPE DE OBRA: {pergunta}
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
                if ("503" in erro_str or "429" in erro_str) and tentativa < max_tentativas - 1:
                    resposta_ui.markdown(f"⏳ *Buscando conexão. Tentativa {tentativa + 2}...*")
                    time.sleep(4)
                    continue
                
                resposta_final = f"⚠️ Erro de rede ou limite atingido. Detalhe: {erro_str}"
                break
        
        resposta_ui.markdown(resposta_final)
        
    st.session_state.mensagens.append({"role": "assistant", "content": resposta_final})
