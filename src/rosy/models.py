from pydantic import BaseModel

class VSManagerConfig(BaseModel):
    version: str
    download_folder: str
    mods: list[str]


class DBModRelease(BaseModel):
    filename: str
    url: str


class DBModEntry(BaseModel):
    name: str
    modid: str
    installed_release: DBModRelease


class ModDB(BaseModel):
    current_version: str
    mods: list[DBModEntry]
