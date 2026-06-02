from app.ingestion.ashby import AshbyIngester
from app.ingestion.greenhouse import GreenhouseIngester
from app.ingestion.lever import LeverIngester

greenhouse = GreenhouseIngester()
lever = LeverIngester()
ashby = AshbyIngester()

INGESTERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
}

__all__ = ["greenhouse", "lever", "ashby", "INGESTERS"]
