# type: ignore
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from database import engine, SessionLocal
from models import Base, Document, Query, User
from sqlalchemy import text
from pydantic import BaseModel
import os

# New HuggingFace and LangChain imports
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

app = FastAPI(title="AI Knowledge Retrieval API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
def on_startup():
    # Enable the vector extension first
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    
    # Then create the tables
    Base.metadata.create_all(bind=engine)

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

# Define the data structure we expect from the frontend
class QueryRequest(BaseModel):
    user_id: int
    question: str

class FeedbackRequest(BaseModel):
    query_id: int
    rating: int
    engineers_comment: str = ""

@app.post("/ask")
def ask_question(request: QueryRequest):
    db = SessionLocal()
    try:
        # Embed the user's question using the free local model
        embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        query_embedding = embeddings_model.embed_query(request.question)
        
        # Semantic Search: Find top 3 closest documents in PostgreSQL
        # pgvector's l2_distance operator mathematically finds the closest matches
        similar_docs = db.query(Document).order_by(
            Document.embedding.l2_distance(query_embedding)
        ).limit(3).all()
        
        # Combine the retrieved text chunks into one large string
        context = "\n\n".join([doc.content for doc in similar_docs])
        
        # Generate AI Response
        groq_key = os.getenv("GROQ_API_KEY")

        if not groq_key:
            return {"error": "GROQ_API_KEY is not set in the environment variables."}
        
        llm = ChatGroq(
            api_key=groq_key,
            model="llama-3.1-8b-instant",
            temperature=0.1
        )
        # Zephyr uses specific tags for system and users prompts
        prompt = PromptTemplate.from_template(
            "<|system|>\nYou are an expert IT support assistant. Use the following retrieved context to answer the user's question. If you cannot answer based on the context, say 'I don't have enough information to answer this.'\n\nContext:\n{context}</s>\n<|user|>\n{question}</s>\n<|assistant|>"
        )
        chain = prompt | llm
        ai_answer = chain.invoke({"context": context, "question": request.question})

        # Save the interaction to the database
        # For testing, we automatically create a dummy user if they don't exist yet
        user = db.query(User).filter(User.user_id == request.user_id).first()
        if not user:
            user = User(user_id=request.user_id, staff_name="Test Agent", role="Support", department="IT")
            db.add(user)
            db.commit()

        new_query = Query(
            user_id=request.user_id,
            user_prompt=request.question,
            ai_answer=ai_answer.content
        )
        db.add(new_query)
        db.commit()
        db.refresh(new_query)
        
        return {
            "query_id": new_query.query_id,
            "question": request.question,
            "answer": ai_answer.content,
            "sources_retrieved": len(similar_docs)
        }
        
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

@app.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    db = SessionLocal()
    try:
        from models import Feedback
        
        # Check if feedback already exists to allow users to change their mind
        existing_feedback = db.query(Feedback).filter(Feedback.query_id == request.query_id).first()
        if existing_feedback:
            existing_feedback.rating = request.rating
            existing_feedback.engineers_comment = request.engineers_comment
        else:
            new_feedback = Feedback(
                query_id=request.query_id,
                rating=request.rating,
                engineers_comment=request.engineers_comment
            )
            db.add(new_feedback)
            
        db.commit()
        return {"status": "Feedback recorded successfully."}
        
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()