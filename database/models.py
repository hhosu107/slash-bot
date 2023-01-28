from sqlalchemy import ForeignKey
from sqlalchemy import Column, String, Integer, ARRAY, JSON
from sqlalchemy.orm import relationship

from database.database import Base

class GuildTable(Base):
    __tablename__ = "guild_table"
    guild_id = Column(String, primary_key=True, index=True)
    guild_name = Column(String, default="")

    guilds = relationship("RollStat", back_populates="guild")

class UserTable(Base):
    __tablename__ = "user_table"
    user_id = Column(String, primary_key=True, index=True)
    user_name = Column(String, default="")

    users = relationship("RollStat", back_populates="user")

class RollStat(Base):
    __tablename__ = "roll_stat"
    guid = Column(Integer, primary_key=True, index=True)
    guild_id = Column(String, ForeignKey("guild_table.guild_id"), index=True)
    user_id = Column(String, ForeignKey("user_table.user_id"), index=True)
    count_successful_rolls = Column(Integer)
    sum_successful_rolls = Column(Integer)

    guild = relationship("GuildTable", back_populates="guilds")
    user = relationship("UserTable", back_populates="users")

    guids = relationship("RollLog", back_populates="guid")

class RollLog(Base):
    __tablename__ = "roll_log"
    roll_id = Column(Integer, primary_key=True)
    guild_id = Column(Integer, ForeignKey("roll_stat.guid"))
    roll_string = Column(String)
    roll_result = Column(ARRAY(JSON))  # Each json has three attributes: dice, list of roll results, sum
    roll_modifier = Column(Integer)
    roll_sum = Column(Integer)

    guid = relationship("RollStat", back_populates="guids")
