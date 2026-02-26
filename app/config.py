from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_hostname: str
    database_port: int
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    # Email settings (can be accessed as email_host, email_user, etc.)
    email_host: str
    email_port: int
    email_user: str
    email_pass: str

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()