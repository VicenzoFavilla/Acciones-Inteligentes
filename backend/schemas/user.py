from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None

class PasswordChange(BaseModel):
    email: str
    old_password: str
    new_password: str
