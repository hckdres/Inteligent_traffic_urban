from __future__ import annotations

from datetime import timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def zona_horaria(nombre: str, offset_horas: int):
    try:
        return ZoneInfo(nombre)
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=offset_horas), nombre)


COLOMBIA_TZ = zona_horaria("America/Bogota", -5)
UTC_TZ = timezone.utc
