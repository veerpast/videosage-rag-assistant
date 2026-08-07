import os
import shutil
import subprocess
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from core.vector_store import build_vector_store, load_vector_store, get_retriever


def get_mistral_api_key() -> str:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError(
            "MISTRAL_API_KEY is not set. Please add it to your .env file or export it in your shell."
        )
    return api_key.strip()


def get_llm():
    return ChatMistralAI(
        model="mistral-small-latest",
        mistral_api_key=get_mistral_api_key(),
        temperature=0.3,
    )

def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])

RAG_PROMPT_TEMPLATE = """You are an expert meeting assistant. Answer the user's question based ONLY on the meeting transcript context provided below.

If the answer is not found in the context, say:
"I could not find this information in the meeting transcript."

Always be concise and precise. If quoting someone, mention it clearly.

Context from meeting transcript:
{context}

Question: {question}
Answer:"""


def has_ollama() -> bool:
    return shutil.which("ollama") is not None


def get_ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")


def run_ollama(prompt_text: str, model: str | None = None) -> str:
    if not has_ollama():
        raise RuntimeError("Ollama CLI is not available on PATH for local fallback.")

    model_name = model or get_ollama_model()
    cmd = ["ollama", "run", model_name, prompt_text]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Ollama fallback failed (return code {result.returncode}): {result.stderr.strip()}"
        )

    output = result.stdout.strip()
    return output


class RAGChainWrapper:
    def __init__(self, retriever, chain=None, model: str | None = None):
        self.retriever = retriever
        self.chain = chain
        self.model = model or get_ollama_model()

    def invoke(self, question: str) -> str:
        if self.chain is not None:
            try:
                return self.chain.invoke(question)
            except Exception as exc:
                print(f"⚠️ Mistral failed during answer generation: {exc}")
                if has_ollama():
                    print(f"🔁 Falling back to local Ollama model {self.model}.")
                    return self.invoke_ollama(question)
                raise

        return self.invoke_ollama(question)

    def invoke_ollama(self, question: str) -> str:
        if hasattr(self.retriever, "get_relevant_documents"):
            docs = self.retriever.get_relevant_documents(question)
        elif hasattr(self.retriever, "_get_relevant_documents"):
            docs = self.retriever._get_relevant_documents(question, run_manager=None)
        else:
            raise RuntimeError("Retriever does not support relevant document lookup.")

        context = format_docs(docs)
        prompt_text = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
        return run_ollama(prompt_text, self.model)


def build_rag_chain(transcript: str):
    vector_store = build_vector_store(transcript)
    retriever = get_retriever(vector_store, k=4)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an expert meeting assistant. Answer the user's question 
based ONLY on the meeting transcript context provided below.

If the answer is not found in the context, say: 
"I could not find this information in the meeting transcript."

Always be concise and precise. If quoting someone, mention it clearly.

Context from meeting transcript:
{context}""",
            ),
            ("human", "{question}"),
        ]
    )

    try:
        llm = get_llm()
        rag_chain = (
            {"context": retriever | RunnableLambda(format_docs),
             "question": RunnablePassthrough()
             }
            | prompt | llm | StrOutputParser()
        )
        return RAGChainWrapper(retriever, chain=rag_chain)
    except Exception as exc:
        print(f"⚠️  Mistral unavailable: {exc}")
        if not has_ollama():
            raise
        print(f"🔁 Falling back to local Ollama model {get_ollama_model()}")
        return RAGChainWrapper(retriever, chain=None, model=get_ollama_model())

def ask_question(rag_chain, question:str) -> str:
    print(f"Question : {question}")
    answer = rag_chain.invoke(question)
    print(f"answer :{answer}")
    return answer