from pydantic import BaseModel


class MovieEvent(BaseModel):
    movie_id: int
    title: str
    action: str
    user_id: int | None = None
    rating: float | None = None
    genres: list[str] | None = None
    description: str | None = None

class UserEvent(BaseModel):
    user_id: int
    username: str | None = None
    email: str | None = None
    action: str
    timestamp: str

class PaymentEvent(BaseModel):
    payment_id: int
    user_id: int
    amount: float
    status: str
    timestamp: str
    method_type: str | None = None

class Event(BaseModel):
    id: str
    type: str
    timestamp: str
    payload: dict

class EventResponse(BaseModel):
    status: str
    partition: int
    offset: int
    event: Event