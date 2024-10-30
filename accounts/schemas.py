from pydantic import BaseModel, EmailStr
from typing import Union

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        orm_mode = True
        
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Union[str, None]

class UserForgot(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

class Message(BaseModel):
    message: str
