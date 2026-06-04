from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional
from config.db import get_db
from core.auth_handler import get_password_hash, verify_password, create_access_token, decode_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

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

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    db_conn = get_db()
    user = db_conn.users.find_one({"email": email})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    user_data = {k: v for k, v in current_user.items() if k != "password" and k != "_id"}
    return user_data

@router.post("/register")
def register(user: User):
    db_conn = get_db()
    email_lower = user.email.strip().lower()
    if db_conn.users.find_one({"email": email_lower}):
        return {"status": "error", "message": "El usuario ya existe"}
    new_user = {
        "email": email_lower,
        "password": get_password_hash(user.password),
        "name": user.name or ""
    }
    db_conn.users.insert_one(new_user)
    return {"status": "success", "message": "Usuario registrado exitosamente"}

@router.post("/login")
def login(user: User):
    db_conn = get_db()
    email_lower = user.email.strip().lower()
    existing_user = db_conn.users.find_one({"email": email_lower})
    if not existing_user:
        return {"status": "error", "message": "Credenciales inválidas"}
    if verify_password(user.password, existing_user["password"]):
        access_token = create_access_token(data={"sub": email_lower})
        return {
            "status": "success", 
            "message": "Login exitoso", 
            "access_token": access_token,
            "token_type": "bearer",
            "email": email_lower,
            "name": existing_user.get("name", "")
        }
    return {"status": "error", "message": "Credenciales inválidas"}

@router.put("/user/update")
def update_user(user_update: UserUpdate, current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    update_data = {}
    if user_update.name is not None:
        update_data["name"] = user_update.name
    if not update_data:
        return {"status": "info", "message": "No hay datos para actualizar"}
    db_conn.users.update_one({"email": current_user["email"]}, {"$set": update_data})
    return {"status": "success", "message": "Perfil actualizado correctamente"}

@router.post("/user/change_password")
def change_password(req: PasswordChange, current_user: dict = Depends(get_current_user)):
    db_conn = get_db()
    if not verify_password(req.old_password, current_user["password"]):
        return {"status": "error", "message": "La contraseña actual es incorrecta"}
    db_conn.users.update_one(
        {"email": current_user["email"]},
        {"$set": {"password": get_password_hash(req.new_password)}}
    )
    return {"status": "success", "message": "Contraseña actualizada exitosamente"}

@router.get("/user/{email}")
def get_user(email: str):
    db_conn = get_db()
    email_lower = email.strip().lower()
    user = db_conn.users.find_one({"email": email_lower})
    if user:
        return {"status": "success", "user": user}
    else:
        return {"status": "error", "message": "Usuario no encontrado"}
