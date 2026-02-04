
import os
import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///generated_content.db")

engine = create_engine(DATABASE_URL)
metadata = MetaData()

generated_content = Table(
    "generated_content",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("theme", String),
    Column("prompt", String),
    Column("image_url", String),
    Column("video_url", String),
    Column("caption", String),
    Column("created_at", DateTime, default=datetime.datetime.utcnow),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    metadata.create_all(engine)

def save_generated_content(theme: str, prompt: str, image_url: str, video_url: str, caption: str):
    with SessionLocal() as db:
        db.execute(
            generated_content.insert().values(
                theme=theme,
                prompt=prompt,
                image_url=image_url,
                video_url=video_url,
                caption=caption,
            )
        )
        db.commit()
