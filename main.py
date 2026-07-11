from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo
from datetime import datetime
import swisseph as swe

app = FastAPI(title="AstroLivro Swiss API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

geolocator = Nominatim(user_agent="astrolivro-swiss-api")
tzfinder = TimezoneFinder()

PLANETS = {
    "Sol": swe.SUN,
    "Lua": swe.MOON,
    "Mercúrio": swe.MERCURY,
    "Vênus": swe.VENUS,
    "Marte": swe.MARS,
    "Júpiter": swe.JUPITER,
    "Saturno": swe.SATURN,
    "Urano": swe.URANUS,
    "Netuno": swe.NEPTUNE,
    "Plutão": swe.PLUTO,
    "Nodo Norte": swe.TRUE_NODE,
}

SIGNS = [
    "Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem",
    "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"
]

class NatalChartRequest(BaseModel):
    name: str = Field(min_length=1)
    date: str
    time: str
    city: str = Field(min_length=1)
    state: str = Field(min_length=1)
    country: str = Field(min_length=1)

class NatalChartCoordinatesRequest(BaseModel):
    name: str = Field(min_length=1)
    date: str
    time: str
    latitude: float
    longitude: float
    timezone: str

def sign_data(longitude: float) -> dict:
    lon = longitude % 360.0
    sign_index = int(lon // 30)
    degree_in_sign = lon % 30
    return {
        "sign": SIGNS[sign_index],
        "degree_in_sign": degree_in_sign,
    }

def parse_local_to_utc(date_str: str, time_str: str, timezone_name: str):
    try:
        local_dt = datetime.fromisoformat(f"{date_str}T{time_str}")
        local_dt = local_dt.replace(tzinfo=ZoneInfo(timezone_name))
        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
        return local_dt, utc_dt
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Data, horário ou fuso inválido: {exc}")

def find_house(longitude: float, cusps: list[float]) -> int:
    lon = longitude % 360.0
    for i in range(12):
        start = cusps[i] % 360.0
        end = cusps[(i + 1) % 12] % 360.0
        inside = start <= lon < end if start < end else lon >= start or lon < end
        if inside:
            return i + 1
    raise RuntimeError("Não foi possível determinar a casa planetária.")

def calculate_chart(
    name: str,
    date_str: str,
    time_str: str,
    latitude: float,
    longitude: float,
    timezone_name: str,
    location: Optional[dict] = None,
) -> dict:
    local_dt, utc_dt = parse_local_to_utc(date_str, time_str, timezone_name)

    utc_hour = (
        utc_dt.hour
        + utc_dt.minute / 60.0
        + utc_dt.second / 3600.0
    )

    jd_ut = swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_hour,
        swe.GREG_CAL,
    )

    cusps_raw, ascmc = swe.houses(jd_ut, latitude, longitude, b"P")
    cusps = [float(value) for value in cusps_raw]
    ascendant = float(ascmc[0])
    midheaven = float(ascmc[1])

    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    planets = []

    for planet_name, planet_id in PLANETS.items():
        values, return_flag = swe.calc_ut(jd_ut, planet_id, flags)
        planet_longitude = float(values[0]) % 360.0
        longitude_speed = float(values[3])

        planets.append({
            "name": planet_name,
            "longitude": planet_longitude,
            **sign_data(planet_longitude),
            "retrograde": longitude_speed < 0,
            "house": find_house(planet_longitude, cusps),
        })

    houses = [
        {
            "number": index + 1,
            "cusp": cusp % 360.0,
            **sign_data(cusp),
        }
        for index, cusp in enumerate(cusps)
    ]

    return {
        "name": name,
        "location": location or {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone_name,
        },
        "local_datetime": local_dt.isoformat(),
        "utc_datetime": utc_dt.isoformat(),
        "julian_day_ut": jd_ut,
        "ascendant": {
            "longitude": ascendant % 360.0,
            **sign_data(ascendant),
        },
        "midheaven": {
            "longitude": midheaven % 360.0,
            **sign_data(midheaven),
        },
        "houses": houses,
        "planets": planets,
        "engine": "Swiss Ephemeris via pyswisseph",
        "swiss_version": swe.version,
    }

@app.get("/")
def root():
    return {
        "service": "AstroLivro Swiss API",
        "status": "online",
        "docs": "/docs",
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "engine": "pyswisseph",
        "swiss_version": swe.version,
    }

@app.post("/natal-chart")
def natal_chart(payload: NatalChartRequest):
    query = f"{payload.city}, {payload.state}, {payload.country}"
    location = geolocator.geocode(query, exactly_one=True, timeout=15)

    if not location:
        raise HTTPException(
            status_code=404,
            detail="Local não encontrado. Confira cidade, estado e país.",
        )

    latitude = float(location.latitude)
    longitude = float(location.longitude)
    timezone_name = tzfinder.timezone_at(
        lat=latitude,
        lng=longitude,
    )

    if not timezone_name:
        raise HTTPException(
            status_code=422,
            detail="Não foi possível determinar o fuso horário do local.",
        )

    return calculate_chart(
        name=payload.name,
        date_str=payload.date,
        time_str=payload.time,
        latitude=latitude,
        longitude=longitude,
        timezone_name=timezone_name,
        location={
            "query": query,
            "display_name": location.address,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone_name,
        },
    )

@app.post("/natal-chart/coordinates")
def natal_chart_coordinates(payload: NatalChartCoordinatesRequest):
    return calculate_chart(
        name=payload.name,
        date_str=payload.date,
        time_str=payload.time,
        latitude=payload.latitude,
        longitude=payload.longitude,
        timezone_name=payload.timezone,
    )
