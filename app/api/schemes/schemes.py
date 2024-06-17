from app.api.schemes.enums import AvailableRegions
from pydantic import BaseModel, Field
from typing import Optional

class Region(BaseModel):
    """Base class for provision schema."""
    
    region: AvailableRegions