#!/bin/bash

set -e

if [ ! -e montage-workflow.py ]; then
    echo "Error: You have to run this script from the top level workflow checkout" 1>&2
    exit 1
fi
rm -rf data

# the workflow generator needs to have access to the Montage tools - run it in a container
apptainer exec \
            --bind $PWD \
            https://download.pegasus.isi.edu/containers/montage/montage-workflow-v3-20260810.sif \
            python3.12 $PWD/montage-workflow.py \
                --work-dir $PWD \
                 --center "15.09552 -0.74559" \
                --degrees 1.0 \
                --band 2mass:j:red \
                --band 2mass:h:green \
                --band 2mass:k:blue

# plan the workflow
pegasus-plan \
        --dir work \
        --output-site local \
        --cluster horizontal \
        data/montage-workflow.yml

