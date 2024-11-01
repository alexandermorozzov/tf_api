from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from typing import Union
from loguru import logger
import os
import sys

from app.api.utils.constants import DATA_PATH
from app.api.utils import get_graphs
from app.api.utils import get_matrix
from app.api.routers import router_interpretation_criteria
from app.api.routers import router_get_matrix
from app.api.routers import router_recalculate_matrix
from app.api.routers import router_transport_indicator

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:MM-DD HH:mm}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
    colorize=True
)

app = FastAPI(
    title='Transport Frames API',
    description='API for Transport Frames service, building transport frames of regions, calculating transport indicators for regions and specified project areas.', 
    version='1.0.0',
    contact={
         'name': 'Alexander Morozov',
         'email': 'alexandermorozzov@gmail.com'
    }
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_interpretation_criteria.router)
app.include_router(router_get_matrix.router)
app.include_router(router_recalculate_matrix.router)
app.include_router(router_transport_indicator.router)

def create_required_directories():
        required_dirs = ['matrices', 'frames', 'graphs']
        for dir_name in required_dirs:
            dir_path = os.path.join(DATA_PATH, dir_name)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path) 
                logger.info(f"Folder created: {dir_path}")
            else:
                logger.info(f"Folder already exists: {dir_path}")


@app.on_event("startup")
async def startup_event():
    create_required_directories()
    get_graphs.process_graph()
    get_matrix.process_matrix()
    get_graphs.process_frames()