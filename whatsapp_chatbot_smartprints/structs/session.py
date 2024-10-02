from dataclasses import dataclass
from dataclasses import field

from utility import generate_short_id

@dataclass
class Session:
    id: str = field(init=False)
    messages: list
    alive: bool = True

    def __post_init__(self):
        self.id = generate_short_id()

    def update_messages(self, messages):
        self.messages = messages
