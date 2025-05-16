import sys
import pathlib as pl

sys.path.append(str(pl.Path.cwd()))
sys.path.append(
    "~/.cache/pypoetry/virtualenvs/blender-3B2xtVHD-py3.12/lib/python3.12/site-packages"
)
print(sys.path)

from basilisp_blender.nrepl import server_start

shutdown_fn = server_start(host="127.0.0.1", port=8889)
