# from dongraphio import GraphType

# from pydantic import BaseModel, Field
# from typing import Optional

# class Metric(BaseModel):
#     """Base class for provision schema."""

#     city_name: str = Field(..., example="krasnodar", max_length=20, min_length=1)
#     graph_type: str = Field(..., example='public_transport')
#     x: float = Field(..., example=45.043423, ge=0.0, le=180.0)
#     y: float = Field(..., example=39.027212, ge=-90.0, le=90.0)
#     weight_value: int = Field(..., example=10, gt=0)
#     weight_type: str = Field(..., example='time_min')
#     routes: bool = Field(..., example=False)
#     # response_format: str = Field(..., example='html')