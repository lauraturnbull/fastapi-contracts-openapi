from pydantic import BaseModel
from src.contract_tests.src.contract_testing import is_consumer_of, HTTPMethod


@is_consumer_of("griddle-earth/v1/game/{game_id}/command", HTTPMethod.POST, 200)
class CommandResponse(BaseModel):
    thing_1: int
    thing_2: str