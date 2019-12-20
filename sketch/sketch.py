#!/usr/bin/env python3

import collections
import dataclasses
import json
import os
import pprint
import typing
import zipfile
from absl import app
from absl import flags
from fontTools.svgLib.path import SVGPath
from fontTools.pens.basePen import AbstractPen

_BLANK_SKETCH_FILE = '1-blank.sketch'

FLAGS = flags.FLAGS

flags.DEFINE_string('input', '', 'Sketch file or svg file.')
flags.DEFINE_string('output', '', 'Sketch file, produced from svg.')


# https://developer.sketch.com/reference/api/#rectangle
@dataclasses.dataclass
class Rectangle:
  x: int = 0
  y: int = 0
  width: int = 0
  height: int = 0

# https://developer.sketch.com/reference/api/#point
@dataclasses.dataclass
class Point:
  x: float = 0
  y: float = 0

  # init from a sketch file point: {x, y}
  def _parse(point_str: str):
    x, y = [float(s) for s in point_str[1:-1].split(',')]
    return Point(x, y)

# https://developer.sketch.com/reference/api/#curvepoint
@dataclasses.dataclass
class CurvePoint:
  point: Point = Point()
  curveFrom: Point = Point()
  curveTo: Point = Point()

# https://developer.sketch.com/reference/api/#layer
@dataclasses.dataclass
class Layer:
  do_objectID: str
  name: str
  frame: Rectangle = Rectangle()
  layers: typing.List['Layer'] = dataclasses.field(default_factory=list)
  points: typing.List[CurvePoint] = dataclasses.field(default_factory=list)

# https://developer.sketch.com/reference/api/#page
@dataclasses.dataclass
class Page:
  do_objectID: str
  name: str
  layers: typing.List[Layer] = dataclasses.field(default_factory=list)
  frame: Rectangle = Rectangle()

@dataclasses.dataclass
class PageRef:
  _class: str = 'MSJSONFileReference'
  _ref_class: str = 'MSImmutablePage'
  _ref: str = ''

  def to(page: Page):
    return PageRef(_ref=f'pages/{page.do_objectID}.json')


@dataclasses.dataclass
class Document:
  do_objectID: str
  pages: typing.List[PageRef] = dataclasses.field(default_factory=list)

@dataclasses.dataclass
class SketchFile:
  document: Document
  pages: typing.List[Page] = dataclasses.field(default_factory=list)

  def update_refs(self):
    pages = [PageRef.to(p) for p in self.pages]

# ref fonttools/Lib/fontTools/pens/basePen.py 
class SketchPen(AbstractPen):
  def __init__(self):
    self.points = []

  def moveTo(self, p0):
    pt = Point(p0[0], p0[1])
    self.points.append(CurvePoint(pt, pt, pt))

  def lineTo(self, p1):
    pt = Point(p1[0], p1[1])
    self.points.append(CurvePoint(pt, pt, pt))

  def qCurveTo(self, *points):
    #self.points.append(('qCurveTo', points))
    print('qCurveTo')
    pass

  def curveTo(self, *points):
    #self.points.append(('curveTo', points))
    print('curveTo')
    pass

  def closePath(self):
    print('closePath')
    pass

  def endPath(self):
    print('endPath')
    pass

  def points(self):
    return points

def _bbox(layers):
  """Find box containing all the points in layers (curves could go out)."""
  minx = miny = maxx = maxy = 0
  for layer in layers:
    for curve_point in layer.points:
      minx = min(minx, curve_point.point.x)
      miny = min(miny, curve_point.point.y)
      maxx = max(maxx, curve_point.point.x)
      maxy = max(maxy, curve_point.point.y)
    minx2, miny2, maxx2, maxy2 = _bbox(layer.layers)
    minx = min(minx, minx2)
    miny = min(miny, miny2)
    maxx = max(maxx, maxx2)
    maxy = max(maxy, maxy2)
  return (minx, miny, maxx, maxy)


def _read_json(zip_file, path):
  with zip_file.open(path) as f:
    return json.loads(f.read())

