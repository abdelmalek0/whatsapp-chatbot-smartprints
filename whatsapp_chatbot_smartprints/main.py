import os
import json
from flask import Flask, request, jsonify
import httpx
from dotenv import load_dotenv
from flask_cors import CORS
import time
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from threading import Thread
import bs4
from langchain import hub
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_community.embeddings.ollama import OllamaEmbeddings
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader, SitemapLoader, TextLoader
import asyncio
from langchain_core.documents import Document
from typing import List

app = Flask(__name__)
CORS(app)
load_dotenv()

WEBHOOK_VERIFY_TOKEN = os.environ.get('WEBHOOK_VERIFY_TOKEN')
GRAPH_API_TOKEN = os.environ.get('GRAPH_API_TOKEN')
PORT = int(os.environ.get('PORT', 5000))

DEFAULT_MSSG = []
with open('agent.txt', 'r') as file:
    content = file.read()
    DEFAULT_MSSG.append(SystemMessage(
        content=content
    ))
messages = {}

def indexing(chroma_db: Chroma):
    print('Indexing files into the database ...')
    documents: List[Document] = []
    for index, file in enumerate(os.listdir("./docs/")):
        filpath = os.path.join("./docs/", file)
        document_loader = TextLoader(filpath, encoding='utf-8')
        docs = document_loader.load()
        documents.extend(docs)
    
    texts = []
    for doc in documents:
        texts.extend(doc.page_content.split('$$$$$$$$$$$$$$$$'))

    try:
        chroma_db.add_texts(texts, ids=[f'{idx}' for idx in range(len(texts))]);
    except Exception as e:
        print(e)
    print('Indexing files into the database: 🟩 Finished')


MODEL_NAME = 'llama3.1' #'llama3.1' #'gemma2:latest'
EMBED_MODEL_NAME = 'mxbai-embed-large:latest'
CHROMA_DB = './chromadb/'
COLLECTION_NAME = 'smartprints'
# RAG prompt
human_message_template = '''Answer the question based only on the following context:
{context}

Question: {question}
'''

llm = ChatOllama(model=MODEL_NAME, temperature=0.0)
embed_model = OllamaEmbeddings(model=EMBED_MODEL_NAME)
text_splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n"], 
    chunk_size=1000, 
    chunk_overlap=200
)

chroma = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embed_model,
    persist_directory=CHROMA_DB
)
    
# retriever = chroma.as_retriever()

# prompt = ChatPromptTemplate(messages=[])

# def update_chat_history(prompt):
#     chat_history[-1] = prompt.messages[-1]
#     return prompt

rag_chain = (
    llm
    | StrOutputParser()
)

def send_message(business_phone_number_id: str, to: str, body: str, replied_to = None):
    url: str = f"https://graph.facebook.com/v20.0/{business_phone_number_id}/messages"
    headers: dict = {
        "Authorization": f"Bearer {GRAPH_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data: dict = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    print(data)
    if replied_to:
        data['context'] = {"message_id": replied_to}
    
    return httpx.post(
            url,
            headers=headers,
            json=data
        )

@app.route('/webhook', methods=['POST'])
def webhook():
    message = request.json.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('messages', [{}])[0]
    
    if message.get('type') == 'text':
        # extract the business number to send the reply from it
        business_phone_number_id = request.json.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}).get('metadata', {}).get('phone_number_id')
           
        
        
        # mark incoming message as read
        httpx.post(
            f"https://graph.facebook.com/v20.0/{business_phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {GRAPH_API_TOKEN}",
            },
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message['id'],
            }
        )
        
        print(f'You received a message from {message['from']} saying:\n{message['text']['body']}')
        
        llm_thread = Thread(target=reply_using_llm, 
                            args=[business_phone_number_id, 
                                  message['from'], 
                                  message['text']['body'], 
                                  message['id']]
                        )
        llm_thread.start()
    
    return '', 200

def reply_using_llm(business_phone_number_id: str, to: str, body: list, replied_to = None):
    chat_history  = messages.get(to, DEFAULT_MSSG).copy()
    new_message = HumanMessagePromptTemplate.from_template(human_message_template)
    new_message_formatted = new_message.format(context=chroma.as_retriever(search_kwargs={'k': 7}).invoke(body),
                                       question=body)
    chat_history.append(new_message_formatted)
    
    llm_response = rag_chain.invoke(chat_history)
    
    chat_history.append(AIMessage(content=llm_response))
    messages[to] = chat_history.copy()
    print(llm_response)
    
    send_message(business_phone_number_id, to, 
                llm_response, replied_to)

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == WEBHOOK_VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge, 200
    else:
        return '', 403

@app.route('/')
def home():
    return "<pre>Nothing to see here.\nCheckout README.md to start.</pre>"

if __name__ == '__main__':
    # Thread(target=indexing, args=[chroma,]).start()
    if not os.path.exists(CHROMA_DB) and COLLECTION_NAME not in [collection.name for collection in chroma._client.list_collections()]:
        Thread(target=indexing, args=[chroma,]).start()
    else:
        print('Database is already set up!')
    
    app.run(port=PORT, debug=True)