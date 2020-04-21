#!/usr/bin/env python3

'''
Pegasus wf generator for the Montage toolkit. The generated
workflow will support multiple bands and colors to produce
a color image.

#  Copyright 2020 University Of Southern California
#
#  Licensed under the Apache License, Version 2.0 (the 'License');
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an 'AS IS' BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

'''

import os
import argparse
import re
import subprocess
import sys

#Insert this directory in our search path
os.sys.path.insert(0, os.getcwd())

from astropy.io import ascii
from Pegasus.api import *

common_files = {}


def which(file):
    for path in os.environ['PATH'].split(os.pathsep):
        if os.path.exists(os.path.join(path, file)):
            return os.path.join(path, file)
    return None


def build_transformation_catalog(tc_target, wf):
    '''
    Some transformations in Montage uses multiple executables
    '''

    tc = TransformationCatalog()
    trans = {}

    exes = {}
    full_path = which('mProject')
    if full_path is None:
        raise RuntimeError('mProject is not in the $PATH')
    base_dir = os.path.dirname(full_path)
   
    container = None
    if tc_target == 'container':
        container = Container('montage',
            Container.SINGULARITY,
            'shub://pegasus-isi/montage-workflow-v2'
            ).add_env(MONTAGE_HOME='/opt/Montage')
        wf.add_containers(container)

    for fname in os.listdir(base_dir):
        transformation = None
        if fname[0] == '.':
            continue

        if tc_target == 'regular':
            transformation = Transformation(fname, 
                                            site='condor-pool', 
                                            pfn=os.path.join(base_dir, fname), 
                                            is_stageable=True)
        else:
            # container
            transformation = Transformation(fname,
                                            site='condor-pool',
                                            pfn=os.path.join(base_dir, fname),
                                            container=container,
                                            is_stageable=False)

        # some transformations can be clustered for effiency
        if fname in ['gmProject', 'mDiff', 'mDiffFit', 'mBackground']:
            transformation.add_profiles(Namespace.PEGASUS, 'clusters.size', '3')

        # keep a handle to added ones, for use later
        trans[fname] = transformation
            
        tc.add_transformations(transformation)

    # some Montage tools depend on other tools
    trans['mDiffFit'].add_requirement(trans['mDiff'])
    trans['mDiffFit'].add_requirement(trans['mFitplane'])

    wf.add_transformation_catalog(tc)


def generate_region_hdr(wf, rc, center, degrees):

    global common_files

    (crval1, crval2) = center.split()
    crval1 = float(crval1)
    crval2 = float(crval2)

    cdelt = 0.000277778
    naxis = int((float(degrees) / cdelt) + 0.5)
    crpix = (naxis + 1) / 2.0

    f = open('data/region.hdr', 'w')
    f.write('SIMPLE  = T\n')
    f.write('BITPIX  = -64\n')
    f.write('NAXIS   = 2\n')
    f.write('NAXIS1  = %d\n' %(naxis))
    f.write('NAXIS2  = %d\n' %(naxis))
    f.write('CTYPE1  = \'RA---TAN\'\n')
    f.write('CTYPE2  = \'DEC--TAN\'\n')
    f.write('CRVAL1  = %.6f\n' %(crval1))
    f.write('CRVAL2  = %.6f\n' %(crval2))
    f.write('CRPIX1  = %.6f\n' %(crpix))
    f.write('CRPIX2  = %.6f\n' %(crpix))
    f.write('CDELT1  = %.9f\n' %(-cdelt))
    f.write('CDELT2  = %.9f\n' %(cdelt))
    f.write('CROTA2  = %.6f\n' %(0.0))
    f.write('EQUINOX = %d\n' %(2000))
    f.write('END\n')
    f.close()

    common_files['region.hdr'] = File('region.hdr')
    rc.add_replica('local', common_files['region.hdr'], 'file://' + os.getcwd() + '/data/region.hdr')

    # we also need an oversized region which will be used in the first part of the 
    # workflow to get the background correction correct
    f = open('data/region-oversized.hdr', 'w')
    f.write('SIMPLE  = T\n')
    f.write('BITPIX  = -64\n')
    f.write('NAXIS   = 2\n')
    f.write('NAXIS1  = %d\n' %(naxis + 3000))
    f.write('NAXIS2  = %d\n' %(naxis + 3000))
    f.write('CTYPE1  = \'RA---TAN\'\n')
    f.write('CTYPE2  = \'DEC--TAN\'\n')
    f.write('CRVAL1  = %.6f\n' %(crval1))
    f.write('CRVAL2  = %.6f\n' %(crval2))
    f.write('CRPIX1  = %.6f\n' %(crpix + 1500))
    f.write('CRPIX2  = %.6f\n' %(crpix + 1500))
    f.write('CDELT1  = %.9f\n' %(-cdelt))
    f.write('CDELT2  = %.9f\n' %(cdelt))
    f.write('CROTA2  = %.6f\n' %(0.0))
    f.write('EQUINOX = %d\n' %(2000))
    f.write('END\n')
    f.close()

    common_files['region-oversized.hdr'] = File('region-oversized.hdr')
    rc.add_replica('local', common_files['region-oversized.hdr'], 'file://' + os.getcwd() + '/data/region-oversized.hdr')