def _load_sketch_json(json_obj, data_class):
  values = []

  for field in dataclasses.fields(data_class):
    field_type = field.type
    if isinstance(field_type, typing.ForwardRef):
      field_type = field_type._evaluate(globals(), locals())
    json_value = json_obj.get(field.name, None)

    if getattr(field_type, '__origin__', field_type) == list:
      item_type = field_type.__args__[0]
      a_list = list()
      if json_value:
        for json_list_item in json_value:
          a_list.append(_load_sketch_json(json_list_item, item_type))
      values.append(a_list)
    elif hasattr(field_type, '_parse'):
      values.append(field_type._parse(json_value))
    elif dataclasses.is_dataclass(field_type):
      values.append(_load_sketch_json(json_value, field_type))
    else:
      values.append(field_type(json_value))
  return data_class(*values)

def _read_sketch_file(src_file):
  with zipfile.ZipFile(src_file) as zip_file:
    json_doc = _read_json(zip_file, 'document.json')
    doc = _load_sketch_json(json_doc, Document)
    _print(doc)
    pages = [_load_sketch_json(_read_json(zip_file, r._ref + '.json'), Page)
             for r in doc.pages]
  return SketchFile(doc, pages)

def _write_sketch_file(dest_file, sketch_file: SketchFile):
  # write updates into dest

  sketch_file.update_refs()

  doc_dest = os.path.join(dest_file, 'document.json')
  print(f'Write {doc_dest}')
  with open(doc_dest, 'w') as f:
    json.dump(dataclasses.asdict(sketch_file.document), f, indent=2)

  for page in sketch_file.pages:
    page_dest = os.path.join(dest_file, f'{page.do_objectID}.json')
    print(f'Write {page_dest}')
    with open(page_dest, 'w') as f:
      json.dump(dataclasses.asdict(page), f, indent=2)


def _print(data_obj, depth=0, data_class=None):
  if not data_class:
    data_class = type(data_obj)
  if not dataclasses.is_dataclass(data_class):
    raise ValueError(f'Unable to identify dataclass for {data_obj}')

  field_types = {f.name: f.type for f in dataclasses.fields(data_class)}
  field_values = data_obj
  if dataclasses.is_dataclass(data_obj):
    field_values = dataclasses.asdict(data_obj)

  print('PRINT')
  print(data_class)
  print(field_types)
  print(field_values)

  pad = ' ' * depth
  print(f'{pad}{data_class.__name__}')
  depth += 2
  pad = ' ' * depth

  for field_name in sorted(field_values.keys()):
    field_type = field_types[field_name]
    field_value = field_values[field_name]
    if isinstance(field_type, typing.ForwardRef):
      field_type = field_type._evaluate(globals(), locals())
    if isinstance(field_value, list):
      print(f'{pad}{field_name} =')
      for list_item in field_value:
        _print(list_item, depth=depth + 2, data_class=field_type.__args__[0])
    elif dataclasses.is_dataclass(field_type):
      print(f'{pad}{field_name} =')
      _print(field_value, depth=depth + 2, data_class=field_type)
    else:
      print(f'{pad}{field_name} = {field_value}')


def main(argv):
  _, ext = os.path.splitext(FLAGS.input)
  if ext == '.sketch':
    doc = _read_sketch_file(FLAGS.input)
    _print(doc)

    _write_sketch_file('/tmp/test.sketch', doc)
  elif ext == '.svg':
    pen = SketchPen()

    path = SVGPath(FLAGS.input)
    path.draw(pen)

    icon_layer = Layer('artboard', 'Icons', Rectangle(0, 0, 10, 20), [], pen.points)

    doc = _read_sketch_file(_BLANK_SKETCH_FILE)
    doc.pages[0].layers.append(icon_layer)
    doc.pages[0].frame = Rectangle(*_bbox(doc.pages[0].layers))

    print(dataclasses.asdict(doc))
    _print(doc)
  else:
    raise ValueError(f'What to do with {FLAGS.input}')

if __name__ == '__main__':
  app.run(main)
