from sqlalchemy import (
    Column, Integer, BigInteger, String, DateTime, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.base import Base

class Poll(Base):
    __tablename__ = 'polls'
    # Уникальный идентификатор опроса (PK)
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Идентификатор чата, где создан опрос
    chat_id = Column(String(255), nullable=False)
    # Текст вопроса
    question = Column(Text, nullable=False)
    # Дата создания опроса
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связь с ответами на опрос
    answers = relationship('PollAnswer', back_populates='poll', cascade="all, delete-orphan")

class PollAnswer(Base):
    __tablename__ = 'poll_answers'
    # Уникальный идентификатор ответа (PK)
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Внешний ключ на опрос
    poll_id = Column(Integer, ForeignKey('polls.id', ondelete='CASCADE'), nullable=False)
    # Внешний ключ на пользователя
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    # Вариант ответа пользователя
    option = Column(Text, nullable=False)
    # Дата ответа
    answered_at = Column(DateTime(timezone=True), server_default=func.now())

    poll = relationship('Poll', back_populates='answers')
    __table_args__ = (
        UniqueConstraint('poll_id', 'user_id', name='uq_poll_user'),
    ) 