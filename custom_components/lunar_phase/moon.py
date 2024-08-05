"""MoonCalc instance."""

import datetime
import logging

from astral import LocationInfo
import ephem

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from .const import (
    EXTRA_ATTR_ALTITUDE,
    EXTRA_ATTR_AZIMUTH,
    EXTRA_ATTR_PARALLACTIC_ANGLE,
    STATE_ATTR_AGE,
    STATE_ATTR_ALTITUDE,
    STATE_ATTR_AZIMUTH,
    STATE_ATTR_DISTANCE_KM,
    STATE_ATTR_ILLUMINATION_FRACTION,
    STATE_ATTR_NEXT_FIRST,
    STATE_ATTR_NEXT_FULL,
    STATE_ATTR_NEXT_HIGH,
    STATE_ATTR_NEXT_NEW,
    STATE_ATTR_NEXT_RISE,
    STATE_ATTR_NEXT_SET,
    STATE_ATTR_NEXT_THIRD,
    STATE_ATTR_PARALLACTIC_ANGLE,
)
from .moon_script import MoonScript

_LOGGER = logging.getLogger(__name__)


class MoonCalc:
    """Class to calculate the Moon phase."""

    def __init__(
        self,
        hass: HomeAssistant,
        city: str,
        region: str,
        latitude: float,
        longitude: float,
        timezone: str,
    ) -> None:
        """Initialize the MoonCalc object."""

        _LOGGER.debug("Initializing MoonCalc object")
        self.hass = hass
        self._city = city
        self._region = region
        self._latitude = latitude
        self._longitude = longitude
        self._timezone = timezone
        self.today = dt_util.now().date()
        self.date = datetime.datetime.now()
        self.moon_ephem = ephem.Moon()
        self.observer = ephem.Observer()
        self.location = None
        self.observer.date = self.date
        self._phase_name = None
        self._moon_attributes = {}
        self._moon_position = {}
        self._moon_illumination = {}
        self._moon_times = {}
        self._extra_attributes = {}

    def set_location(self) -> LocationInfo:
        """Set the location."""
        self.location = LocationInfo(
            self._city, self._region, self._timezone, self._latitude, self._longitude
        )
        self.observer.lat = str(self.location.latitude)
        self.observer.lon = str(self.location.longitude)
        return self.location

    def get_moon_position(self):
        """Return the moon position."""
        lat = self.location.latitude
        lon = self.location.longitude
        now = dt_util.now()
        self._moon_position = MoonScript.get_moon_position(now, lat, lon)
        return self._moon_position

    def get_moon_illumination(self):
        """Return the moon illumination."""
        self._moon_illumination = MoonScript.get_moon_illumination(self.date)
        return self._moon_illumination

    def get_moon_times(self):
        """Return the moon times."""
        now = datetime.datetime.now()

        self._moon_times = MoonScript.get_moon_times(
            now, self.location.latitude, self.location.longitude, False
        )
        _LOGGER.debug("Moon times: %s", self._moon_times)
        return self._moon_times

    def get_current_position(self, position):
        """Return the moon position attribute."""

        return self._moon_position.get(position)

    def get_moon_event_time(self, event):
        """Return the moon event time as a timestamp with timezone information."""
        event_time = self._moon_times.get(event)
        if event_time:
            iso_time = event_time.isoformat()
            time_replace = iso_time.replace(" ", "T")
            time_utc = time_replace + "Z"
            time_str = datetime.datetime.strptime(time_utc, "%Y-%m-%dT%H:%M:%S.%fZ")
            time_replace = time_str.replace(tzinfo=datetime.UTC)
            _LOGGER.debug(
                "Moon event time: %s raw: %s timezone: %s iso: %s, str: %s, replace: %s",
                event,
                event_time,
                time_replace,
                time_utc,
                time_str,
                time_replace,
            )
            return time_replace
        return None

    def get_moon_phase_name(self):
        """Return the state of the sensor."""
        phase_name = self._moon_illumination.get("phase").get("id")
        if phase_name:
            self._phase_name = phase_name
            return self._phase_name
        return None

    def get_moon_age(self):
        """Return the current moon age."""
        synodicMonth = 29.53058868
        moon_age = self._moon_illumination.get("phaseValue") * synodicMonth
        if moon_age:
            return moon_age
        return None

    def get_next_moon_phase(self, phase):
        """Return the next moon phase date as a datetime object with timezone information."""
        next_obj = self._moon_illumination.get("next")
        phase_date_str = next_obj.get(phase).get("date")
        phase_date = datetime.datetime.strptime(phase_date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        _LOGGER.debug("Next %s: %s, %s", phase, phase_date_str, phase_date)
        return phase_date.replace(tzinfo=datetime.UTC)

    def get_moon_illumination_fraction(self):
        """Return the fraction of the moon that is illuminated."""
        fraction = self._moon_illumination.get("fraction")
        if fraction:
            return fraction * 100
        return None

    def get_moon_attributes(self):
        """Return the moon attributes."""
        self._moon_attributes = {
            STATE_ATTR_AGE: self.get_moon_age(),
            STATE_ATTR_DISTANCE_KM: self.get_current_position("distance"),
            STATE_ATTR_AZIMUTH: self.get_current_position("azimuthDegrees"),
            STATE_ATTR_ALTITUDE: self.get_current_position("altitudeDegrees"),
            STATE_ATTR_PARALLACTIC_ANGLE: self.get_current_position(
                "parallacticAngleDegrees"
            ),
            STATE_ATTR_ILLUMINATION_FRACTION: self.get_moon_illumination_fraction(),
            STATE_ATTR_NEXT_FULL: self.get_next_moon_phase("fullMoon"),
            STATE_ATTR_NEXT_NEW: self.get_next_moon_phase("newMoon"),
            STATE_ATTR_NEXT_THIRD: self.get_next_moon_phase("thirdQuarter"),
            STATE_ATTR_NEXT_FIRST: self.get_next_moon_phase("firstQuarter"),
            STATE_ATTR_NEXT_RISE: self.get_moon_event_time("rise"),
            STATE_ATTR_NEXT_SET: self.get_moon_event_time("set"),
            STATE_ATTR_NEXT_HIGH: self.get_moon_event_time("highest"),
        }

        return self._moon_attributes

    def get_extra_attributes(self):
        """Return the extra attributes."""
        self._extra_attributes = {
            EXTRA_ATTR_AZIMUTH: self.get_current_position("azimuth"),
            EXTRA_ATTR_ALTITUDE: self.get_current_position("altitude"),
            EXTRA_ATTR_PARALLACTIC_ANGLE: self.get_current_position("parallacticAngle"),
        }
        return self._extra_attributes

    def update(self):
        """Update the MoonCalc object."""
        self.get_moon_illumination()
        self.get_moon_position()
        self.get_moon_times()
        self.get_moon_phase_name()
        self.get_moon_attributes()
        self.get_extra_attributes()
