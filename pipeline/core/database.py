from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime

# Database setup
# Using SQLite for simplicity as no other DB was specified.
DB_URL = "sqlite:///./pipeline_data/log_analyzer.db"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class FileMaster(Base):
    __tablename__ = "file_master"

    id = Column(Integer, primary_key=True, index=True)
    File_ID = Column(String, index=True) # This acts as Batch ID from legacy CSV
    Original_Filename = Column(String)
    Stored_Filename = Column(String)
    Source_Type = Column(String)
    Raw_Storage_Path = Column(String)
    Final_Path = Column(String)
    Category = Column(String)
    Cluster_ID = Column(String)
    Summary = Column(Text)
    File_Size_KB = Column(Float)
    Row_Count = Column(Integer)
    Status = Column(String)
    Created_On = Column(DateTime, default=datetime.utcnow)
    Created_By = Column(String)

class LogExtraction(Base):
    __tablename__ = "log_extraction"

    id = Column(Integer, primary_key=True, index=True)
    FileID = Column(Integer, ForeignKey("file_master.id")) # References unique DB ID
    LogEntryType = Column(String) # Error, Vulnerability, Warning, Info
    LogMessage = Column(Text)
    Resolution = Column(Text)
    ReferenceURL = Column(String)
    LoggedOn = Column(DateTime)
    Priority = Column(String)
    CreatedBy = Column(String)
    CreatedOn = Column(DateTime, default=datetime.utcnow)
    UpdatedBy = Column(String)
    UpdatedOn = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
