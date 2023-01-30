import uuid
import bcrypt
import logging
from datetime import date

from sqlalchemy import Table, Column, ForeignKey, Integer, VARCHAR
from sqlalchemy import inspect, create_engine, URL
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import declarative_base, mapped_column, Session

logging.basicConfig(level=logging.DEBUG)

class ValidationError(Exception):
    pass
    
class DuplicateError(Exception):
    pass

class LogSec:

    def __init__(self, username, password, host, port, database):
        logging.debug("__init__ start.")
        url_object = URL.create(
            "mysql",
            username=username,
            password=password,
            host=host,
            port=port,
            database=database 
        )
        logging.debug("Creating engine...")
        self.engine = create_engine(url_object)
        self.Base = declarative_base()
        logging.debug("Reflecting tables...")
        self.Base.metadata.reflect(self.engine,)

        inspect_object = inspect(self.engine)
        if not inspect_object.has_table("lgds_registration"):
            logging.debug("lgds_registration table does not exist, creating...")
            class Registration(self.Base):
                __tablename__ = "lgds_registration"
                # __table__ = Table("lgds_registration", self.Base.metadata, autoload_with=self.engine)
                
                discord_id = mapped_column(
                    VARCHAR(32), primary_key=True)
                unique_user_id = mapped_column(
                    VARCHAR(128), ForeignKey("ls_players.unique_user_id", ondelete="CASCADE"), 
                    unique=True, nullable=False)
                
                def __repr__(self):
                    return f"Registration(id={self.discord_id!r}, unique_user_id={self.unique_user_id!r})"
            Registration.__table__.create(self.engine)

        self.Registration = self.Base.metadata.tables['lgds_registration']
        self.LogSecPlayers = self.Base.metadata.tables['ls_players']
        logging.debug("__init__ done.")

    def register(self, discord_id, mc_username, password):
        """Registers Minecraft username bound to Discord user id.
        
        Raises ValidationError if either Minecraft username or password don't meet criteria.
        Raises DuplicateError if either Discord ID or Minecraft username exist in database.
        """
        
        logging.debug(f"(register) discord id, mc_username, and password: {discord_id} {mc_username} {password}")
        
        # Validate Minecraft username and password.
        if not (3 <= len(mc_username) <= 16) and ' ' not in mc_username:
            raise ValidationError("Minecraft username must be 3 to 16 characters long and without spaces.")
        if not (6 <= len(password) <= 32) and ' ' not in password:
            raise ValidationError("Password must be 6 to 32 characters long and without spaces.")
        
        # Generate UUID3 from lowercase name without stuffing.
        class NULL_NAMESPACE: bytes = b''
        mc_username_uuid = uuid.uuid3(NULL_NAMESPACE, 'OfflinePlayer:' + mc_username.lower())
        
        # Bcrypt 10 rounds variant 2a, which is what LoginSecurity uses.
        salt = bcrypt.gensalt(10, b'2a')
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        logging.debug(f"Generated uuid and password hash: {mc_username_uuid} {password_hash}")
            
        with Session(self.engine) as session:
            # Returns cursor, which apparently can only be iterated once, from then it is exhausted.
            # So assign all values to variable to use it multiple times.
            # .mappings().all() returns a list of dict, where key is the column name.
            # Allow only one discord id and minecraft uuid (lowercase username) in database.
            
            # Check if Minecraft username exist in LoginSecurity player table.
            existing_uuid = session.execute(
                select(self.LogSecPlayers.c.unique_user_id, self.LogSecPlayers.c.last_name)
                .where(self.LogSecPlayers.c.unique_user_id==str(mc_username_uuid))
            ).mappings().all()
            
            logging.debug(f"Result of existing uuid query: {existing_uuid}")
            
            # Check if Discord ID exist in database.
            existing_discord_id = session.execute(
                select(self.Registration.c.discord_id, self.Registration.c.unique_user_id)
                .where(self.Registration.c.discord_id==discord_id)
            ).mappings().all()
            
            logging.debug(f"Result of existing discord id query: {existing_discord_id}")
            
            # Make sure neither Discord ID nor Minecraft username exist in database.
            if existing_uuid:
                raise DuplicateError(
                    "Minecraft UUID already exist in database. "
                    f"UUID={existing_uuid[0]['unique_user_id']}, username={existing_uuid[0]['last_name']}")
            elif existing_discord_id:
                raise DuplicateError(
                    "Discord ID already exist in database. "
                    f"UUID={existing_discord_id[0]['discord_id']}, username={existing_discord_id[0]['unique_user_id']}")

            # Create a LoginSecurity username entry.
            session.execute(
                insert(self.LogSecPlayers),
                [{
                    "unique_user_id": str(mc_username_uuid), 
                    "last_name": mc_username, 
                    "password": password_hash, 
                    "hashing_algorithm": 7, 
                    "registration_date": date.today(), 
                    "optlock": 1, 
                    "uuid_mode": "O"
                }]
            )
            
            # Create a mapping between Discord ID and Minecraft username.
            session.execute(
                insert(self.Registration),
                [{
                    "discord_id": discord_id,
                    "unique_user_id": mc_username_uuid
                }]
            )
            
            # Commit rows to database.
            session.commit()
            
    def unregister(self, discord_id):
        """Removes registered Minecraft account bound to Discord user ID.
        """
        
        logging.debug(f"(unregister) discord id: {discord_id}")
        
        with Session(self.engine) as session:
            # Check if Discord ID exist in database.
            existing_discord_id = session.execute(
                select(self.Registration.c.discord_id, self.Registration.c.unique_user_id)
                .where(self.Registration.c.discord_id==discord_id)
            ).mappings().all()
            
            # The user did not register a username.
            if not existing_discord_id:
                raise KeyError(f"Discord ID not found in database. discord_id={discord_id}")
                
            mc_username_uuid = existing_discord_id[0]['unique_user_id']
            
            # Check if Minecraft username bound to Discord ID exist in database.
            existing_uuid = session.execute(
                select(self.LogSecPlayers.c.unique_user_id)
                .where(self.LogSecPlayers.c.unique_user_id==str(mc_username_uuid))
            ).mappings().all()
            
            
            if not existing_uuid:
                # Somehow, the bound username does not exist. Delete strange entry in lgds_registration table.
                session.execute(
                    delete(self.Registration)
                    .where(self.Registration.c.unique_user_id == mc_username_uuid)
                )
            else:
                # Entry in lgds_registration will be deleted as ForeignKey unique_user_id's deletion is cascaded.
                session.execute(
                    delete(self.LogSecPlayers)
                    .where(self.LogSecPlayers.c.unique_user_id == mc_username_uuid)
                )
                
            session.commit()
            
    @property
    def registered(self):
        """Returns players registered through this module, excluding pre-existing players in LoginSecurity.
        """
        with Session(self.engine) as session:
            registrations = session.execute(
                select(
                    self.Registration.c.discord_id, 
                    self.LogSecPlayers.c.last_name, 
                    self.LogSecPlayers.c.registration_date
                )
                .join_from(self.Registration, self.LogSecPlayers)
            ).mappings().all()
            return registrations
            
    @property
    def usernames(self):
        """Returns all usernames including pre-existing players in LoginSecurity.
        """
        with Session(self.engine) as session:
            registrations = session.execute(
                select(self.LogSecPlayers.c.last_name, self.LogSecPlayers.c.registration_date)
            ).mappings().all()
            return registrations
        
    def lookup_discord(self, discord_id):
        """Returns registration of Discord user.
        """
        with Session(self.engine) as session:
            registrations = session.execute(
                select(
                    self.Registration.c.discord_id, 
                    self.LogSecPlayers.c.last_name, 
                    self.LogSecPlayers.c.registration_date
                )
                .join_from(self.Registration, self.LogSecPlayers)
                .where(self.Registration.c.discord_id==discord_id)
            ).mappings().all()
            return registrations
            
    def lookup_username(self, mc_username):
        """Returns row where UUID of username matches.
        """
        # Generate UUID3 from lowercase name without stuffing.
        class NULL_NAMESPACE: bytes = b''
        mc_username_uuid = str(uuid.uuid3(NULL_NAMESPACE, 'OfflinePlayer:' + mc_username.lower()))
        
        with Session(self.engine) as session:
            registrations = session.execute(
                select(self.LogSecPlayers.c.last_name, self.LogSecPlayers.c.registration_date)
                .where(self.LogSecPlayers.c.unique_user_id==mc_username_uuid)
            ).mappings().all()
            return registrations