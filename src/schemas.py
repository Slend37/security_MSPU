from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr
import re
from typing_extensions import Self


class UserCreate(BaseModel):
    username: str = Field(..., min_length=4, max_length=20, pattern=r'^[a-zA-Z0-9]*$')
    email: EmailStr = Field(...)
    password: str = Field(...)
    confirm_password: str = Field(...)
    age: int = Field(..., ge=18, le=100)

    @field_validator('password')
    @classmethod
    def username_validator(cls, value):
        if not re.search(r'[A-Z]', value):
            raise ValueError("Password must contain at least 1 upcase letter.")
        if not re.search(r'[0-9]', value):
            raise ValueError("Password must contain at least 1 digital.")
        if not re.search(r'[^a-zA-Z0-9\s]', value):
            raise ValueError("Password must contain at least 1 special symbol.")


    @model_validator(mode='after')
    def check_passwords_match(self) -> Self:
        pw1 = self.password
        pw2 = self.confirm_password
        if pw1 is not None and pw2 is not None and pw1 != pw2:
            raise ValueError('passwords do not match')
        return self
