from setuptools import setup
from Cython.Build import cythonize

files = [
    "main.py",
    "config.py",
    "database.py",
    "network.py",
    "gui/base.py",
    "gui/chat_page.py",
    "gui/dialogs.py"
]

setup(
    ext_modules = cythonize(files, compiler_directives={'language_level': "3"})
)