def add_band(wf, rc, band_id, center, degrees, survey, band, color):

    band_id = str(band_id)

    print('\nAdding band %s (%s %s -> %s)' %(band_id, survey, band, color))

    # data find - go a little bit outside the box - see mExec implentation
    degrees_datafind = str(float(degrees) * 1.42)
    cmd = 'mArchiveList %s %s \'%s\' %s %s data/%s-images.tbl' \
          %(survey, band, center, degrees_datafind, degrees_datafind, band_id)
    print('Running sub command: ' + cmd)
    if subprocess.call(cmd, shell=True) != 0:
        print('Command failed!')
        sys.exit(1)
    rc.add_replica('local', '%s-images.tbl' %(band_id), 'file://' + os.getcwd() + '/data/%s-images.tbl' %(band_id))

    # image tables
    raw_tbl = File('%s-raw.tbl' %(band_id))
    rc.add_replica('local', raw_tbl, 'file://' + os.getcwd() + '/data/' + raw_tbl.lfn)
    projected_tbl = File('%s-projected.tbl' %(band_id))
    rc.add_replica('local', projected_tbl, 'file://' + os.getcwd() + '/data/' + projected_tbl.lfn)
    corrected_tbl = File('%s-corrected.tbl' %(band_id))
    rc.add_replica('local', corrected_tbl, 'file://' + os.getcwd() + '/data/' + corrected_tbl.lfn)
    cmd = 'cd data && mDAGTbls %s-images.tbl region-oversized.hdr %s %s %s' \
          %(band_id, raw_tbl.lfn, projected_tbl.lfn, corrected_tbl.lfn)
    print('Running sub command: ' + cmd)
    if subprocess.call(cmd, shell=True) != 0:
        print('Command failed!')
        sys.exit(1)
    
    # diff table
    cmd = 'cd data && mOverlaps %s-raw.tbl %s-diffs.tbl' \
          %(band_id, band_id)
    print('Running sub command: ' + cmd)
    if subprocess.call(cmd, shell=True) != 0:
        print('Command failed!')
        sys.exit(1)

    # statfile table
    t = ascii.read('data/%s-diffs.tbl' %(band_id))
    # make sure we have a wide enough column
    t['stat'] = '                                                                  '
    for row in t:
        base_name = re.sub('(diff\.|\.fits.*)', '', row['diff'])
        row['stat'] = '%s-fit.%s.txt' %(band_id, base_name)
    ascii.write(t, 'data/%s-stat.tbl' %(band_id), format='ipac')
    rc.add_replica('local', '%s-stat.tbl' %(band_id), 'file://' + os.getcwd() + '/data/%s-stat.tbl' %(band_id))

    # for all the input images in this band, and them to the rc, and
    # add reproject tasks
    data = ascii.read('data/%s-images.tbl' %(band_id))  
    for row in data:
        
        base_name = re.sub('\.fits.*', '', row['file'])

        # add an entry to the replica catalog
        rc.add_replica('ipac', base_name + '.fits', row['URL'])

        # projection job
        j = Job('mProject')
        in_fits = File(base_name + '.fits')
        projected_fits = File('p' + base_name + '.fits')
        area_fits = File('p' + base_name + '_area.fits')
        j.add_inputs(common_files['region-oversized.hdr'], in_fits)
        j.add_outputs(projected_fits, area_fits, stage_out=False)
        j.add_args('-X', in_fits, projected_fits, common_files['region-oversized.hdr'])
        wf.add_jobs(j)

    fit_txts = []
    data = ascii.read('data/%s-diffs.tbl' %(band_id))
    for row in data:
        
        base_name = re.sub('(diff\.|\.fits.*)', '', row['diff'])

        # mDiffFit job
        j = Job('mDiffFit')
        plus = File('p' + row['plus'])
        plus_area = File(re.sub('\.fits', '_area.fits', plus.lfn))
        minus = File('p' + row['minus'])
        minus_area = File(re.sub('\.fits', '_area.fits', minus.lfn))
        fit_txt = File('%s-fit.%s.txt' %(band_id, base_name))
        diff_fits = File('%s-diff.%s.fits' %(band_id, base_name))
        j.add_inputs(plus, plus_area, minus, minus_area, common_files['region-oversized.hdr'])
        j.add_outputs(fit_txt, stage_out=False)
        j.add_args('-d', '-s', fit_txt, plus, minus, diff_fits, common_files['region-oversized.hdr'])
        wf.add_jobs(j)
        fit_txts.append(fit_txt)

    # mConcatFit
    j = Job('mConcatFit')
    stat_tbl = File('%s-stat.tbl' %(band_id))
    j.add_inputs(stat_tbl)
    for fit_txt in fit_txts:
        j.add_inputs(fit_txt)
    fits_tbl = File('%s-fits.tbl' %(band_id))
    j.add_outputs(fits_tbl, stage_out=False)
    j.add_args(stat_tbl, fits_tbl, '.')
    wf.add_jobs(j)

    # mBgModel
    j = Job('mBgModel')
    images_tbl = File('%s-images.tbl' %(band_id))
    corrections_tbl = File('%s-corrections.tbl' %(band_id))
    j.add_inputs(images_tbl, fits_tbl)
    j.add_outputs(corrections_tbl, stage_out=False)
    j.add_args('-i', '100000', images_tbl, fits_tbl, corrections_tbl)
    wf.add_jobs(j)

    # mBackground
    data = ascii.read('data/%s-raw.tbl' %(band_id))  
    for row in data:
        base_name = re.sub('(diff\.|\.fits.*)', '', row['file'])

        # mBackground job
        j = Job('mBackground')
        projected_fits = File('p' + base_name + '.fits')
        projected_area = File('p' + base_name + '_area.fits')
        corrected_fits = File('c' + base_name + '.fits')
        corrected_area = File('c' + base_name + '_area.fits')
        j.add_inputs(projected_fits, projected_area, projected_tbl, corrections_tbl)
        j.add_outputs(corrected_fits, corrected_area, stage_out=False)
        j.add_args('-t', projected_fits, corrected_fits, projected_tbl, corrections_tbl)
        wf.add_jobs(j)

    # mImgtbl - we need an updated corrected images table because the pixel offsets and sizes need
    # to be exactly right and the original is only an approximation
    j = Job('mImgtbl')
    updated_corrected_tbl = File('%s-updated-corrected.tbl' %(band_id))
    j.add_inputs(corrected_tbl)
    j.add_outputs(updated_corrected_tbl, stage_out=False)
    j.add_args('.', '-t', corrected_tbl, updated_corrected_tbl)
    data = ascii.read('data/%s-corrected.tbl' %(band_id))  
    for row in data:
        base_name = re.sub('(diff\.|\.fits.*)', '', row['file'])
        projected_fits = File(base_name + '.fits')
        j.add_inputs(projected_fits)
    wf.add_jobs(j)

    # mAdd
    j = Job('mAdd')
    mosaic_fits = File('%s-mosaic.fits' %(band_id))
    mosaic_area = File('%s-mosaic_area.fits' %(band_id))
    j.add_inputs(updated_corrected_tbl, common_files['region.hdr'])
    j.add_outputs(mosaic_fits, mosaic_area, stage_out=True)
    j.add_args('-e', updated_corrected_tbl, common_files['region.hdr'], mosaic_fits)
    data = ascii.read('data/%s-corrected.tbl' %(band_id))  
    for row in data:
        base_name = re.sub('(diff\.|\.fits.*)', '', row['file'])
        corrected_fits = File(base_name + '.fits')
        corrected_area = File(base_name + '_area.fits')
        j.add_inputs(corrected_fits, corrected_area)
    wf.add_jobs(j)

    # mJPEG - Make the JPEG for this channel
    j = Job('mJPEG')
    mosaic_jpg = File('%s-mosaic.jpg' %(band_id))
    j.add_inputs(mosaic_fits)
    j.add_outputs(mosaic_jpg, stage_out=True)
    j.add_args('-ct', '0', '-gray', mosaic_fits, '0s', '99.999%', 'gaussian', \
               '-out', mosaic_jpg)
    wf.add_jobs(j)


