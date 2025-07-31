from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import json
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from . import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    questions = relationship("QuestionAnswer", back_populates="user", cascade="all, delete")

    score = relationship("UserScore", uselist=False, back_populates="user")

    def to_dict(self):
        return {"name": self.email}

class QuestionAnswer(Base):
    __tablename__ = 'question_answers'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="questions")


class Challenges(Base):
    __tablename__ = 'challenges'

    id = Column(Integer, primary_key=True, index=True)
    challenge_sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    challenge_receiver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    accepted_sender = Column(Boolean, default=True)
    accepted_receiver = Column(Boolean, default=False)
    quiz_json = Column(JSON)
    sender_answer_for_challenge = Column(String, default=None)
    receiver_answer_for_challenge = Column(String, default=None)


class UserScore(Base):
    __tablename__ = "user_scores"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    total_score = Column(Integer, default=0)

    user = relationship("User", back_populates="score")