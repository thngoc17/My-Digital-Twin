from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from llama_cpp import Llama
import time
import os
from source.schemas import ChatRequest, ChatResponse

# Global registry for ML models
ml_models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Resolve Vector DB path
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'my_data', 'knowledge_db'))

    try:
        ml_models["embedding"] = HuggingFaceEmbeddings(
            model_name="bkai-foundation-models/vietnamese-bi-encoder"
        )
        ml_models["vector_db"] = Chroma(
            persist_directory=db_path,
            embedding_function=ml_models["embedding"]
        )
    except Exception as e:
        raise RuntimeError(f"Vector DB initialization failed: {e}")

    # Resolve LLM directory via Azure ML environment variables
    model_dir = os.getenv("AZUREML_MODEL_DIR")
    if not model_dir:
        raise RuntimeError("CRITICAL: AZUREML_MODEL_DIR environment variable missing.")

    # Dynamic traversal to locate the GGUF model file across nested directories
    target_filename = "qwen3-4b-instruct-2507.Q4_K_M.gguf"
    model_path = None

    for root, dirs, files in os.walk(model_dir):
        if target_filename in files:
            model_path = os.path.join(root, target_filename)
            break

    if not model_path:
        raise FileNotFoundError(f"CRITICAL: Target model {target_filename} not found in {model_dir}")

    print(f"INFO: LLM resolved at absolute path: {model_path}")

    try:
        # Initialize Llama.cpp model
        ml_models["llm"] = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_gpu_layers=0
        )
    except Exception as e:
        raise RuntimeError(f"Llama.cpp model initialization failed: {e}")

    yield
    ml_models.clear()


app = FastAPI(lifespan=lifespan)


# Synchronous definition forces FastAPI to execute this CPU-bound task in a threadpool
@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    start_time = time.time()

    try:
        # 1. Extract user query
        user_query = request.messages[-1].content

        # 2. RAG contextual retrieval (CPU-bound)
        vector_db = ml_models["vector_db"]
        results = vector_db.similarity_search(user_query, k=2)
        context_str = "\n".join([f"- {doc.page_content}" for doc in results]) if results else ""

        # 3. Prompt augmentation via in-context learning
        if context_str:
            augmented_prompt = f"[THÔNG TIN NỀN VỀ BẠN]:\n{context_str}\n\n[CÂU HỎI]:\n{user_query}"
            request.messages[-1].content = augmented_prompt

        # 4. Format message history
        formatted_messages = [{"role": m.role, "content": m.content} for m in request.messages]

        # 5. LLM inference execution (Heavy CPU-bound)
        llm = ml_models["llm"]
        response = llm.create_chat_completion(
            messages=formatted_messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop=["<|im_end|>", "<|endoftext|>"]
        )
        ai_reply = response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        # Global exception handler to maintain worker stability
        raise HTTPException(status_code=500, detail=str(e))

    process_time = time.time() - start_time

    return ChatResponse(
        reply=ai_reply,
        retrieved_context=context_str,
        processing_time=process_time
    )