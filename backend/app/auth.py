import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_password(credentials: HTTPBasicCredentials) -> bool:
    password = os.getenv("LOGIN_PASSWORD", "admin123")
    return credentials.password == password

def get_current_user(credentials: HTTPBasicCredentials = Security(security)):
    if not verify_password(credentials):
        raise HTTPException(
            status_code=401,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username or "admin"