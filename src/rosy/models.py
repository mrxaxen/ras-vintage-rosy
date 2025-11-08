from pydantic import BaseModel

class VSManagerConfig(BaseModel):
    version: str
    download_folder: str
    mods: list[str]
