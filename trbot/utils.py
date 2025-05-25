from datetime import datetime


## ========== UTILITY FUNCTIONS ========== ##
def timestamp_to_datetime(timestamp: int) -> str:
    dt = datetime.fromtimestamp(timestamp/1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def datetime_to_timestamp(dt_str: str) -> int:
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    return int(dt.timestamp() * 1000)
