# -*- coding: utf-8 -*-
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")

    # Database: prefer DATABASE_URL (Render Postgres). Fall back to SQLite for local dev.
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        # Render may provide postgres://; SQLAlchemy needs postgresql+psycopg2://
        SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://")
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///concorrencia.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
