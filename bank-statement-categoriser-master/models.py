from sqlalchemy import create_engine, ForeignKey
from sqlalchemy import Column, Date, Integer, String
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///data/app.db')
Base = declarative_base()


class Training(Base):
    __tablename__ = 'TrainingData'

    id = Column(Integer, primary_key=True)
    description = Column(String)
    category = Column(String)


Base.metadata.create_all(engine)
