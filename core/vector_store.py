from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def build_vector_store(transcript: str) -> Chroma:
    print("Building in-memory vector store")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(transcript)

    docs = [
        Document(page_content=chunk, metadata={"chunk_index": i})
        for i, chunk in enumerate(chunks)
    ]

    # With no LangChain embedding wrapper, Chroma uses its bundled ONNX
    # all-MiniLM-L6-v2 model. This keeps semantic retrieval on CPU without
    # pulling PyTorch/CUDA packages into the free Streamlit deployment.
    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=None,
    )

    return vector_store


def get_retriever(vector_store: Chroma, k: int = 4):
    return vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})
