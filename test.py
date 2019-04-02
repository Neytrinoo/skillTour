from datetime import datetime, timedelta, timezone

now_date = datetime.now(timezone.utc).astimezone()
print(now_date < datetime.now(timezone.utc).astimezone())
print((now_date - datetime.now(timezone.utc).astimezone()).days)
print(now_date.strftime('%d.%m.%Y, %H:%M'))
