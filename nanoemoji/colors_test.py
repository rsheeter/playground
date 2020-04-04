from colors import Color
import pytest


@pytest.mark.parametrize(
    "color_string, expected_color",
    [
        # 3-hex digits
        ("#BCD", Color(0xBB, 0xCC, 0xDD, 1.0)),
        # 4-hex digits
        ("#BCD3", Color(0xBB, 0xCC, 0xDD, 0.2)),
        # 6-hex digits
        ("#F1E2D3", Color(0xF1, 0xE2, 0xD3, 1.0)),
        # 8-hex digits
        ("#F1E2D366", Color(0xF1, 0xE2, 0xD3, 0.4)),
        # CSS named color
        ("wheat", Color(0xF5, 0xDE, 0xB3, 1.0)),
        # rgb(r,g,b)
        ("rgb(0, 256, -1)", Color(0, 255, 0, 1.0)),
        # rgb(r g b)
        ("rgb(42 101 43)", Color(42, 101, 43, 1.0)),
    ],
)
def test_color_fromstring(color_string, expected_color):
    assert expected_color == Color.fromstring(color_string)
