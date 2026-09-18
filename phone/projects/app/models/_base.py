# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/models/_base.py
from pydantic import BaseModel, EmailStr, model_validator, Field
from typing import Optional, Union, List, Tuple, Annotated, Any, Dict, Callable
from typing_extensions import Self
from datetime import datetime, timedelta


class ORMBaseModel(BaseModel):
    model_config = {"from_attributes": True}
