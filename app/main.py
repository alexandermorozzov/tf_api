from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from typing import Union
from loguru import logger
import sys

from app.api.routers import router_get_metric
from app.api.routers import router_interpretation_criteria

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:MM-DD HH:mm}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
    colorize=True
)

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_get_metric.router, prefix="/api_v1")
app.include_router(router_interpretation_criteria.router, prefix="/api_v1")
