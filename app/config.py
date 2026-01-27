from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    # Database
    database_url: str
    
    
    # Auth/JWT
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    temp_token_expire_minutes: int = 3
    jwt_algorithm: str = 'HS256'
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

    #2FA
    two_factor_issuer: str


settings = Settings()