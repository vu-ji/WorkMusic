from pydantic import BaseModel

class TrackCandidate(BaseModel):
    song_name: str
    hit_reason: str
    estimated_price: str

class CatalogResponse(BaseModel):
    model_config = {"extra": "forbid"}  # 多了字段直接抛错
    """
    返回的结果
    """
    follow_up: str
    requirements: str
    candidates: list[TrackCandidate] | None