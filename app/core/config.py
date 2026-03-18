import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://erp:erp@127.0.0.1:5433/erpdb",
)

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-use-openssl-rand-hex-32")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))