#!/bin/bash

set -e

export PYTHONPATH=`pegasus-config --python`:$PYTHONPATH

if [ ! -e montage-workflow.py ]; then
    echo "Error: You have to run this script from the top level workflow checkout" 1>&2
    exit 1
fi
rm -rf data

apptainer exec \
            --bind $PWD \
            https://data.isi.edu/montage/images/montage-workflow-v3.sif \
            $PWD/montage-workflow.py \
                --work-dir $PWD \
                --tc-target container \
                --center "56.7 24.00" \
                --degrees 1.0 \
                --band dss:DSS2B:blue \
                --band dss:DSS2R:green \
                --band dss:DSS2IR:red

pegasus-plan \
        --dir work \
        --output-site local \
        --cluster horizontal \
        data/montage-workflow.yml
