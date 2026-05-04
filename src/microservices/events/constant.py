from enum import StrEnum, auto


class TopicName(StrEnum):
    MOVIES = "movie-events"
    USERS = "user-events"
    PAYMENTS = "payment-events"