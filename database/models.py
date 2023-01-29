from sqlalchemy import ForeignKey
from sqlalchemy import Column, String, Integer, ARRAY, JSON, BigInteger
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

    users = relationship("RollStat", back_populates="user")

class RollStat(Base):
    __tablename__ = "roll_stat"
    guid = Column(Integer, primary_key=True, index=True)
    guild_id = Column(ForeignKey("guild_table.guild_id"), index=True)
    user_id = Column(ForeignKey("user_table.user_id"), index=True)
    count_successful_rolls = Column(BigInteger, default=0)
    sum_successful_rolls = Column(BigInteger, default=0)

    guild = relationship("GuildTable", back_populates="guilds")
    user = relationship("UserTable", back_populates="users")

    roll_logs = relationship("RollLog", back_populates="guid_obj")

class RollLog(Base):
    __tablename__ = "roll_log"
    roll_id = Column(Integer, primary_key=True, index=True)
    guid = Column(Integer, ForeignKey("roll_stat.guid"))
    roll_string = Column(String, default="")
    roll_result = Column(ARRAY(JSON), default=[])  # Each json has three attributes: dice, list of roll results, sum
    roll_modifier = Column(Integer, default=0)
    roll_sum = Column(Integer, default=0)

    guid_obj = relationship("RollStat", back_populates="roll_logs")
