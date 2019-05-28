#!/usr/bin/env python3
from absl import app
from absl import flags
from fontTools import ttLib
from fontTools.varLib import instancer
import io
import itertools
import logging
import os
import requests
import traceback

FLAGS = flags.FLAGS

flags.DEFINE_boolean('registered_only', True, 'Whether to try leave non-registered tables ')
flags.DEFINE_string('temp_dir', '/tmp/axis_sizes', 'Scratch directory')
flags.DEFINE_boolean('download', True, 'Whether to try to download samples')
flags.DEFINE_string('output_csv', '/tmp/axis_sizes.csv', 'Scratch directory')

def _font_dir():
  return os.path.join(FLAGS.temp_dir, 'fonts')

def _vf_source_urls():
  with open('vf_source_urls.txt', 'r') as f:
    lines = [l.strip() for l in f.readlines() if not l.startswith('#')]
  return [l for l in lines if l]

def _local_file(font_url):
  return os.path.join(_font_dir(), font_url.rpartition('/')[2])

def _download(url, local_file):
  print('%s => %s' % (url, local_file))
  response = requests.get(url)
  if response.status_code != requests.codes.ok:
    print('  DOWNLOAD FAILED with code %d' % response.status_code)
    return False
  os.makedirs(os.path.dirname(local_file), exist_ok=True)
  with open(local_file, 'wb') as f:
    f.write(response.content)
  return True

def _download_samples():
  urls = _vf_source_urls()
  local_files = [_local_file(u) for u in urls]
  for url, local_file in zip(urls, local_files):
    _download(url, local_file)

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
  for i in range(len(axes)):
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
      return -1
  return len(_save_to_bytes(font).getbuffer())

def _measure_sizes(font_file):
  print('measuring %s' % font_file)
  axes = _axes(font_file)
  ignored = _ignored_axes(font_file)
  for axes_retained in _axis_combinations(axes):
    axis_limits = {tag:None for tag in (axes - axes_retained) | ignored}
    print('%s retain %s drop %s)...' % (os.path.basename(font_file), sorted(axes_retained), sorted(axis_limits.keys())))
    size = _instance_size(font_file, axis_limits)
    print('%s %s %d bytes.' % (os.path.basename(font_file), sorted(axes_retained), size))
    yield (axes_retained, size, axis_limits.keys())

def _test_assets():
  if FLAGS.download:
    _download_samples()

  font_files = [os.path.join(_font_dir(), f) for f in os.listdir(_font_dir())]
  return sorted([f for f in font_files if _isVF(f)])

def _init_output():
  with open(FLAGS.output_csv, 'w') as f:
    f.write('file, axis_removed, axes_retained, size_with_ttf, size_without_ttf\n')

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
    size_by_axes = {axes:(size, dropped) for axes, size, dropped in _measure_sizes(font_file)}
    axes = _axes(font_file)
    for axis in sorted(axes):
      # print sizes between ever combination w/o axis and the same with it
      # purely for convenience in making spreadsheet downstream
      for without_axis in _axis_combinations(axes - {axis}):
        with_axis = without_axis | {axis}
        size_with_axis, _ = size_by_axes[with_axis]
        size_without_axis, _ = size_by_axes[without_axis]
        _output_and_print('%s, %s, "%s", %d, %d' % (
          os.path.basename(font_file),
          axis,
          ','.join(sorted(with_axis)),
          size_with_axis,
          size_without_axis))
  print('Results in %s' % FLAGS.output_csv)


if __name__ == '__main__':
  app.run(main)
