''' Database row buffers and descriptors '''

from dataclasses import dataclass
from typing import Any, List


@dataclass
class RowBuf(object):
    cols: List[Any]




