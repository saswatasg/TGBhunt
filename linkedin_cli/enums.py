from enum import Enum


class ProfileState(str, Enum):
    QUALIFIED = "Qualified"
    READY_TO_CONNECT = "Ready to Connect"
    PENDING = "Pending"
    CONNECTED = "Connected"
    COMPLETED = "Completed"
    FAILED = "Failed"

