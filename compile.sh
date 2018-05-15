# Without optimize
#python -m py_compile spotifyrecorder.py

# remove assert and __debug__-dependent statements; add .opt-1 before .pyc extension; also PYTHONOPTIMIZE=x
#python -O -m py_compile spotifyrecorder.py

# do -O changes and also discard docstrings; add .opt-2 before .pyc extension
python -OO -m py_compile spotifyrecorder.py


mv __pycache__/spotifyrecorder.cpython-36.opt-2.pyc .
rm -r __pycache__/
