from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from core.llm_provider import get_llm
from core.vector_store import build_vector_store, get_retriever


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


class RAGChainWrapper:
    def __init__(self, retriever, chain):
        self.retriever = retriever
        self.chain = chain

    def invoke(self, question: str) -> str:
        return self.chain.invoke(question)


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

    llm = get_llm(temperature=0.3)
    rag_chain = (
        {
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return RAGChainWrapper(retriever, chain=rag_chain)


def ask_question(rag_chain, question: str) -> str:
    print(f"Question : {question}")
    answer = rag_chain.invoke(question)
    print(f"answer :{answer}")
    return answer
