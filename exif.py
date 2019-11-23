''' EXIF data extracted from images '''

from typing import Tuple


class Exif(object):
    any_set: bool
    image_size: Tuple[int, int]  # width, height
    focal_length: float
    flash: str
    shutter_speed: float
    aperture: float
    sensitivity: int

    def __init__(self):
        pass  # all fields default to None


attrs = [  # (exiftool argument, Exif attribute, conversion function)
    ('ImageSize', 'image_size', lambda x: tuple([int(e) for e in x.split('x')])),
    ('FocalLength', 'focal_length', lambda x: float(x[0:-3])),  # remove trailing ' mm''
    ('Flash', 'flash'),
    ('ExposureTime', 'shutter_speed', lambda x: int(x.split('/')[0]) / int(x.split('/')[1])),
    ('FNumber', 'aperture'),
    ('ISO', 'sensitivity'),
    # special-case handling by IEImage.get_exiftool_json
    ('XMP-dc:subject',),
    ('XMP-lr:hierarchicalSubject',)
]