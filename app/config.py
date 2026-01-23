from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    # Database
    database_url: str
    
    
    # Auth/JWT
    token_time: int = 60
    jwt_algorthim: str = 'HS256'
    secret_key: str
    
    # Mail config
    smtp_server: str = ''
    smtp_port: str = ''
    smtp_user: str = ''
    smtp_password: str = ''

    # App
    app_name: str = 'TraumGmbH Bestellsystem'
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
       
    )

settings = Settings()