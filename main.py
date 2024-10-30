from fastapi import FastAPI, UploadFile, File, Form, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.document_loaders import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings  
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from sqlalchemy.orm import Session
from database import SessionLocal, engine
from accounts import models, schemas, auth
from accounts.models import User
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import timedelta

from sqlalchemy.exc import IntegrityError

from pydantic import BaseModel
from typing import Optional
from chatbot import conversation
from calculator import Calculate
import fitz  
import os
import tempfile
from groq import Groq
from contextlib import asynccontextmanager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


vectorstore = None
hf = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global vectorstore, hf

    csv_file = 'data/final_cleansed_data.csv'
    loader = CSVLoader(file_path=csv_file)
    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, length_function=len)
    docs = text_splitter.split_documents(documents)

    model_name = "paraphrase-MiniLM-L6-v2"
    model_kwargs = {'device': 'cpu'}
    hf = HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs)

    vectorstore = Chroma.from_documents(documents=docs, collection_name="rag-chroma", embedding=hf)

   

    yield
    
os.environ["GROQ_API_KEY"] = "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"

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


app = FastAPI(lifespan=lifespan)


@app.post("/recommendation")
async def ask_user(query: str = Form(...), pdf_file: UploadFile = File(None)):
    response = {}

    if pdf_file:
        try:
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(await pdf_file.read())
                pdf_path = temp_file.name
            
            health_report_text = extract_text_from_pdf(pdf_path)
            analysis_prompt = f"Analyze the following health report:\n\n{health_report_text}\n\nWhat health condition(s) are mentioned in the report?"

            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": analysis_prompt}],
                model="llama3-8b-8192",
            )
            detected_condition = chat_completion.choices[0].message.content.strip()
            response["detected_condition"] = detected_condition

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
        finally:
        
            if os.path.exists(pdf_path):
                os.remove(pdf_path)


    if query:
        try:
            retriever = vectorstore.as_retriever(k=4)
            retrieved_docs = retriever.invoke(query) 
            context = "\n\n".join([doc.page_content for doc in retrieved_docs]) 
            query_embedding = hf.embed_query(query)
            prompt = f"""Based on the information provided, suggest a doctor who would be suitable for addressing in following {context}
            The response should include:
            Answer the {query} in the following way.
            1. The doctor's name, specialization, and experience (including certifications, if applicable).
            2. Patient feedback statistics (satisfaction rate, number of reviews).
            3. Consultation fees and any other notable details such as location, wait time, etc.
            4. Recommendations for next steps, like checking profiles, patient reviews, or other factors the user should consider (such as location, wait time, specific skin condition).
            Format the response professionally, using headings, bullet points, and a conversational yet informative tone. Ensure that the suggestions are clear and actionable.
            """

    
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
            )
            ai_response = chat_completion.choices[0].message.content.strip()
            response["doctor_suggestion"] = ai_response

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

    return JSONResponse(content=response)


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    doc = fitz.open(pdf_path)
    extracted_text = ""
    for page in doc:
        extracted_text += page.get_text()
    doc.close()
    return extracted_text


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




class UserDetails(BaseModel):
    age: int
    gender: str
    height: float
    weight: float
    prompt: Optional[str] = ''

@app.post("/nutrition")
async def nutritionist(details: UserDetails):
    age = details.age
    gender = details.gender
    height = details.height
    weight = details.weight

    BMI_info = Calculate(age, gender, height, weight)
    BMI = BMI_info.get('BMI', '')
    weight_category = BMI_info.get('Remarks', '')
    weight_to_gain = BMI_info.get('Weight to Gain (kgs)', '')

    diet_plan_template = f"""
        You are a professional nutritionist tasked with creating a **hypothetical** six-month diet plan for educational purposes. 
        The plan does not have to be medically accurate, but should demonstrate a well-balanced approach to gaining weight based on the user's profile.

        Here is the user's information:
        - Age: {age}
        - Sex: {gender}
        - Height: {height} feet
        - Weight: {weight} kg
        - BMI: {BMI}
        - Current weight category: {weight_category}
        - Weight to gain: {weight_to_gain} kg

        Please generate a **hypothetical** detailed six-month diet plan, including breakfast, lunch, dinner, and snacks for each day.
    """

    if 'Weight to Gain (kgs)' in BMI_info:
        weight_to_gain = BMI_info.get('Weight to Gain (kgs)', '')

        if weight_to_gain > 0:
            diet_plan_template = f"""
                You are a professional nutritionist tasked with creating a **hypothetical** six-month diet plan for educational purposes. 
                The plan does not have to be medically accurate, but should demonstrate a well-balanced approach to gaining weight based on the user's profile.

                Here is the user's information:
                - Age: {age}
                - Sex: {gender}
                - Height: {height} feet
                - Weight: {weight} kg
                - BMI: {BMI}
                - Current weight category: {weight_category}
                - Weight to gain: {weight_to_gain} kg

                Based on this information, generate a hypothetical six-month meal plan for breakfast, lunch, dinner, and snacks each day.
                The plan should be structured as follows:
                - **Breakfast**: Include sources of protein, carbohydrates, and healthy fats.
                - **Lunch**: Should include a balance of lean protein, whole grains, and vegetables.
                - **Dinner**: Include a light but nutritious meal to promote weight gain.
                - **Snacks**: Suggest healthy snacks between meals to help meet caloric intake goals.

                Provide a detailed plan with specific foods for each meal.
                """
        else:
            diet_plan_template = f"""
                You are a professional nutritionist tasked with creating a **hypothetical** six-month diet plan for educational purposes. 
                The plan does not have to be medically accurate, but should demonstrate a well-balanced approach to lose weight based on the user's profile.

                Here is the user's information:
                - Age: {age}
                - Sex: {gender}
                - Height: {height} feet
                - Weight: {weight} kg
                - BMI: {BMI}
                - Current weight category: {weight_category}
                - Weight to lose: {weight_to_gain} kg

                Based on this information, generate a hypothetical six-month meal plan for breakfast, lunch, dinner, and snacks each day.
                The plan should be structured as follows:
                - **Breakfast**: Include sources of protein, carbohydrates, and healthy fats.
                - **Lunch**: Should include a balance of lean protein, whole grains, and vegetables.
                - **Dinner**: Include a light but nutritious meal to promote weight gain.
                - **Snacks**: Suggest healthy snacks between meals to help meet caloric intake goals.

                Provide a detailed plan with specific foods for each meal.
                """

    else:
        diet_plan_template = f"""
            You are a professional nutritionist tasked with creating diet plan for educational purposes. 
            The plan does not have to be medically accurate, but should demonstrate a well-balanced approach to maintain weight based on the user's profile.

            Here is the user's information:
            - Age: {age}
            - Sex: {gender}
            - Height: {height} feet
            - Weight: {weight} kg
            - BMI: {BMI}
            - Current weight category: {weight_category}

            This person has a Normal weight based on BMI calculations, just tell this person how he can main his current weight.
        """

    if details.prompt and not details.age and not details.weight and not details.gender and not details.height :     
        response = conversation(details.prompt)  
    else:
        response = conversation(diet_plan_template)

    return {"assistant": response}




app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/signup", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        hashed_password = auth.get_password_hash(user.password)
        db_user = User(username=user.username, email=user.email, password=hashed_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )


@app.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.email).first()
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/forgot", response_model=schemas.Message)
def forgot_password(form_data: schemas.UserForgot, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if form_data.new_password != form_data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    user.password = auth.get_password_hash(form_data.new_password)
    db.commit()

    return {"message": "Password updated successfully"}