def color_jpg(wf, rc, red_id, green_id, blue_id):

    red_id = str(red_id)
    green_id = str(green_id)
    blue_id = str(blue_id)

    # mJPEG - Make the JPEG for this channel
    j = Job('mJPEG')
    mosaic_jpg = File('mosaic-color.jpg')
    red_fits = File('%s-mosaic.fits' %(red_id))
    green_fits = File('%s-mosaic.fits' %(green_id))
    blue_fits = File('%s-mosaic.fits' %(blue_id))
    j.add_inputs(red_fits, green_fits, blue_fits)
    j.add_outputs(mosaic_jpg, stage_out=True)
    j.add_args( \
            '-red', red_fits, '-1s', '99.999%', 'gaussian-log', \
            '-green', green_fits, '-1s', '99.999%', 'gaussian-log', \
            '-blue', blue_fits, '-1s', '99.999%', 'gaussian-log', \
            '-out', mosaic_jpg)
    wf.add_jobs(j)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('--work-dir', action = 'store', dest = 'work_dir',
                        help = 'Work directory to chdir to')
    parser.add_argument('--center', action = 'store', dest = 'center',
                        help = 'Center of the output, for example M17 or 56.5 23.75')
    parser.add_argument('--degrees', action = 'store', dest = 'degrees',
                        help = 'Number of degrees of side of the output')
    parser.add_argument('--band', action = 'append', dest = 'bands',
                        help = 'Band definition. Example: dss:DSS2B:red')
    parser.add_argument('--tc-target', action = 'store', dest = 'tc_target',
                        help = 'Transformation catalog: regular or container')
    args = parser.parse_args()

    if args.work_dir:
        os.chdir(args.work_dir)

    if args.tc_target is None:
        args.tc_target = 'regular'

    if os.path.exists('data'):
        print('data/ directory already exists')
        sys.exit(1)
    os.mkdir('data')

    wf = Workflow('montage', infer_dependencies=True)
    rc = ReplicaCatalog()

    # FIXME
    # email notificiations for when the state of the workflow changes
    #share_dir = subprocess.Popen('pegasus-config --sh-dump | grep ^PEGASUS_SHARE_DIR= | sed -e 's/.*=//' -e 's/\'//g'',
    #                             shell=True,
    #                             stdout=subprocess.PIPE).communicate()[0]
    #share_dir = share_dir.strip()
    #wf.invoke('start', share_dir + '/notification/email')
    #wf.invoke('on_error', share_dir + '/notification/email')
    #wf.invoke('on_success', share_dir + '/notification/email --report=pegasus-statistics')

    build_transformation_catalog(args.tc_target, wf)

    # region.hdr is the template for the ouput area
    generate_region_hdr(wf, rc, args.center, args.degrees)

    band_id = 0
    color_band = {}
    for band_def in args.bands:
        band_id += 1
        (survey, band, color) = band_def.split(':')
        add_band(wf, rc, band_id, args.center, args.degrees, survey, band, color)
        color_band[color] = band_id

    # if we have 3 bands in red, blue, green, try to create a color jpeg
    if 'red' in color_band and 'green' in color_band and 'blue' in color_band:
        color_jpg(wf, rc, color_band['red'], color_band['green'], color_band['blue'])

    # write out the workflow and catalogs
    wf.add_replica_catalog(rc)
    wf.write('data/montage-workflow.yml')


if __name__ == '__main__':
    main()


