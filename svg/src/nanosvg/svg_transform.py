"""Helpers for https://www.w3.org/TR/SVG11/coords.html#TransformAttribute.

Focuses on converting to a sequence of affine matrices.
"""
import collections
from math import cos, sin, radians, tan
import re
from typing import NamedTuple


_SVG_ARG_FIXUPS = collections.defaultdict(
    lambda: lambda _: None,
    {
        "rotate": lambda args: _fix_rotate(args),
        "skewx": lambda args: _fix_rotate(args),
        "skewy": lambda args: _fix_rotate(args),
    },
)


# 2D affine transform.
#
# View as vector of 6 values or matrix:
#
# a   c   e
# b   d   f
class Affine2D(NamedTuple):
    a: float
    b: float
    c: float
    d: float
    e: float
    f: float

    @staticmethod
    def identity():
        return Affine2D._identity

    @staticmethod
    def fromstring(raw_transform):
        return parse_svg_transform(raw_transform)

    def concat(self, other: "Affine2D") -> "Affine2D":
        return self.matrix(*other)

    def matrix(self, a, b, c, d, e, f):
        return Affine2D(
            a * self.a + b * self.c,
            a * self.b + b * self.d,
            c * self.a + d * self.c,
            c * self.b + d * self.d,
            self.a * e + self.c * f + self.e,
            self.b * e + self.d * f + self.f,
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
    # Note that rotation here is in radians
    def rotate(self, a, cx=0.0, cy=0.0):
        return (
            self.translate(cx, cy)
            .matrix(cos(a), sin(a), -sin(a), cos(a), 0, 0)
            .translate(-cx, -cy)
        )

    # https://www.w3.org/TR/SVG11/coords.html#SkewXDefined
    def skewx(self, a):
        return self.matrix(1, 0, tan(a), 1, 0, 0)

    # https://www.w3.org/TR/SVG11/coords.html#SkewYDefined
    def skewy(self, a):
        return self.matrix(1, tan(a), 0, 1, 0, 0)


Affine2D._identity = Affine2D(1, 0, 0, 1, 0, 0)


def _fix_rotate(args):
    args[0] = radians(args[0])
    print("_fix_rotate")


def parse_svg_transform(raw_transform: str):
    # much simpler to read if we do stages rather than a single regex
    transform = Affine2D.identity()

    svg_transforms = re.split(r"(?<=[)])\s*[,\s]\s*(?=\w)", raw_transform)
    for svg_transform in svg_transforms:
        match = re.match(
            r"(?i)(matrix|translate|scale|rotate|skewX|skewY)\((.*)\)", svg_transform
        )
        if not match:
            raise ValueError(f"Unable to parse {raw_transform}")

        op = match.group(1).lower()
        args = [float(p) for p in re.split(r"\s*[,\s]\s*", match.group(2))]
        print(op, "args pre-fixup", args)
        _SVG_ARG_FIXUPS[op](args)
        print(op, "args post-fixup", args)
        transform = getattr(transform, op)(*args)

    return transform
