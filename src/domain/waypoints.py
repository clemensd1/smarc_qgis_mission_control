from typing import Annotated, Self
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .schema import Schema, SchemaMixin, Column, Unit

__all__ = ["Waypoint", "AUVWaypoint", "GeoPoint"]


@dataclass
class Waypoint(SchemaMixin):
    """
    This class represents a bare 2D waypoint, and holds only its location.
    """

    latitude  : Annotated[float, Unit("°"), Column("Lat.", "Latitude" )] \
              = .0
    longitude : Annotated[float, Unit("°"), Column("Lon.", "Longitude")] \
              = .0
    #: Internal use. For associating a `QgsFeatureId` with the waypoint.
    uuid      : UUID = field(default_factory = uuid4, kw_only = True)

    @classmethod
    def fromJson(cls, data: dict) -> Self:
        """Load a waypoint from mission plan JSON."""
        # NOTE: This should be implemented by subclasses
        raise NotImplementedError

    def toJson(self) -> dict:
        """Convert the waypoint to mission plan JSON."""
        return {
            "latitude"  : self.latitude,
            "longitude" : self.longitude,
        }

@dataclass
class AUVWaypoint(Waypoint):
    """
    This class represents waypoints used for autonomous underwater vehicles.
    """

    #: Depth below the sea level. TODO: or below some other level?
    depth        : Annotated[float, Unit("m"), Column("Depth")] \
                 =    .0
    #: Minimum altitude from the sea floor; takes priority over `depth`.
    min_altitude : Annotated[float, Unit("m"), Column("Min. Alt.", "Min. Altitude")] \
                 =    .0
    #: Distance within which the waypoint is considered reached.
    tolerance    : Annotated[float, Unit("m"), Column("Tol.", "Tolerance")] \
                 =  10.0 
    #: RPM used while traveling to the waypoint.
    rpm          : Annotated[float, Column("RPM")] \
                 = 500.0
    #: TODO
    timeout      : Annotated[float, Unit("s"), Column("Timeout")] \
                 =    .0

    def toJson(self) -> dict:
        return super().toJson() | {
            "target_depth" : self.depth,
            "min_altitude" : self.min_altitude,
            "tolerance"    : self.tolerance,
            "rpm"          : self.rpm,
            "timeout"      : self.timeout,
        }

    @classmethod
    def fromJson(cls, data: dict) -> Self:
        # make sure not parsing a WARA-PS GeoPoint by accident
        if data.get("rostype") == "GeoPoint":
            raise ValueError(f"GeoPoint data passed to {cls.__name__}")
        return cls(
            latitude     = float(data["latitude"]),
            longitude    = float(data["longitude"]),
            depth        = float(data["target_depth"]),
            min_altitude = float(data["min_altitude"]),
            tolerance    = float(data["tolerance"]),
            rpm          = float(data["rpm"]),
            timeout      = float(data["timeout"]),
        )

@dataclass
class GeoPoint(Waypoint):
    #: Altitude above some reference height, e.g. geoid or water surface.
    altitude  : Annotated[float, Unit("m"), Column("Alt.", "Altitude")] \
              =   .0
    #: Distance within which the waypoint is considered reached.
    #: NOTE: not part of WARA-PS spec
    tolerance : Annotated[float, Unit("m"), Column("Tol.", "Tolerance")] \
              =  10.0 

    def toJson(self) -> dict:
        return super().toJson() | {
            "altitude"  : self.altitude,
            "tolerance" : self.tolerance,
            "rostype"   : "GeoPoint",
        }

    @classmethod
    def fromJson(cls, data: dict) -> Self:
        # make sure we ARE parsing a WARA-PS GeoPoint
        if data.get("rostype") != "GeoPoint":
            raise ValueError(f"Non-GeoPoint data passed to {cls.__name__}")
        return cls(
            latitude  = float(data["latitude"]),
            longitude = float(data["longitude"]),
            altitude  = float(data["altitude"]),
            tolerance = float(data["tolerance"]),
        )
