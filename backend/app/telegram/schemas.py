from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    id: int
    is_bot: bool = False
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class TelegramChat(BaseModel):
    id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class TelegramMessage(BaseModel):
    message_id: int
    from_user: Optional[TelegramUser] = Field(None, alias="from")
    chat: TelegramChat
    date: int
    text: Optional[str] = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class TelegramCallbackQuery(BaseModel):
    id: str
    from_user: TelegramUser = Field(..., alias="from")
    message: Optional[TelegramMessage] = None
    data: Optional[str] = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage] = None
    callback_query: Optional[TelegramCallbackQuery] = None

    model_config = ConfigDict(extra="ignore")


# ─── Keyboards ─────────────────────────────────────────────────────────────

class InlineKeyboardButton(BaseModel):
    text: str
    callback_data: Optional[str] = None
    url: Optional[str] = None


class InlineKeyboardMarkup(BaseModel):
    inline_keyboard: List[List[InlineKeyboardButton]]


class ReplyKeyboardMarkup(BaseModel):
    keyboard: List[List[str]]
    resize_keyboard: bool = True
    one_time_keyboard: bool = True


class ReplyKeyboardRemove(BaseModel):
    remove_keyboard: bool = True


# ─── Auth Linking Schemas ──────────────────────────────────────────────────

class TelegramLinkTokenResponse(BaseModel):
    link_token: str
    expires_in_seconds: int
    bot_username: str
