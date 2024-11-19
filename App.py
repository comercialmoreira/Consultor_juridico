import tempfile
import streamlit as st
from langchain.memory import ConversationBufferMemory
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import base64  
from Loaders import *

openai = st.secrets["OPENAI_API_KEY"]
groq = st.secrets["GROQ_API_KEY"]


# Função para codificar a imagem em base64
def get_base64_image(image_path):
    with open(image_path, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def apply_custom_styles():
    image_path = './assets/images/logo.png'  # Caminho para o seu logo
    encoded_image = get_base64_image(image_path)
    st.markdown(f"""
    <style>
        /* Inserir a imagem no topo da sidebar */
        [data-testid="stSidebar"]::before {{
            content: "";
            display: block;
            height: 130px;  /* Ajuste a altura conforme necessário */
            background-image: url('data:image/png;base64,{encoded_image}');
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            margin-top:40px;
        }}
        /* Ajustar o padding para evitar sobreposição */
        [data-testid="stSidebar"] .block-container {{
            padding-top: 40px;  /* Deve ser maior que a altura da imagem */
        }}
        /* Estilização customizada da sidebar */
        [data-testid="stSidebar"] {{
            background-color: #1C1C1C;
            color: white;
            font-color: white;
        }}
        /* Estilização dos botões na sidebar */
        .stButton>button {{
            background-color: #587472;
            color: white;
            border-radius: 8px;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            margin-bottom: 10px;
        }}
        /* Estilização das abas */
        .stTabs [role=tab] {{
            background-color: #40444B;
            border: none;
            color: white;
            padding: 10px;
            font-size: 18px;
        }}
        /* Estilização da aba selecionada */
        .stTabs [role=tab][aria-selected="true"] {{
            background-color: #587472;
        }}
    </style>
    """, unsafe_allow_html=True)

apply_custom_styles()



TIPOS_ARQUIVOS_VALIDOS = [
    'Gerador de Contratos', 'Analisador de Contratos', 'Consultor juridico'
]

CONFIG_MODELOS = {'Groq': 
                        {'modelos': ['llama-3.1-70b-versatile', 'gemma2-9b-it', 'mixtral-8x7b-32768'],
                         'chat': ChatGroq,
                         'api_key': groq,
                         },
                    'Openai': 
                        {'modelos': ['gpt-4o-mini', 'gpt-4o'],
                         'chat': ChatOpenAI,
                         'api_key': openai}
}


MEMORIA = ConversationBufferMemory()


PROMPTS = {
    'Gerador de Contratos': '''
    Objetivo: Gerar um contrato robusto baseado nas informações fornecidas.
    Para começar, preciso de algumas informações básicas:
    - Quais são as partes envolvidas?
    - Qual é o objeto do contrato?
    - Qual será a duração e condições de rescisão?
    - Existem obrigações específicas?
    {input}
    ''',
    'Analisador de Contratos': '''
    Objetivo: Analisar o contrato fornecido e fornecer uma análise detalhada.
    Vou revisar cada cláusula e sugerir melhorias, caso necessário.
    {input}
    ''',
    'Consultor juridico': '''
    Objetivo: Fornecer consultoria jurídica com base nas informações fornecidas.
    Por favor, descreva a questão jurídica que deseja discutir.
    {input}
    '''
}

def carrega_arquivos(tipo_arquivo, arquivo):
    if tipo_arquivo == 'Gerador de Contratos':
        documento = carrega_site(arquivo)
    if tipo_arquivo == 'Analisador de Contratos':
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp:
            temp.write(arquivo.read())
            nome_temp = temp.name
        documento = carrega_pdf(nome_temp)
    if tipo_arquivo == 'Consultor juridico':
        documento = carrega_site(arquivo)
    return documento

def carrega_modelo(provedor, modelo, api_key, tipo_arquivo, arquivo):

    documento = carrega_arquivos(tipo_arquivo, arquivo)

    system_message = PROMPTS[tipo_arquivo].format(input=documento)

    template = ChatPromptTemplate.from_messages([
        ('system', system_message),
        ('placeholder', '{chat_history}'),
        ('user', '{input}')
    ])
    chat = CONFIG_MODELOS[provedor]['chat'](model=modelo, api_key=api_key)
    chain = template | chat

    st.session_state['chain'] = chain

def pagina_chat():
    st.header('Consultor :violet[Juridico]', divider='violet')

    chain = st.session_state.get('chain')
    if chain is None:
        st.error('Carregue o assistente na sidebar antes de usar o chat')
        st.stop()

    memoria = st.session_state.get('memoria', MEMORIA)

    # Carregar histórico de mensagens
    for mensagem in memoria.buffer_as_messages:
        chat = st.chat_message(mensagem.type)
        chat.markdown(mensagem.content)

    # Capturar a entrada do usuário
    input_usuario = st.chat_input('Digite para o seu assistente')
    if input_usuario:
        # Mostrar a entrada do usuário na interface
        chat = st.chat_message('human')
        chat.markdown(input_usuario)

        # Configurar a resposta da IA
        chat = st.chat_message('ai')

        # Ajustar o histórico de chat para uma lista de mensagens base, ao invés de uma string
        chat_history = [{'type': msg.type, 'content': msg.content} for msg in memoria.buffer_as_messages]

        # Obter a resposta da IA
        resposta_stream = chain.stream({
            'input': input_usuario,
            'chat_history': chat_history  # Agora passado como uma lista de mensagens base
        })

        resposta = ""
        for chunk in resposta_stream:
            resposta += chunk
            chat.markdown(resposta)

        # Atualizar memória de conversação
        memoria.chat_memory.add_user_message(input_usuario)
        memoria.chat_memory.add_ai_message(resposta)
        st.session_state['memoria'] = memoria

def sidebar():
    tabs = st.tabs(['Upload de Arquivos', 'Seleção de Modelos'])
    with tabs[0]:
        tipo_arquivo = st.selectbox('Selecione o tipo de assistente', TIPOS_ARQUIVOS_VALIDOS)
        if tipo_arquivo == 'Analisador de Contratos':
            arquivo = st.file_uploader('Faça o upload do arquivo pdf', type=['.pdf'])
        if tipo_arquivo == 'Gerador de Contratos':
            arquivo = "https://wolfadvocacia.com.br"
        if tipo_arquivo == 'Consultor juridico':
            arquivo = "https://wolfadvocacia.com.br"
       

    with tabs[1]:
        provedor = st.selectbox('Selecione o provedor dos modelo', CONFIG_MODELOS.keys())
        modelo = st.selectbox('Selecione o modelo', CONFIG_MODELOS[provedor]['modelos'])
        api_key = CONFIG_MODELOS[provedor]['api_key']
        
    if st.button('Inicializar Assistente', use_container_width=True):
            carrega_modelo(provedor, modelo, api_key, tipo_arquivo, arquivo)
    if st.button('Apagar Histórico de Conversa', use_container_width=True):
            st.session_state['memoria'] = MEMORIA

def main():
    with st.sidebar:
        sidebar()
    pagina_chat()


if __name__ == '__main__':
    main()
