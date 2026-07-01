from app.ingestion.ashby import AshbyIngester
from app.ingestion.greenhouse import GreenhouseIngester
from app.ingestion.lever import LeverIngester
from app.ingestion.mcf import MCFIngester
from app.ingestion.pyjamahr import PyjamaHRIngester
from app.ingestion.recruitee import RecruiteeIngester
from app.ingestion.smartrecruiters import SmartRecruitersIngester
from app.ingestion.workable import WorkableIngester
from app.ingestion.ycombinator import YCombinatorIngester

ashby = AshbyIngester()
greenhouse = GreenhouseIngester()
lever = LeverIngester()
smartrecruiters = SmartRecruitersIngester()
workable = WorkableIngester()
ycombinator = YCombinatorIngester()
recruitee = RecruiteeIngester()
pyjamahr = PyjamaHRIngester()
mcf = MCFIngester()

INGESTERS = {
    "ashby": ashby,
    "greenhouse": greenhouse,
    "lever": lever,
    "smartrecruiters": smartrecruiters,
    "workable": workable,
    "ycombinator": ycombinator,
    "recruitee": recruitee,
    "pyjamahr": pyjamahr,
    "mcf": mcf,
}

__all__ = [
    "ashby",
    "greenhouse",
    "lever",
    "smartrecruiters",
    "workable",
    "ycombinator",
    "recruitee",
    "pyjamahr",
    "mcf",
    "INGESTERS",
]
