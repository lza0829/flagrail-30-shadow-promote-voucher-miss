"""兼容性别名：金丝雀影子道的实现位于 app.modules.金丝雀影子道。"""
from app.modules.金丝雀影子道 import *  
from app.modules import 金丝雀影子道 as _核心  

for _n in dir(_核心):
    if not _n.startswith("_"):
        globals()[_n] = getattr(_核心, _n)
