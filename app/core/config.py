import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://erp:erp@127.0.0.1:5433/erpdb")