from pydantic import BaseModel

class CatelogItem(BaseModel):
    song_name: str # 歌名
    bpm_min: int # 最小bpm
    bpm_max: int # 最大bpm
    style: str # 风格
    budget: int # 价格