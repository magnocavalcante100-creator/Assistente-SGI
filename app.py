import streamlit as st
from google import genai
import time
import re

# 1. Configuração visual
st.set_page_config(page_title="Assistente SGI - Moura Dubeux", page_icon="👷")
st.title("👷 Assistente SGI - Infinity")
st.markdown("Consulta Inteligente. O robô localiza a norma exata e lê apenas o necessário.")

# 2. Conexão com o Google
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(
    api_key=API_KEY,
    http_options={'headers': {'x-goog-api-key': API_KEY}}
)

# 3. SISTEMA DEFINITIVO: Dicionário de Normas (Intacto, sem cortar a PES no meio)
@st.cache_data
def carregar_sgi_em_dicionario():
    try:
        with open('SGI_Completo.txt', 'r', encoding='utf-8') as f:
            texto = f.read()
        
        partes = texto.split("[ARQUIVO:")
        dicionario_normas = {}
        
        for parte in partes:
            if len(parte.strip()) < 10: continue
            linhas = parte.split("\n", 1)
            nome_arq = linhas[0].replace("]", "").strip()
            conteudo = linhas[1] if len(linhas) > 1 else ""
            # Guarda a PES inteira atrelada ao nome dela
            dicionario_normas[nome_arq] = conteudo
            
        return dicionario_normas
    except Exception as e:
        return {}

normas_dit = carregar_sgi_em_dicionario()

# 4. BUSCA HÍBRIDA (Nome do arquivo + Conteúdo)
def buscar_pes_exata(pergunta, dicionario):
    if not dicionario: return "Base de dados vazia."
    
    pergunta_limpa = pergunta.lower()
    textos_selecionados = []
    
    # REGRA 1: Busca implacável pelo número da PES (Ex: PES 28, PES-28)
    # Extrai só o número que você digitou
    match_pes = re.search(r'pes\s*[-_]?\s*(\d+)', pergunta_limpa)
    if match_pes:
        numero = match_pes.group(1)
        for nome, texto in dicionario.items():
            nome_lower = nome.lower()
            # Puxa a norma pelo nome do arquivo!
            if f"pes {numero}" in nome_lower or f"pes_{numero}" in nome_lower or f"pes{numero}" in nome_lower:
                textos_selecionados.append(f"[ARQUIVO: {nome}]\n{texto}")
                
    # Se achou a PES pelo número, manda a norma inteira para a IA e já resolve aqui!
    if textos_selecionados:
        return "\n\n".join(textos_selecionados)[:60000]
        
    # REGRA 2: Busca por Assunto (Ex: ramal de esgoto)
    palavras_inuteis = ['qual', 'fala', 'sobre', 'de', 'o', 'a', 'e', 'que', 'do', 'da', 'no', 'na', 'como']
    palavras_chave = [p for p in re.findall(r'\b\w+\b', pergunta_limpa) if p not in palavras_inuteis and len(p) > 2]
    
    pontuacoes = []
    for nome, texto in dicionario.items():
        pontuacao = 0
        texto_lower = texto.lower()
        nome_lower = nome.lower()
        
        for palavra in palavras_chave:
            pontuacao += texto_lower.count(palavra)
        
        # Bônus gigante se o assunto estiver no NOME do arquivo
        for palavra in palavras_chave:
            if palavra in nome_lower:
                pontuacao += 100
                
        if pontuacao > 0:
            pontuacoes.append((pontuacao, nome, texto))
            
    pontuacoes.sort(key=lambda x: x[0], reverse=True)
    
    # Pega as 2 normas mais prováveis e envia inteiras
    for p, nome, texto in pontuacoes[:2]:
        textos_selecionados.append(f"[ARQUIVO: {nome}]\n{texto}")
        
    if not textos_selecionados:
        return "Nenhuma PES encontrada com esses termos. Tente ser mais específico."
        
    return "\n\n".join(textos_selecionados)[:60000]

# 5. Interface e Chat
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

for msg in st.session_state.mensagens:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if pergunta := st.chat_input("Ex: Qual PES fala sobre ramal de esgoto? ou PES 28"):
    
    with st.chat_message("user"):
        st.markdown(pergunta)
    st.session_state.mensagens.append({"role": "user", "content": pergunta})

    historico_formatado = ""
    for m in st.session_state.mensagens[-2:]: 
        quem = "Usuário" if m["role"] == "user" else "Assistente"
        historico_formatado += f"\n{quem}: {m['content']}\n"

    with st.chat_message("assistant"):
        resposta_ui = st.empty()
        resposta_ui.markdown("🔎 *Localizando a PES correta no fichário...*")
        
        # Pesca a PES correta ANTES de chamar a IA
        base_filtrada = buscar_pes_exata(pergunta, normas_dit)
        
        prompt = f"""
        Você é Engenheiro de Produção e consultor técnico do SGI.
        Sua missão é responder à dúvida do usuário com base EXCLUSIVAMENTE nas PES fornecidas abaixo.
        Seja direto. SEMPRE inicie a resposta citando o nome do arquivo da PES utilizada.
        
        NORMAS SELECIONADAS:
        {base_filtrada}
        
        HISTÓRICO RECENTE:
        {historico_formatado}
        
        PERGUNTA: {pergunta}
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
                    time.sleep(3)
                    continue
                resposta_final = f"⚠️ Erro de comunicação com o Google. Detalhe: {erro_str}"
                break
        
        resposta_ui.markdown(resposta_final)
        
    st.session_state.mensagens.append({"role": "assistant", "content": resposta_final})
