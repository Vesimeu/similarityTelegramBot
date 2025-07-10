from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from sqlalchemy.types import UserDefinedType
from models.base import Base

# Для поля POINT (PostGIS)
class Point(UserDefinedType):
    def get_col_spec(self):
        return "POINT"

class User(Base):
    __tablename__ = 'users'
    # Уникальный идентификатор пользователя (PK)
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Telegram user_id (уникальный идентификатор Telegram)
    tg_user_id = Column(BigInteger, unique=True, index=True)
    # Имя пользователя
    name = Column(String(255), nullable=False)
    # Username в Telegram
    username = Column(String(255))
    # Возраст пользователя
    age = Column(Integer)
    # Пол пользователя ('Мужской', 'Женский', 'Любой')
    gender = Column(String(50))
    # Город пользователя
    city = Column(String(255))
    # URL аватарки/фото
    photo_url = Column(Text)
    # Телефон пользователя
    phone = Column(String(20))
    # Email пользователя
    email = Column(String(255))
    # Дата создания профиля
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Дата последней активности
    last_activity = Column(DateTime(timezone=True))
    # Дата последнего изменения профиля
    last_modified = Column(DateTime(timezone=True))
    # Был ли показан welcome scroll
    seen_welcome_scroll = Column(Boolean, default=False)
    # Заполнен ли профиль полностью
    is_completed = Column(Boolean, default=False)
    # Количество совпадений (матчей)
    matches = Column(Integer, default=0)
    # Геолокация пользователя (PostGIS POINT)
    location = Column(Point)
    # Радиус поиска пары (км)
    search_radius_km = Column(Numeric(10, 2))

    # Связи с другими таблицами
    preferences = relationship('UserPreference', uselist=False, back_populates='user', cascade="all, delete-orphan")
    visibility = relationship('UserVisibility', uselist=False, back_populates='user', cascade="all, delete-orphan")
    social_links = relationship('UserSocialLink', back_populates='user', cascade="all, delete-orphan")
    interests = relationship('UserInterest', back_populates='user', cascade="all, delete-orphan")
    photos = relationship('Photo', back_populates='user', cascade="all, delete-orphan")

class UserPreference(Base):
    __tablename__ = 'user_preferences'
    # Уникальный идентификатор (PK)
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Внешний ключ на пользователя
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    # Предпочитаемый пол для поиска
    preferred_gender = Column(String(50))
    # Предпочитаемый город для поиска
    preferred_city = Column(String(255))
    # Ключевое слово для поиска
    preferred_keyword = Column(String(3))
    # Минимальный возраст для поиска
    preferred_age_min = Column(Integer)
    # Максимальный возраст для поиска
    preferred_age_max = Column(Integer)

    user = relationship('User', back_populates='preferences')

class UserVisibility(Base):
    __tablename__ = 'user_visibility'
    # Уникальный идентификатор (PK)
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Внешний ключ на пользователя
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    # Видимость имени
    name_visible = Column(Boolean, default=True)
    # Видимость возраста
    age_visible = Column(Boolean, default=True)
    # Видимость пола
    gender_visible = Column(Boolean, default=True)
    # Видимость города
    city_visible = Column(Boolean, default=True)
    # Видимость email
    email_visible = Column(Boolean, default=False)
    # Видимость фото
    photo_url_visible = Column(Boolean, default=False)
    # Видимость соцсетей
    social_links_visible = Column(Boolean, default=False)
    # Видимость интересов
    interests_visible = Column(Boolean, default=False)
    # Видимость телефона
    phone_visible = Column(Boolean, default=False)

    user = relationship('User', back_populates='visibility')

class UserSocialLink(Base):
    __tablename__ = 'user_social_links'
    # Уникальный идентификатор (PK)
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Внешний ключ на пользователя
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    # Название платформы (VK, Telegram, Instagram и т.д.)
    platform = Column(String(50), nullable=False)
    # URL профиля
    url = Column(Text, nullable=False)

    user = relationship('User', back_populates='social_links')
    __table_args__ = (UniqueConstraint('user_id', 'platform', name='uq_user_platform'),)

class UserInterest(Base):
    __tablename__ = 'user_interests'
    # Уникальный идентификатор (PK)
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Внешний ключ на пользователя
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    # Интерес пользователя (строка)
    interest = Column(String(255), nullable=False)

    user = relationship('User', back_populates='interests')
    __table_args__ = (UniqueConstraint('user_id', 'interest', name='uq_user_interest'),)

class Photo(Base):
    __tablename__ = 'photos'
    # Уникальный идентификатор (PK)
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Внешний ключ на пользователя
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    # URL фото
    photo_url = Column(Text, nullable=False)
    # Дата загрузки фото
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship('User', back_populates='photos') 