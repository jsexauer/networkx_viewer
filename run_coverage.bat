set PYTHONPATH=.

coverage run --include=networkx_viewer\* networkx_viewer\tests.py
coverage html

start chrome .\htmlcov\index.html
