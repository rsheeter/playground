#!/usr/bin/env python3
from __future__ import annotations  # enable recursive tuples

import json
import collections
import typing
import os
import zipfile
import pprint

# https://developer.sketch.com/reference/api/#rectangle
class Rectangle(typing.NamedTuple):
  x: int
  y: int
  width: int
  height: int

# https://developer.sketch.com/reference/api/#point
class Point(typing.NamedTuple):
  x: float
  y: float


  # init from a sketch file point: {x, y}
  def _parse(point_str):
    x, y = [float(s) for s in point_str[1:-1].split(',')]
    return Point(x, y)

# https://developer.sketch.com/reference/api/#curvepoint
class CurvePoint(typing.NamedTuple):
  curveFrom: Point
  curveTo: Point

# https://developer.sketch.com/reference/api/#layer
class Layer(typing.NamedTuple):
  id: str
  name: str
  frame: Rectangle
  layers: typing.List[Layer]
  points: typing.List[CurvePoint]

# https://developer.sketch.com/reference/api/#page
class Page(typing.NamedTuple):
  id: str
  name: str
  layers: typing.List[Layer]
  frame: Rectangle

class Document(typing.NamedTuple):
  id: str
  pages: typing.List[Page]

_FIELD_MAP = {
  'id': 'do_objectID',
}

def _read_json(zip_file, path):
  with zip_file.open(path) as f:
    return json.loads(f.read())

def _resolve_ref(zip_file, json_obj):
  if not json_obj.get('_class', None) == 'MSJSONFileReference':
    return json_obj
  target = json_obj.get('_ref') + '.json'
  return _read_json(zip_file, target)

def _load_sketch_json(zip_file, json_obj, tuple_type):
  json_obj = _resolve_ref(zip_file, json_obj)
  values = []
  for field_name, field_type in tuple_type._field_types.items():
    if isinstance(field_type, typing.ForwardRef):
      field_type = field_type._evaluate(globals(), locals())
    json_field = _FIELD_MAP.get(field_name, field_name)
    json_value = json_obj.get(json_field, None)
    if getattr(field_type, '__origin__', field_type) == list:
      item_type = field_type.__args__[0]
      a_list = list()
      if json_value:
        for json_list_item in json_value:
          a_list.append(_load_sketch_json(zip_file, json_list_item, item_type))
      values.append(a_list)
    elif hasattr(field_type, '_parse'):
      values.append(field_type._parse(json_value))
    elif hasattr(field_type, '_field_types'):
      values.append(_load_sketch_json(zip_file, json_value, field_type))
    else:
      values.append(field_type(json_value))
  return tuple_type(*values)

def _load_sketch_file(src_file):
  with zipfile.ZipFile(src_file) as zip_file:
    json_doc = _read_json(zip_file, 'document.json')
    return _load_sketch_json(zip_file, json_doc, Document)

def _update_sketch_file(dest_file, doc: Document):
  # align Document with dest contents, including reversing refs (only pages?)
  # write updates into dest
  pass


def _print(a_tuple, depth=0):
  pad = ' ' * depth
  print(f'{pad}{type(a_tuple).__name__}')
  depth += 2
  pad = ' ' * depth
  for idx, (field_name, field_type) in enumerate(a_tuple._field_types.items()):
    if isinstance(field_type, typing.ForwardRef):
      field_type = field_type._evaluate(globals(), locals())
    field_value = a_tuple[idx]
    if getattr(field_type, '__origin__', field_type) == list:
      print(f'{pad}{field_name} =')
      for list_item in field_value:
        _print(list_item, depth + 2)
    elif hasattr(field_type, '_field_types'):
      print(f'{pad}{field_name} =')
      _print(field_value, depth + 2)
    else:
      print(f'{pad}{field_name} = {field_value}')


def main():
  doc = _load_sketch_file('./Sketch1Icon.sketch')
  _print(doc)

if __name__ == '__main__':
  main()
