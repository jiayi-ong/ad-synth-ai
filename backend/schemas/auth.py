from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    password: str


class UserRead(BaseModel):
    id: str
    email: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
