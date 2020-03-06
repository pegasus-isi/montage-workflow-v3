#!/bin/bash

set -e

export PYTHONPATH=`pegasus-config --python`:$PYTHONPATH

if ! which mViewer >/dev/null 2>&1; then
    echo "Error: Unable to find the Montage tools in your path. Please download and" 1>&2
    echo "       install version 4 or above (http://montage.ipac.caltech.edu)" 1>&2
    exit 1
fi

if [ ! -e montage-workflow.py ]; then
    echo "Error: You have to run this script from the top level workflow checkout" 1>&2
    exit 1
fi
rm -rf data

./montage-workflow.py --center "15.09552 -0.74559" --degrees 2.0 --band 2mass:j:red --band 2mass:h:green --band 2mass:k:blue

pegasus-plan \
        --dir work \
        --dax data/montage-workflow.yaml \
        --output-site local \
        --cluster horizontal

