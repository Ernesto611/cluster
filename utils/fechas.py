from datetime import datetime
from zoneinfo import ZoneInfo

def ahora_mx():
    return datetime.now(ZoneInfo("America/Mexico_City"))
