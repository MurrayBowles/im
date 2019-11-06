''' Database row buffers '''

from dataclasses import dataclass
from typing import Any, List


@dataclass
class RowBuf(object):
    cols: List[Any]


