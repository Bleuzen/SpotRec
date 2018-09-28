
python -OO -m py_compile spotrec.py

mv __pycache__/spotrec.cpython-37.opt-2.pyc .
rm -r __pycache__/

echo "SHA256: $(sha256sum spotrec.cpython-37.opt-2.pyc)"
