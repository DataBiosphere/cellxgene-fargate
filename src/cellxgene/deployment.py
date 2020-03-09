import json
import os
import sys
import tempfile
from typing import (
    Optional,
    Mapping,
    Any,
)

from cellxgene.types import JSON


def _sanitize_tf(tf_config: JSON) -> JSON:
    """
    Avoid errors like

        Error: Missing block label

          on api_gateway.tf.json line 12:
          12:     "resource": []

        At least one object property is required, whose name represents the resource
        block's type.
    """
    return {k: v for k, v in tf_config.items() if v}


def emit(json_doc: Optional[Mapping[str, Any]]):
    path = sys.argv[1]
    if json_doc is None:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        else:
            print(f"Removing {path}")
    else:
        f = tempfile.NamedTemporaryFile(mode='w+', dir=os.path.dirname(path), encoding='utf-8', delete=False)
        try:
            json.dump(json_doc, f, indent=4)
        except BaseException:
            os.unlink(f.name)
            raise
        else:
            print(f"Creating {path}")
            os.rename(f.name, path)
        finally:
            f.close()


def emit_tf(tf_config: Optional[JSON]):
    return emit(tf_config if tf_config is None else _sanitize_tf(tf_config))
