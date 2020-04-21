#!/bin/bash

set -e

export PYTHONPATH=`pegasus-config --python`:$PYTHONPATH

if [ ! -e montage-workflow.py ]; then
    echo "Error: You have to run this script from the top level workflow checkout" 1>&2
    exit 1
fi
rm -rf data

singularity exec \
            --bind $PWD \
            library://rynge/default/montage:latest \
            $PWD/montage-workflow.py \
                --work-dir $PWD \
                --tc-target container \
                --center "56.7 24.00" \
                --degrees 1.0 \
                --band dss:DSS2B:blue \
                --band dss:DSS2R:green \
                --band dss:DSS2IR:red

# rc needs to have paths "outside" the image
perl -p -i -e "s;/srv/data;$PWD/data;g" data/rc.txt

pegasus-plan \
        --dir work \
        --dax data/montage-workflow.yml \
        --output-site local \
        --cluster horizontal 
