*  Create a virtual environment
*  Clone https://github.com/fonttools/fonttools
*  Checkout the partial-instancer branch of fonttools
   *  Install it (`pip install -e .` from the fonttools root)
*  Install other dependencies into your virtual environment:
   *  `pip install absl-py`
   *  `pip install brotli`
*  Download the font(s) you want to analyze into `/tmp/axis_sizes/fonts`
*  Run `./axis-sizes.py`
