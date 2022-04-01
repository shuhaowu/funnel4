from setuptools import setup, find_packages

setup(
  name="funnel4",
  version="0.1",
  py_modules=["funnel4"],
  install_requires=[
    "pyaml>=0.2.5",
    "docutils>=0.17.1",
    "jinja2>=3.0.1",
    "Pygments",
    "beautifulsoup4",
  ],
  entry_points={
    "console_scripts": ["funnel4 = funnel4:main"]
  }
)
