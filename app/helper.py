import datetime

def to_datetime(inp):
    if isinstance(inp, (int, float)):
        dt = datetime.datetime.fromtimestamp(inp, tz=datetime.timezone.utc)
    elif isinstance(inp, str):
        dt = datetime.datetime.fromisoformat(inp.replace("Z", "+00:00"))
    else:
        raise TypeError("Non supported type {}".format(type(inp)))
    return dt
