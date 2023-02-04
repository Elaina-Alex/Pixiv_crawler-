from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker

# 允许多线程
engine = create_engine('sqlite:///pixiv_image.db', connect_args={"check_same_thread": False})

Base = declarative_base()


class ImageDB(Base):
    __tablename__ = 'images'
    id = Column(Integer, primary_key=True)
    image_title = Column(String)
    image_description = Column(String)
    image_author = Column(String)
    image_author_id = Column(String)
    image_tags = Column(String)
    image_url = Column(String)
    image_page_count = Column(Integer)
    image_create_date = Column(String)
    cover = Column(String)


class UserDB(Base):
    __tablename__ = 'users_info'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    fullname = Column(String)
    password = Column(String)

    def __repr__(self):
        return "<User(name='%s', fullname='%s', password='%s')>" % (
            self.name, self.fullname, self.password)


Base.metadata.create_all(engine)

session = sessionmaker(bind=engine)()
