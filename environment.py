from typing import (
    Mapping,
    Optional,
)


def env() -> Mapping[str, Optional[str]]:
    """
    Returns a dictionary that maps environment variable names to values. The
    values are either None or strings. String values can contain references to
    other environment variables in the form `{FOO}` where FOO is the name of an
    environment variable. See

    https://docs.python.org/3.6/library/string.html#format-string-syntax

    for the concrete syntax. The references will be resolved after the
    environment has been compiled by merging all environment.py files.

    Entries with a None value will be excluded from the environment. They should
    be used to document variables without providing a default value. Other,
    usually more specific environment.py files should provide the value.
    """
    return {
        'CELLXGENE_ZONE_NAME': None,
        'CELLXGENE_DOMAIN_NAME': 'cellxgene.{CELLXGENE_ZONE_NAME}',
        'CELLXGENE_IMAGE': 'gi.ucsc.edu/cellxgene',
        'CELLXGENE_VERSION': '0.14.1',
        'PYTHONPATH': '{project_root}/src',
        'TF_DATA_DIR': '{project_root}/deployments/.active/.terraform.{AWS_PROFILE}',
    }
