"""Path builders for forecast archive and storage locations."""

#################################################
#   
#   Università Degli Studi di Napoli Parthenope 
#
#
# Authors: 
#    Prof. Raffaele Montella
#    Dario Caramiello   
#
#################################################

from datetime import datetime, timezone
from pathlib import Path

from core.Places import Places

class MakeArchivePaths:
    """Build paths to forecast and historical NetCDF archives."""

    @staticmethod
    def _parse_date(value):
        """Parse the archive timestamp format, defaulting to today's UTC run."""
        if value is None:
            now = datetime.now(timezone.utc)
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            return datetime.strptime(value, "%Y%m%dZ%H%M")
        except (TypeError, ValueError) as exc:
            raise ValueError("date must use the YYYYMMDDZHHMM format") from exc

    @staticmethod
    def makePath(
        prod, place=None, date=None, history=None, lat=None, lon=None, *, config
    ):
        """Build an archive path using the caller's explicit application config."""
        archive_date = MakeArchivePaths._parse_date(date)

        if lat is not None and lon is not None:
            domain = Places(config).get_domain_by_product_and_ll(prod, lat, lon)
        else:
            domain, *_ = Places(config).get_domain_and_indeces_by_product_and_place(
                prod, place, archive_date.strftime("%Y%m%dZ%H00")
            )

        if history:
            base_path = config["BASE_PATH_HISTORY"]
            archive_directory = config["HISTORY"]
        else:
            base_path = config["BASE_PATH"]
            archive_directory = config["ARCHIVE"]

        timestamp = archive_date.strftime("%Y%m%dZ%H%M")
        daily_path = archive_date.strftime("%Y/%m/%d")
        filename = f"{prod}_{domain}_{timestamp}.nc"
        return str(Path(base_path) / prod / domain / archive_directory / daily_path / filename)

 
