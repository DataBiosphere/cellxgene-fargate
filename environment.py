import os

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
        # The name of the Route 53 hosted zone in which to create the records
        # that point to the individual Fargate containers. This zone has to
        # exist.
        #
        'CELLXGENE_ZONE_NAME': None,

        # The parent domain of the records in the zone identified by
        # CELLXGENE_ZONE_NAME. Each container will be assigned a subdomain of
        # the domain given here. CELLXGENE_ZONE_NAME must be a suffix of this
        # value. Both values may even be identical.
        #
        'CELLXGENE_DOMAIN_NAME': 'cellxgene.{CELLXGENE_ZONE_NAME}',

        # The name of the Docker image repository to which the cellxgene Docker
        # image will be pushed.
        #
        'CELLXGENE_IMAGE': 'gi.ucsc.edu/cellxgene',

        # The version of cellxgene to install into the virtualenv and the image.
        #
        'CELLXGENE_VERSION': '0.15.0',

        # The variables below this point aren't meant to be customized. Things
        # may break if they are changed.

        # FIXME: remove (https://github.com/DataBiosphere/azul/issues/1644)
        # FIXME: can't use '{project_root}' due to https://github.com/DataBiosphere/azul/issues/1645
        'azul_home': os.environ['project_root'],

        # A short string (no punctuation allowed) that identifies a Terraform
        # component i.e., a distinct set of Terraform resources to be deployed
        # together but separately from resources in other components. They are
        # typically defined in a subdirectory of the `terraform` directory and have
        # their own directory under `deployments`. The main component is identified
        # by the empty string and its resources are defined in the `terraform`
        # directory.
        'azul_terraform_component': '',

        # https://docs.python.org/3.6/using/cmdline.html#envvar-PYTHONPATH
        'PYTHONPATH': '{project_root}/src',

        # https://www.terraform.io/docs/commands/environment-variables.html#tf_data_dir
        'TF_DATA_DIR': '{project_root}/deployments/.active/.terraform.{AWS_PROFILE}',
    }
