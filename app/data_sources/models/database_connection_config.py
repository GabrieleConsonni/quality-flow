from pydantic import BaseModel


class DatabaseConnectionConfig(BaseModel):
    database_type: str
    host: str
    port: int
    database: str
    db_schema:str
    user: str
    password: str