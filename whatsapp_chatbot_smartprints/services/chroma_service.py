import os
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings.ollama import OllamaEmbeddings
from langchain_core.documents import Document

from whatsapp_chatbot_smartprints.utility import normalize_distance_reversed


class ChromaService:
    def __init__(self, collection_name, persist_directory, embedding_model_name):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embed_model = OllamaEmbeddings(model=embedding_model_name)
        self.chroma = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embed_model,
            persist_directory=self.persist_directory,
            relevance_score_fn=normalize_distance_reversed
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n"], 
            chunk_size=1000, 
            chunk_overlap=200
        )

    def index_files(self, summarizer):
        print('Indexing files into the database ...')
        documents: List[Document] = []
        for file in os.listdir("./docs/"):
            filepath = os.path.join("./docs/", file)
            document_loader = TextLoader(filepath, encoding='utf-8')
            docs = document_loader.load()
            documents.extend(docs)
        
        texts = []
        for doc in documents:
            texts.extend(doc.page_content.split('$$$$$$$$$$$$$$$$'))

        texts = [text for text in texts if text]
        # extracted_topics = [summarizer.invoke(text)[0] for text in texts]

        try:
            self.chroma.add_texts(
                ids=[f'{idx}' for idx in range(len(texts))],
                texts= texts,
                embeddings= self.embed_model.embed_documents(texts)
                )
        except Exception as e:
            print(f"Error indexing files: {e}")
        print('Indexing files into the database: 🟩 Finished')

    def retrieve(self, query: str, score_threshold=.8, k=5) -> List[Document]:
        return self.chroma.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": score_threshold, "k": k}
            ).invoke(query)