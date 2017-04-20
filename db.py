# pylint: disable=C0103
import os
import sqlalchemy.ext.declarative
from sqlalchemy import Column, Integer, String, ForeignKey

def create_session(path, **connect_args):
    url = 'sqlite+pysqlite:///' + path
    engine = sqlalchemy.create_engine(url, connect_args=connect_args)
    if not os.path.isfile(path):
        Base.metadata.create_all(bind=engine)
    Session = sqlalchemy.orm.sessionmaker(bind=engine)
    return Session()

Base = sqlalchemy.ext.declarative.declarative_base()
class Information(Base):
    __tablename__ = 'information'
    id = Column(Integer, primary_key=True)
    lcid = Column(String)
    name = Column(String)

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String)

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    categoryID = Column(Integer, ForeignKey('categories.id'))
    name = Column(String)

    category = sqlalchemy.orm.relationship(
        'Category',
        backref=sqlalchemy.orm.backref('groups', order_by=id)
    )

class Type(Base):
    __tablename__ = 'types'
    id = Column(Integer, primary_key=True)
    groupID = Column(Integer, ForeignKey('groups.id'))
    name = Column(String, index=True)
    description = Column(String)

    group = sqlalchemy.orm.relationship(
        'Group',
        backref=sqlalchemy.orm.backref('types', order_by=id)
    )
