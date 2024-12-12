import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


load_dotenv()

SQLALCHEMY_DATABASE_URL = str(os.getenv("POSTGRES_URL", ""))

engine = create_engine(SQLALCHEMY_DATABASE_URL)

# CREATE THE METADATA OBJECT TO ACCESS THE TABLE
meta_data = MetaData()
meta_data.reflect(bind=engine)

# Generate the session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
