from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.base import Base

class AdminSetting(Base):
    __tablename__ = 'admin_settings'
    # Уникальный идентификатор настройки (PK)
    id = Column(String(50), primary_key=True)
    # Показывать ли полные профили пользователям
    show_full_profiles = Column(Boolean, default=True)
    # Разрешить ли контакт между пользователями
    allow_contact = Column(Boolean, default=False)
    # Дата последнего изменения
    last_modified = Column(DateTime(timezone=True), server_default=func.now())
    # Кто последний изменил настройку (user_id)
    modified_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))

    # Связь с видимыми полями
    visible_fields = relationship('AdminVisibleField', back_populates='setting', cascade="all, delete-orphan")

class AdminVisibleField(Base):
    __tablename__ = 'admin_visible_fields'
    # Уникальный идентификатор (PK)
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Внешний ключ на настройку
    setting_id = Column(String(50), ForeignKey('admin_settings.id', ondelete='CASCADE'), nullable=False)
    # Имя поля, которое видно пользователям
    field_name = Column(String(50), nullable=False)

    setting = relationship('AdminSetting', back_populates='visible_fields')
    __table_args__ = (
        UniqueConstraint('setting_id', 'field_name', name='uq_setting_field'),
    ) 