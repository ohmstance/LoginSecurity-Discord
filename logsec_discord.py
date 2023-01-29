import uuid
import bcrypt
import logging

from sqlalchemy import Table, Column, ForeignKey, Integer, VARCHAR
from sqlalchemy import inspect, create_engine, URL
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import mapped_column, Session

logging.basicConfig(level=logging.DEBUG)

class LogSec:

    def __init__(self, username, password, host, port, database):
        url_object = URL.create(
            "mysql",
            username=username,
            password=password,
            host=host,
            port=port,
            database=database 
        )
        self.Base = automap_base()
        
        class Registration(self.Base):
            logging.debug("__init__ start.")
            __tablename__ = "lgds_registration"
            
            discord_id = mapped_column(
                VARCHAR(32), 
                primary_key=True
            )
            unique_user_id = mapped_column(
                VARCHAR(128), 
                ForeignKey("ls_players.unique_user_id", ondelete="CASCADE"), 
                unique=True,
                nullable=False
            )
            
            def __repr__(self):
                return (
                    "Registration("
                        f"id={self.discord_id!r}, "
                        f"unique_user_id={self.unique_user_id!r}"
                    ")"
                )
        
        logging.debug("Creating engine...")
        self.engine = create_engine(url_object)
        logging.debug("Base prepare with autoload...")
        
        self.Base.prepare(autoload_with=self.engine)
        
        inspect_object = inspect(self.engine)
        if not inspect_object.has_table("lgds_registration"):
            logging.debug("Creating lgds_registration table...")
            Registration.__table__.create(self.engine)
        
        logging.debug("Creating declarative mapping of tables...")
        self.Registration = Registration
        self.LogSecPlayers = self.Base.classes.ls_players
        logging.debug("__init__ done.")
        
    def init_table(self):
        inspect_object = inspect(self.engine)
        if not inspect_object.has_table("lgds_registration"):
            class Registration(Base):
                __tablename__ = "lgds_registration"
                
                discord_id = mapped_column(
                    VARCHAR(32), 
                    primary_key=True
                )
                unique_user_id = mapped_column(
                    VARCHAR(128), 
                    ForeignKey("ls_players.unique_user_id", ondelete="CASCADE"), 
                    unique=True,
                    nullable=False
                )
                
                def __repr__(self):
                    return (
                        "Registration("
                            f"id={self.discord_id!r}, "
                            f"unique_user_id={self.unique_user_id!r}"
                        ")"
                    )
                    
            Registration.__table__.create(self.engine)
        
        