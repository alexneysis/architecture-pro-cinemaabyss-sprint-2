import datetime
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from faststream.kafka import KafkaBroker
from starlette import status

from constant import TopicName
from schema import MovieEvent, UserEvent, PaymentEvent, EventResponse, Event

KAFKA_BROKERS = os.getenv("KAFKA_BROKERS")
assert KAFKA_BROKERS

broker = KafkaBroker(KAFKA_BROKERS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.start()
    try:
        yield
    finally:
        await broker.stop()


app = FastAPI(
    title="Events API",
    version="1.0.0",
    description="API to create and process kafka events",
    lifespan=lifespan
)


@app.get("/api/events/health")
async def healthcheck() -> dict[str, bool]:
    return {"status": True}


@app.post("/api/events/movie", status_code=status.HTTP_201_CREATED)
async def create_movie_event(movie_event: MovieEvent) -> EventResponse:
    result = await broker.publish(message=movie_event.model_dump(), topic=TopicName.MOVIES)
    return EventResponse(
        status="success",
        partition=result.partition,
        offset=result.offset,
        event=Event(
            id=str(uuid.uuid4()),
            type=TopicName.MOVIES,
            timestamp=datetime.datetime.now(tz=datetime.UTC).isoformat(),
            payload=movie_event.model_dump()
        )
    )


@app.post("/api/events/user", status_code=status.HTTP_201_CREATED)
async def create_user_event(user_event: UserEvent) -> EventResponse:
    result = await broker.publish(message=user_event.model_dump(), topic=TopicName.USERS)
    return EventResponse(
        status="success",
        partition=result.partition,
        offset=result.offset,
        event=Event(
            id=str(uuid.uuid4()),
            type=TopicName.USERS,
            timestamp=datetime.datetime.now(tz=datetime.UTC).isoformat(),
            payload=user_event.model_dump()
        )
    )


@app.post("/api/events/payment", status_code=status.HTTP_201_CREATED)
async def create_payment_event(payment_event: PaymentEvent) -> EventResponse:
    result = await broker.publish(message=payment_event.model_dump(), topic=TopicName.PAYMENTS)
    return EventResponse(
        status="success",
        partition=result.partition,
        offset=result.offset,
        event=Event(
            id=str(uuid.uuid4()),
            type=TopicName.PAYMENTS,
            timestamp=datetime.datetime.now(tz=datetime.UTC).isoformat(),
            payload=payment_event.model_dump()
        )
    )


# Worker
@broker.subscriber(TopicName.MOVIES)
async def process_movie(body: MovieEvent) -> None:
    print(f"Process message: {body=}")


@broker.subscriber(TopicName.USERS)
async def process_user(body: UserEvent) -> None:
    print(f"Process message: {body=}")


@broker.subscriber(TopicName.PAYMENTS)
async def process_payment(body: PaymentEvent) -> None:
    print(f"Process message: {body=}")
