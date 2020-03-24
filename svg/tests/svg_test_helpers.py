from lxml import etree
import os
from nanosvg.svg import SVG


def _locate_test_file(filename):
    return os.path.join(os.path.dirname(__file__), filename)


def load_test_svg(filename):
    return SVG.parse(_locate_test_file(filename))


def svg_string(*els):
    root = etree.fromstring('<svg version="1.1" xmlns="http://www.w3.org/2000/svg"/>')
    for el in els:
        root.append(etree.fromstring(el))
    return etree.tostring(root)


def pretty_print(svg_tree):
    def _reduce_text(text):
        text = text.strip() if text else None
        return text if text else None

    # lxml really likes to retain whitespace
    for e in svg_tree.iter("*"):
        e.text = _reduce_text(e.text)
        e.tail = _reduce_text(e.tail)

    return etree.tostring(svg_tree, pretty_print=True).decode("utf-8")


def drop_whitespace(svg):
    svg._update_etree()
    for el in svg.svg_root.iter("*"):
        if el.text is not None:
            el.text = el.text.strip()
        if el.tail is not None:
            el.tail = el.tail.strip()
