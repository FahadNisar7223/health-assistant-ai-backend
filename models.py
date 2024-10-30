
from fastapi import UploadFile
from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    pdf_file: Optional[UploadFile] | None = None  
    query: Optional[str] | None = None

class DoctorRecommendationResponse(BaseModel):
    doctors: str 
