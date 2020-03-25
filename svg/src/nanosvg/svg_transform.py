"""Helpers for https://www.w3.org/TR/SVG11/coords.html#TransformAttribute.

Focuses on converting to a sequence of affine matrices.
"""
import dataclasses
from math import cos, sin, tan
import re


# attributes declared in order to make vector [a b c d e f]
# when dumped as a tuple:
#
# a   c   e
# b   d   f
#
# meaning:
#
# 
@dataclasses.dataclass(frozen=True)
class Transform:
    a: float
    b: float
    c: float
    d: float
    e: float
    f: float


    @staticmethod
    def identity():
      return Transform(1, 0, 0, 1, 0, 0)


    @staticmethod
    def fromstring(raw_transform):
      return parse_svg_transform(raw_transform)


    def transform(self, transform):
      return self.matrix(*transform.tuple())


    def matrix(self, a, b, c, d, e, f):
        return Transform(
            a * self.a + b * self.c,
            a * self.b + b * self.d,
            c * self.a + d * self.c,
            c * self.b + d * self.d,
            self.a * e + self.c * f + self.e,
            self.b * e + self.d * f + self.f
        )


    # https://www.w3.org/TR/SVG11/coords.html#TranslationDefined
    def translate(self, tx, ty=0):
        if (0, 0) == (tx, ty):
            return self
        return self.matrix(1, 0, 0, 1, tx, ty)


    # https://www.w3.org/TR/SVG11/coords.html#ScalingDefined
    def scale(self, sx, sy=None):
        if sy is None:
            sy = sx
        return self.matrix(sx, 0, 0, sy, 0, 0)


    # https://www.w3.org/TR/SVG11/coords.html#RotationDefined
    def rotate(self, a, cx=0., cy=0.):
        return (self.translate(cx, cy)
                .matrix(cos(a), sin(a), -sin(a), cos(a), 0, 0)
                .translate(-cx, -cy))


    # https://www.w3.org/TR/SVG11/coords.html#SkewXDefined
    def skewx(self, a):
        return self.matrix(1, 0, tan(a), 1, 0, 0)


    # https://www.w3.org/TR/SVG11/coords.html#SkewYDefined
    def skewy(self, a):
        return self.matrix(1, tan(a), 0, 1, 0, 0)


    def tuple(self):
        return dataclasses.astuple(self)


def parse_svg_transform(raw_transform: str):
    # much simpler to read if we do stages rather than a single regex
    transform = Transform.identity()

    svg_transforms = re.split(r'(?<=[)])\s*[,\s]\s*(?=\w)', raw_transform)
    for svg_transform in svg_transforms:
        match = re.match(r'(?i)(matrix|translate|scale|rotate|skewX|skewY)\((.*)\)',
                         svg_transform)
        if not match:
            raise ValueError(f'Unable to parse {raw_transform}')

        args = tuple(float(p) for p in re.split(r'\s*[,\s]\s*', match.group(2)))
        transform = getattr(transform, match.group(1).lower())(*args)

    return transform





