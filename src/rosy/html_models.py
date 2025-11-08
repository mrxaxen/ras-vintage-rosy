from pydantic import BaseModel

class HtmlModRelease(BaseModel):
    compatible_version_low: str
    compatible_version_high: str | None = None
    filename: str
    mainfile: str

class HtmlModEntry(BaseModel):
    name: str
    modid: str
    releases: list[HtmlModRelease]

