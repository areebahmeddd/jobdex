from app.ingestion.ashby import AshbyIngester
from app.ingestion.greenhouse import GreenhouseIngester
from app.ingestion.lever import LeverIngester
from app.ingestion.ycombinator import YCombinatorIngester

ashby = AshbyIngester()
greenhouse = GreenhouseIngester()
lever = LeverIngester()
ycombinator = YCombinatorIngester()

INGESTERS = {
    "ashby": ashby,
    "greenhouse": greenhouse,
    "lever": lever,
    "ycombinator": ycombinator,
}

__all__ = ["ashby", "greenhouse", "lever", "ycombinator", "INGESTERS"]
