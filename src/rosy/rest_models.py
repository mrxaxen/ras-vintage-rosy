from pydantic import BaseModel

class RestModRelease(BaseModel):
    releaseid: int
    mainfile: str
    filename: str
    fileid: int
    tags: list[str]


class RestModEntry(BaseModel):
    name: str
    modid: int
    urlalias: str | None = None
    releases: list[RestModRelease]

class RestMod(BaseModel):
    mod: RestModEntry | None = None
    statuscode: str
