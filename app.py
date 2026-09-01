import streamlit as st
from google import genai
import time
import re

# 1. Configuração visual
st.set_page_config(page_title="Assistente SGI - Moura Dubeux", page_icon="👷")
st.title("👷 Assistente SGI - Infinity")
st.markdown("Consulta com Arquitetura de Fatiamento. Rápido, leve e imune a travamentos.")

# 2. Conexão com o Google
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(
    api_key=API_KEY,
    http_options={'headers': {'x-goog-api-key': API_KEY}}
)

# 3. NOVO SISTEMA: Fatiamento do Arquivo (Evita estouro de Memória RAM)
@st.cache_data
def carregar_e_fatiar_sgi():
    try:
        with open('SGI_Completo.txt', 'r', encoding='utf-8') as f:
            texto = f.read()
        
        # Divide por arquivos primeiro
        arquivos_brutos = texto.split("[ARQUIVO:")
        pedacos = []
        
        for arq in arquivos_brutos:
            if len(arq.strip()) < 10: continue
            
            linhas = arq.split("\n", 1)
            nome_arq = linhas[0].replace("]", "").strip()
            conteudo = linhas[1] if len(linhas) > 1 else ""
            
            # Corta o conteúdo da norma em pedaços leves de 2000 caracteres
            tamanho_pedaco = 2000
            for i in range(0, len(conteudo), tamanho_pedaco):
                trecho = conteudo[i:i+tamanho_pedaco]
                pedacos.append({"arquivo": nome_arq, "texto": trecho})
                
        return pedacos
    except Exception as e:
        return []

lista_pedacos = carregar_e_fatiar_sgi()

# 4. BUSCA CIRÚRGICA NOS PEDAÇOS (Gasta quase nada da cota do Google)
def buscar_melhores_trechos(pergunta, pedacos):
    if not pedacos: return "Base de dados vazia."
    
    # Extrai as palavras que você digitou
    palavras_chave = [p.lower() for p in re.findall(r'\b\w+\b', pergunta) if len(p) > 2]
    
    for pedaco in pedacos:
        texto_lower = pedaco["texto"].lower()
        pontuacao = 0
        for palavra in palavras_chave:
            pontuacao += texto_lower.count(palavra)
        
        # Bônus para buscas críticas da engenharia
        if "pes 28" in pergunta.lower() and ("pes 28" in texto_lower or "pes_28" in texto_lower):
            pontuacao += 50
        if "esgoto" in pergunta.lower() and "ramal" in pergunta.lower() and "esgoto" in texto_lower and "ramal" in texto_lower:
            pontuacao += 20
            
        pedaco["pontuacao"] = pontuacao
        
    # Organiza do melhor para o pior
    pedacos_ordenados = sorted(pedacos, key=lambda x: x["pontuacao"], reverse=True)
    
    # Separa APENAS os 5 melhores recortes para mandar para a IA
    melhores = pedacos_ordenados[:5]
    
    resultado = ""
    for m in melhores:
        if m["pontuacao"] > 0:
            resultado += f"\n\n--- FONTE: {m['arquivo']} ---\n{m['texto']}...\n"
            
    if not resultado.strip():
        resultado = "Nenhuma norma específica encontrada sobre isso. Peça mais detalhes."
        
    return resultado

# 5. Memória Leve do Chat
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if pergunta := st.chat_input("Ex: Qual PES fala sobre ramal de esgoto?"):
    
    with st.chat_message("user"):
        st.markdown(pergunta)
    st.session_state.mensagens.append({"role": "user", "content": pergunta})

    # Puxa apenas a sua última pergunta para não pesar a memória
    historico_formatado = ""
    for m in st.session_state.mensagens[-2:]: 
        quem = "Usuário" if m["role"] == "user" else "Assistente"
        historico_formatado += f"\n{quem}: {m['content']}\n"

    with st.chat_message("assistant"):
        resposta_ui = st.empty()
        resposta_ui.markdown("🔎 *Escaneando as normas e processando...*")
        
        trechos_filtrados = buscar_melhores_trechos(pergunta, lista_pedacos)
        
        prompt = f"""
        Você é Engenheiro de Produção, atuando como consultor de qualidade da obra.
        Responda à dúvida do usuário com base EXCLUSIVAMENTE nos trechos do SGI abaixo.
        Seja prático e SEMPRE cite a Fonte (nome do arquivo) logo no início da sua explicação.
        
        TRECHOS DO SGI ENCONTRADOS:
        {trechos_filtrados}
        
        PERGUNTA DO USUÁRIO: {pergunta}
        """
        
        try:
            resposta = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            resposta_final = resposta.text
        except Exception as e:
            resposta_final = f"⚠️ Erro de servidor. Detalhe: {str(e)}"
        
        resposta_ui.markdown(resposta_final)
        
    st.session_state.mensagens.append({"role": "assistant", "content": resposta_final})
