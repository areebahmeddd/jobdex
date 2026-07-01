from app.ingestion.europe.recruitee import RecruiteeIngester
from app.ingestion.india.pyjamahr import PyjamaHRIngester
from app.ingestion.usa.ashby import AshbyIngester
from app.ingestion.usa.greenhouse import GreenhouseIngester
from app.ingestion.usa.lever import LeverIngester
from app.ingestion.usa.smartrecruiters import SmartRecruitersIngester
from app.ingestion.usa.workable import WorkableIngester
from app.ingestion.usa.ycombinator import YCombinatorIngester

ashby = AshbyIngester()
greenhouse = GreenhouseIngester()
lever = LeverIngester()
pyjamahr = PyjamaHRIngester()
recruitee = RecruiteeIngester()
smartrecruiters = SmartRecruitersIngester()
workable = WorkableIngester()
ycombinator = YCombinatorIngester()

INGESTERS = {
    "ashby": ashby,
    "greenhouse": greenhouse,
    "lever": lever,
    "pyjamahr": pyjamahr,
    "recruitee": recruitee,
    "smartrecruiters": smartrecruiters,
    "workable": workable,
    "ycombinator": ycombinator,
}

__all__ = [
    "ashby",
    "greenhouse",
    "lever",
    "pyjamahr",
    "recruitee",
    "smartrecruiters",
    "workable",
    "ycombinator",
    "INGESTERS",
]
