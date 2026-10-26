"""Opaque-session wire bodies; no token decoding, renewal or authentication here."""

from typing import Literal

from pydantic import Field

from app.schemas.common import Body, Email, UtcInstant


class AdminCredentials(Body):
    email: Email = Field(repr=False)
    password: str = Field(repr=False)


class AdminToken(Body):
    access_token: str = Field(alias="accessToken", repr=False)
    token_type: Literal["bearer"] = Field(alias="tokenType")
    expires_at: UtcInstant = Field(alias="expiresAt")
