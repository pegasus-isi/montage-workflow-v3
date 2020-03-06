# montage-workflow-v3

*NOTE: This is a Montage workflow version which requires Pegasus 5.0. For a version that works with
Pegasus 4, please use `montage-workflow-v2`*

A new Python DAX generator version of the classic Montage workflow. This workflow uses the [Montage
toolkit](http://montage.ipac.caltech.edu) to re-project, background correct and add astronomical
images into custom mosaics.

## Prerequisites

 * [Pegasus](https://pegasus.isi.edu) - version 5.0 or later
 * [Montage](http://montage.ipac.caltech.edu) - version 6.0 or later
 * [AstroPy](http://www.astropy.org/) - version 1.0 or later

## Plan a Montage Workflow

The _./montage-workflow.py_ Python script sets up a _data/_ directory with a Pegasus DAX,
image tables and region headers. For example:

    ./montage-workflow.py --center "56.7 24.0" --degrees 2.0 \
              --band dss:DSS2B:blue --band dss:DSS2R:green --band dss:DSS2IR:red

This will create a 2x2 degree mosaic centered on 56.7 24.0, with 3 bands making up the
red, green, and blue channels for the final JPEG output. A 2 degree workflow has a lot
of input images and thus the workflow becomes wide. I simplified version of the workflow
looks like:

![DAX 1](docs/images/dax1.png?raw=true "DAX 1")

## Examples

The quickest way to get started is to use the _./example-dss.sh_
script. It shows how to use the _montage-workflow.py_ DAX generator to set up and plan
2 degree workflows as described above. Example:

    $ ./example-dss.sh 
    
    Adding band 1 (dss DSS2B -> blue)
    Running sub command: mArchiveList dss DSS2B "56.7 24.00" 2.2 2.2 data/1-images.tbl
    [struct stat="OK", count="16"]
    Running sub command: cd data && mDAGTbls 1-images.tbl region-oversized.hdr 1-raw.tbl 1-projected.tbl 1-corrected.tbl
    [struct stat="OK", count="16", total="16"]
    Running sub command: cd data && mOverlaps 1-raw.tbl 1-diffs.tbl
    [struct stat="OK", count=120]
    
    Adding band 2 (dss DSS2R -> green)
    Running sub command: mArchiveList dss DSS2R "56.7 24.00" 2.2 2.2 data/2-images.tbl
    [struct stat="OK", count="16"]
    Running sub command: cd data && mDAGTbls 2-images.tbl region-oversized.hdr 2-raw.tbl 2-projected.tbl 2-corrected.tbl
    [struct stat="OK", count="16", total="16"]
    Running sub command: cd data && mOverlaps 2-raw.tbl 2-diffs.tbl
    [struct stat="OK", count=120]
    
    Adding band 3 (dss DSS2IR -> red)
    Running sub command: mArchiveList dss DSS2IR "56.7 24.00" 2.2 2.2 data/3-images.tbl
    [struct stat="OK", count="16"]
    Running sub command: cd data && mDAGTbls 3-images.tbl region-oversized.hdr 3-raw.tbl 3-projected.tbl 3-corrected.tbl
    [struct stat="OK", count="16", total="16"]
    Running sub command: cd data && mOverlaps 3-raw.tbl 3-diffs.tbl
    [struct stat="OK", count=120]
    2016.06.02 21:46:32.455 PDT:    
    2016.06.02 21:46:32.461 PDT:   ----------------------------------------------------------------------- 
    2016.06.02 21:46:32.466 PDT:   File for submitting this DAG to HTCondor           : montage-0.dag.condor.sub 
    2016.06.02 21:46:32.471 PDT:   Log of DAGMan debugging messages                 : montage-0.dag.dagman.out 
    2016.06.02 21:46:32.476 PDT:   Log of HTCondor library output                     : montage-0.dag.lib.out 
    2016.06.02 21:46:32.481 PDT:   Log of HTCondor library error messages             : montage-0.dag.lib.err 
    2016.06.02 21:46:32.487 PDT:   Log of the life of condor_dagman itself          : montage-0.dag.dagman.log 
    2016.06.02 21:46:32.492 PDT:    
    2016.06.02 21:46:32.497 PDT:   -no_submit given, not submitting DAG to HTCondor.  You can do this with: 
    2016.06.02 21:46:32.507 PDT:   ----------------------------------------------------------------------- 
    2016.06.02 21:46:33.387 PDT:   Your database is compatible with Pegasus version: 4.6.1 
    2016.06.02 21:46:33.392 PDT:   
    
    I have concretized your abstract workflow. The workflow has been entered 
    into the workflow database with a state of "planned". The next step is 
    to start or execute your workflow. The invocation required is
    
    pegasus-run  /data/scratch/rynge/montage2/montage-workflow-v2/work/1464929190
    
    2016.06.02 21:46:33.419 PDT:   Time taken to execute is 2.961 seconds 


Running the workflow produces fits and jpeg mosaics for each band, as well as a combined color one:

![Pleiades](docs/images/pleiades.jpg?raw=true "Pleiades")


