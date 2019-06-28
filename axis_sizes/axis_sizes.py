#!/usr/bin/env python3
from absl import app
from absl import flags
from fontTools import ttLib
from fontTools.varLib import instancer
import io
import itertools
import logging
import os
import re
import traceback

FLAGS = flags.FLAGS

flags.DEFINE_boolean('registered_only', True, 'Whether to try leave non-registered tables ')
flags.DEFINE_string('font_dir', '/tmp/axis_sizes/fonts', 'Where to find the fonts')
flags.DEFINE_string('temp_dir', '/tmp/axis_sizes', 'Scratch directory')
flags.DEFINE_string('output_csv', '/tmp/axis_sizes.csv', 'Scratch directory')
flags.DEFINE_string('filter', None, 'filename regex')

def _font_dir():
  return FLAGS.font_dir

def _local_file(font_url):
  return os.path.join(_font_dir(), font_url.rpartition('/')[2])

def _ttFont(font_file):
  return ttLib.TTFont(font_file)

def _isVF(font_file):
  try:
    font = _ttFont(font_file)
    if not 'fvar' in font:
      print('%s NO \'fvar\'' % font_file)
      return False
  except ttLib.TTLibError as e:
    print('%s BAD FONT: %s' % (font_file, str(e)))
    return False
  return True

def _all_axes(font_file):
  font = _ttFont(font_file)
  if not 'fvar' in font:
    return frozenset()
  return frozenset({a.axisTag for a in font['fvar'].axes})

def _axes(font_file):
  axes = _all_axes(font_file)
  if FLAGS.registered_only:
    axes = {a for a in axes if a == a.lower()}
  return frozenset(axes)

def _ignored_axes(font_file):
  return _all_axes(font_file) - _axes(font_file)

def _axis_combinations(axes):
  for i in range(len(axes) + 1):
    for axis_combination in itertools.combinations(axes, i):
      yield frozenset(axis_combination)

def _drop_axes(font, axes):
  if not axes:
    return font
  return instancer.instantiateVariableFont(font, {tag: None for tag in axes}, inplace=True)

def _save_to_bytes(font):
  font_bytes = io.BytesIO()
  font.save(font_bytes)
  return font_bytes

def _instance_size(font_file, axis_limits):
  font = _ttFont(font_file)
  if axis_limits:
    try:
      instancer.instantiateVariableFont(font, axis_limits, inplace=True)
    except Exception:
      print('FAILED TO INSTANCE %s at %s' % (font_file, axis_limits))
      print(traceback.print_exc())
      return (-1, -1)
  ttf_sz = len(_save_to_bytes(font).getbuffer())
  font.flavor = 'woff2'
  woff2_sz = len(_save_to_bytes(font).getbuffer())
  return (ttf_sz, woff2_sz)

def _measure_sizes(font_file):
  print('measuring %s' % font_file)
  axes = _axes(font_file)
  ignored = _ignored_axes(font_file)
  for axes_retained in _axis_combinations(axes):
    axis_limits = {tag:None for tag in (axes - axes_retained) | ignored}
    print('%s retain %s drop %s)...' % (os.path.basename(font_file), sorted(axes_retained), sorted(axis_limits.keys())))
    ttf_sz, woff2_sz = _instance_size(font_file, axis_limits)
    print('%s %s %d byte ttf, %d byte woff2.' % (os.path.basename(font_file), sorted(axes_retained), ttf_sz, woff2_sz))
    yield (axes_retained, ttf_sz, woff2_sz)

def _test_assets():
  font_files = [os.path.join(_font_dir(), f) for f in os.listdir(_font_dir())]
  if FLAGS.filter:
    font_files = [f for f in font_files if re.search(FLAGS.filter, f)]
  return sorted([f for f in font_files if _isVF(f)])

def _init_output():
  with open(FLAGS.output_csv, 'w') as f:
    f.write('file, axes, axis_removed, ttf_before, ttf_after, woff2_before, woff2_after\n')

def _output_and_print(line):
  print(line)
  with open(FLAGS.output_csv, 'a') as f:
    f.write(line)
    f.write('\n')

def main(_):
  font_files = _test_assets()
  for font_file in font_files:
    print('%s consider {%s} ignore {%s}' % (font_file, 
      ','.join(sorted(_axes(font_file))),
      ','.join(sorted(_ignored_axes(font_file)))))

  _init_output()
  for font_file in font_files:
    axes = _axes(font_file)
    combinations = [c for c in _axis_combinations(axes)]
    size_by_axes = {axes:(ttf_sz, woff2_sz) for axes, ttf_sz, woff2_sz in _measure_sizes(font_file)}
    for axis in sorted(axes):
      # print sizes between ever combination w/o axis and the same with it
      # purely for convenience in making spreadsheet downstream
      for with_axis in [c for c in combinations if axis in c]:
        without_axis = with_axis - {axis}
        size_before_ttf, size_before_woff2 = size_by_axes[with_axis]
        size_after_ttf, size_after_woff2 = size_by_axes[without_axis]
        _output_and_print('%s, "%s", %s, %d, %d, %d, %d' % (
          os.path.basename(font_file),
          ','.join(sorted(with_axis)),
          axis,
          size_before_ttf, size_after_ttf,
          size_before_woff2, size_after_woff2))
  print('Results in %s' % FLAGS.output_csv)


if __name__ == '__main__':
  app.run(main)
