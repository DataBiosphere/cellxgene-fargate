#!/bin/bash

set -o allexport
source environment.env
set +o allexport

cellxgene launch --verbose $CXG_DATA_URL $CXG_BACKED --host 0.0.0.0 --port $CXG_PORT

