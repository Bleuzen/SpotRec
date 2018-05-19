
python -OO -m py_compile spotrec.py

mv __pycache__/spotrec.cpython-36.opt-2.pyc .
rm -r __pycache__/

echo "SHA1: $(sha1sum spotrec.cpython-36.opt-2.pyc)"
