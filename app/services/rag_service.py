"""
RAG Service — Core pipeline (FAISS version):
  PDF → chunks → HuggingFace embeddings → FAISS index
  Question → retrieve top-K chunks → LLM → answer
"""
import os
import logging
import pickle
from pathlib import Path

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.core.config import settings

logger = logging.getLogger(__name__)

FAISS_INDEX_PATH = os.path.join(settings.CHROMA_PERSIST_DIR, "faiss_index")

RAG_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are an Enterprise AI Knowledge Assistant. Answer employee questions
using ONLY the information in the company documents below.

Rules:
- Answer clearly and concisely based on the context provided.
- If the answer is not in the documents, say: "I couldn't find this in the available documents."
- Do NOT make up information.
- Mention the source document name when possible.

Context from company documents:
---------------------------------
{context}
---------------------------------

Employee Question: {question}

Answer:"""
)


class RAGService:
    _instance = None

    def __init__(self):
        self._embeddings = None
        self._vectorstore = None
        self._llm = None
        self._doc_chunk_map: dict = {}

    @classmethod
    def get_instance(cls) -> "RAGService":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        logger.info("Initializing RAG service (FAISS)...")
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

        self._embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        if os.path.exists(FAISS_INDEX_PATH):
            try:
                self._vectorstore = FAISS.load_local(
                    FAISS_INDEX_PATH,
                    self._embeddings,
                    allow_dangerous_deserialization=True,
                )
                self._load_chunk_map()
                logger.info("Loaded existing FAISS index")
            except Exception as e:
                logger.warning(f"Could not load existing index: {e}. Starting fresh.")
                self._vectorstore = None

        self._llm = self._load_llm()
        logger.info("RAG service ready")

    def _load_llm(self):
        if settings.LLM_PROVIDER == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.1,
            )
        elif settings.LLM_PROVIDER == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=settings.GROQ_MODEL,
                groq_api_key=settings.GROQ_API_KEY,
                temperature=0.1,
            )
        else:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.OPENAI_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.1,
            )

    def _save_chunk_map(self):
        map_path = os.path.join(settings.CHROMA_PERSIST_DIR, "chunk_map.pkl")
        with open(map_path, "wb") as f:
            pickle.dump(self._doc_chunk_map, f)

    def _load_chunk_map(self):
        map_path = os.path.join(settings.CHROMA_PERSIST_DIR, "chunk_map.pkl")
        if os.path.exists(map_path):
            with open(map_path, "rb") as f:
                self._doc_chunk_map = pickle.load(f)

    async def ingest_pdf(self, file_path: str, doc_id: int) -> int:
        logger.info(f"Ingesting PDF: {file_path}")

        loader = PyMuPDFLoader(file_path)
        pages = loader.load()

        if not pages:
            raise ValueError("PDF appears to be empty or unreadable")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(pages)

        filename = Path(file_path).name
        for chunk in chunks:
            chunk.metadata["doc_id"] = str(doc_id)
            chunk.metadata["source"] = filename

        if self._vectorstore is None:
            self._vectorstore = FAISS.from_documents(chunks, self._embeddings)
        else:
            self._vectorstore.add_documents(chunks)

        self._vectorstore.save_local(FAISS_INDEX_PATH)
        self._doc_chunk_map[str(doc_id)] = len(chunks)
        self._save_chunk_map()

        logger.info(f"Stored {len(chunks)} chunks for doc_id={doc_id}")
        return len(chunks)

    async def ask(self, question: str) -> dict:
        if self._vectorstore is None:
            return {
                "answer": "No documents uploaded yet. Please upload PDF documents first.",
                "sources": [],
            }

        retriever = self._vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": settings.TOP_K_RESULTS},
        )

        # Modern LCEL chain — no RetrievalQA needed
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | RAG_PROMPT
            | self._llm
            | StrOutputParser()
        )

        # Get source documents separately
        source_docs = retriever.invoke(question)
        answer = await chain.ainvoke(question)

        sources = list({
            doc.metadata.get("source", "Unknown")
            for doc in source_docs
        })

        return {"answer": answer, "sources": sources}

    async def delete_document(self, doc_id: int):
        if self._vectorstore is None:
            return

        all_docs = []
        docstore = self._vectorstore.docstore._dict
        index_to_id = self._vectorstore.index_to_docstore_id

        for idx, doc_id_key in index_to_id.items():
            doc = docstore.get(doc_id_key)
            if doc and doc.metadata.get("doc_id") != str(doc_id):
                all_docs.append(doc)

        if all_docs:
            self._vectorstore = FAISS.from_documents(all_docs, self._embeddings)
            self._vectorstore.save_local(FAISS_INDEX_PATH)
        else:
            self._vectorstore = None
            if os.path.exists(FAISS_INDEX_PATH):
                import shutil
                shutil.rmtree(FAISS_INDEX_PATH)

        self._doc_chunk_map.pop(str(doc_id), None)
        self._save_chunk_map()

    def get_stats(self) -> dict:
        if self._vectorstore is None:
            return {"total_chunks_in_vectorstore": 0}
        return {"total_chunks_in_vectorstore": self._vectorstore.index.ntotal}


def get_rag_service() -> RAGService:
    return RAGService.get_instance()
