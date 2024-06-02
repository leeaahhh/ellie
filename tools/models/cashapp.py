from pydantic import BaseModel


class CashAppAvatar(BaseModel):
    image_url: str | None = None
    accent_color: str | None = None


class CashApp(BaseModel):
    url: str
    cashtag: str
    display_name: str
    country_code: str
    avatar_url: CashAppAvatar
    qr: str
