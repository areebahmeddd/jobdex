from app.ingestion.ashby import AshbyIngester
from app.ingestion.greenhouse import GreenhouseIngester
from app.ingestion.lever import LeverIngester
from app.ingestion.mcf import MCFIngester
from app.ingestion.pyjamahr import PyjamaHRIngester
from app.ingestion.recruitee import RecruiteeIngester
from app.ingestion.rippling import RipplingIngester
from app.ingestion.smartrecruiters import SmartRecruitersIngester
from app.ingestion.teamtailor import TeamtailorIngester
from app.ingestion.workable import WorkableIngester
from app.ingestion.workday import WorkdayIngester
from app.ingestion.ycombinator import YCombinatorIngester

ashby = AshbyIngester()
greenhouse = GreenhouseIngester()
lever = LeverIngester()
smartrecruiters = SmartRecruitersIngester()
workable = WorkableIngester()
workday = WorkdayIngester()
ycombinator = YCombinatorIngester()
recruitee = RecruiteeIngester()
rippling = RipplingIngester()
teamtailor = TeamtailorIngester()
pyjamahr = PyjamaHRIngester()
mcf = MCFIngester()

INGESTERS = {
    "ashby": ashby,
    "greenhouse": greenhouse,
    "lever": lever,
    "smartrecruiters": smartrecruiters,
    "workable": workable,
    "workday": workday,
    "ycombinator": ycombinator,
    "recruitee": recruitee,
    "rippling": rippling,
    "teamtailor": teamtailor,
    "pyjamahr": pyjamahr,
    "mcf": mcf,
}

__all__ = [
    "ashby",
    "greenhouse",
    "lever",
    "smartrecruiters",
    "workable",
    "workday",
    "ycombinator",
    "recruitee",
    "rippling",
    "teamtailor",
    "pyjamahr",
    "mcf",
    "INGESTERS",
]
