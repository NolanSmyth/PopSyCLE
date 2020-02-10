#! /usr/bin/env python
"""
run.py
Executable to run the PopSyCLE pipeline.
"""

import os
from pathlib import Path
import argparse
from argparse import RawTextHelpFormatter
from popsycle import synthetic
import sys


def return_filename_dict(output_root):
    """
    Return the filenames of the files output by the pipeline

    Parameters
    ----------
    output_root : str
        Base filename of the output files
        Examples:
           '{output_root}.h5'
           '{output_root}.ebf'
           '{output_root}_events.h5'

    Output
    ------
    filename_dict : dict
        Dictionary containing the names of the files output by the pipeline

    """
    # Write out all of the filenames using the output_root
    ebf_filename = '%s.ebf' % output_root
    hdf5_filename = '%s.h5' % output_root
    events_filename = '%s_events.fits' % output_root
    blends_filename = '%s_blends.fits' % output_root
    noevents_filename = '%s_NOEVENTS.txt' % output_root

    # Add the filenames to a dictionary
    filename_dict = {
        'ebf_filename': ebf_filename,
        'hdf5_filename': hdf5_filename,
        'events_filename': events_filename,
        'blends_filename': blends_filename,
        'noevents_filename': noevents_filename
    }

    return filename_dict


def run():
    description_str = """
    Run the PopSyCLE pipeline. This executable can be either 
    run by slurm scripts generated by `generate_slurm_scripts` or from the 
    command line.

    Script must be executed in a folder containing a field_config file and 
    point to a popsycle_config file both generated by 
    `popsycle.slurm.generate_config_file`.
    """

    parser = argparse.ArgumentParser(description=description_str,
                                     formatter_class=RawTextHelpFormatter)
    required = parser.add_argument_group(title='Required')
    required.add_argument('--output-root', type=str,
                          help='Base filename of the output files. '
                               'Default: root0',
                          default='root0')
    required.add_argument('--field-config-filename', type=str,
                          help='Name of configuration file containing '
                               'the field parameters. '
                               'Default: field_config.yaml',
                          default='field_config.yaml')
    required.add_argument('--popsycle-config-filename', type=str,
                          help='Name of configuration file containing '
                               'the PopSyCLE parameters. '
                               'Default: popsycle_config.yaml',
                          default='popsycle_config.yaml')
    required.add_argument('--n-cores-calc-events', type=int,
                          help='Number of cores to use in the calc_events '
                               'function (the only piece of the '
                               'PopSyCLE pipeline that uses multiprocessing). '
                               'Default is --n-cores=1 or serial processing.',
                          default=1)

    optional = parser.add_argument_group(title='Optional')
    optional.add_argument('--seed', type=int,
                          help='Set a seed for all PopSyCLE functions with '
                               'randomness, including running Galaxia and '
                               'PyPopStar. Setting this flag guarantees '
                               'identical output and is useful for debugging.',
                          default=None)
    optional.add_argument('--overwrite',
                          help="Overwrite all output files.",
                          action='store_true')
    optional.add_argument('--skip-galaxia',
                          help="Skip running galaxia.",
                          action='store_true')
    optional.add_argument('--skip-perform-pop-syn',
                          help="Skip running perform_pop_syn.",
                          action='store_true')
    optional.add_argument('--skip-calc-events',
                          help="Skip running calc_events.",
                          action='store_true')
    optional.add_argument('--skip-refine-events',
                          help="Skip running refine_events.",
                          action='store_true')
    args = parser.parse_args()

    # Check for field config file. Exit if not present.
    if not os.path.exists(args.field_config_filename):
        print("""Error: Field configuration file {0} missing, 
        cannot continue. In order to execute run.py, generate a 
        field configuration file using 
        popsycle.synthetic.generate_field_config_file. 
        Exiting...""".format(args.field_config_filename))
        sys.exit(1)

    # Check for popsycle config file. Exit if not present.
    if not os.path.exists(args.popsycle_config_filename):
        print("""Error: popsycle configuration file {0} missing, 
        cannot continue. In order to execute run.py, generate a 
        popsycle configuration file using 
        popsycle.synthetic.generate_popsycle_config_file. 
        Exiting...""".format(args.popsycle_config_filename))
        sys.exit(1)

    # Load the config files for field parameters
    field_config = synthetic.load_config(args.field_config_filename)

    # Load the config files for popsycle parameters. If the `bin_edges_number`
    # has been set to the string `None`, instead set it to the boolean None.
    popsycle_config = synthetic.load_config(args.popsycle_config_filename)
    if popsycle_config['bin_edges_number'] == 'None':
        popsycle_config['bin_edges_number'] = None

    # Create an isochrones mirror in the current directory
    isochrones_dir = './isochrones'
    if not os.path.exists(isochrones_dir):
        os.symlink(popsycle_config['isochrones_dir'], isochrones_dir)

    # Return the dictionary containing PopSyCLE output filenames
    filename_dict = return_filename_dict(args.output_root)

    if not args.skip_galaxia:
        # Remove Galaxia output if already exists and overwrite=True
        if synthetic.check_for_output(filename_dict['ebf_filename'],
                                      args.overwrite):
            sys.exit(1)

        # Write out parameters for Galaxia run to disk
        print('-- Generating galaxia params')
        synthetic.write_galaxia_params(
            output_root=args.output_root,
            longitude=field_config['longitude'],
            latitude=field_config['latitude'],
            area=field_config['area'],
            seed=args.seed)

        # Run Galaxia from that parameter file
        cmd = 'galaxia -r galaxia_params.%s.txt' % args.output_root
        print('** Executing galaxia with {0} **'.format(cmd))
        _ = synthetic.execute(cmd)

    if not args.skip_perform_pop_syn:
        # Remove perform_pop_syn output if already exists and overwrite=True
        if synthetic.check_for_output(filename_dict['hdf5_filename'],
                                      args.overwrite):
            sys.exit(1)

        # Run perform_pop_syn
        print('-- Executing perform_pop_syn')
        synthetic.perform_pop_syn(
            ebf_file=filename_dict['ebf_filename'],
            output_root=args.output_root,
            iso_dir=popsycle_config['isochrones_dir'],
            bin_edges_number=popsycle_config['bin_edges_number'],
            BH_kick_speed_mean=popsycle_config['BH_kick_speed_mean'],
            NS_kick_speed_mean=popsycle_config['NS_kick_speed_mean'],
            additional_photometric_systems=[popsycle_config['photometric_system']],
            overwrite=args.overwrite,
            seed=args.seed)

    if not args.skip_calc_events:
        # Remove calc_events output if already exists and overwrite=True
        if synthetic.check_for_output(filename_dict['events_filename'],
                                      args.overwrite):
            sys.exit(1)
        if synthetic.check_for_output(filename_dict['blends_filename'],
                                      args.overwrite):
            sys.exit(1)

        # Run calc_events
        print('-- Executing calc_events')

        synthetic.calc_events(hdf5_file=filename_dict['hdf5_filename'],
                              output_root2=args.output_root,
                              radius_cut=popsycle_config['radius_cut'],
                              obs_time=popsycle_config['obs_time'],
                              n_obs=popsycle_config['n_obs'],
                              theta_frac=popsycle_config['theta_frac'],
                              blend_rad=popsycle_config['blend_rad'],
                              n_proc=args.n_cores_calc_events,
                              seed=args.seed,
                              overwrite=args.overwrite)

        # Write a fle to disk stating that there are no events if
        # calc_events does not produce an events file
        if not os.path.exists(filename_dict['events_filename']):
            Path(filename_dict['noevents_filename']).touch()
            print('No events present, skipping refine_events')
            sys.exit(0)

    if not args.skip_refine_events:
        # Remove refine_events output if already exists and overwrite=True
        filename = '{0:s}_refined_events_{1:s}_{2:s}.' \
                   'fits'.format(args.output_root,
                                 popsycle_config['filter_name'],
                                 popsycle_config['red_law'])
        if synthetic.check_for_output(filename, args.overwrite):
            sys.exit(1)

        # Run refine_events
        print('-- Executing refine_events')
        synthetic.refine_events(input_root=args.output_root,
                                filter_name=popsycle_config['filter_name'],
                                red_law=popsycle_config['red_law'],
                                overwrite=args.overwrite,
                                output_file='default',
                                photometric_system=popsycle_config['photometric_system'])

    # Remove Galaxia output if already exists and overwrite=True
    if synthetic.check_for_output(filename_dict['ebf_filename'],
                                  args.overwrite):
        sys.exit(1)

    # Write out parameters for Galaxia run to disk
    print('-- Generating galaxia params')
    synthetic.write_galaxia_params(
        output_root=args.output_root,
        longitude=field_config['longitude'],
        latitude=field_config['latitude'],
        area=field_config['area'],
        seed=args.seed)

    # Run Galaxia from that parameter file
    cmd = 'galaxia -r galaxia_params.%s.txt' % args.output_root
    print('** Executing galaxia with {0} **'.format(cmd))
    _ = synthetic.execute(cmd)

    # Remove perform_pop_syn output if already exists and overwrite=True
    if synthetic.check_for_output(filename_dict['hdf5_filename'],
                                  args.overwrite):
        sys.exit(1)

    # Run perform_pop_syn
    print('-- Executing perform_pop_syn')
    synthetic.perform_pop_syn(
        ebf_file=filename_dict['ebf_filename'],
        output_root=args.output_root,
        iso_dir=popsycle_config['isochrones_dir'],
        bin_edges_number=popsycle_config['bin_edges_number'],
        BH_kick_speed_mean=popsycle_config['BH_kick_speed_mean'],
        NS_kick_speed_mean=popsycle_config['NS_kick_speed_mean'],
        seed=args.seed,
        overwrite=args.overwrite)

    # Remove calc_events output if already exists and overwrite=True
    if synthetic.check_for_output(filename_dict['events_filename'],
                                  args.overwrite):
        sys.exit(1)
    if synthetic.check_for_output(filename_dict['blends_filename'],
                                  args.overwrite):
        sys.exit(1)

    # Run calc_events
    print('-- Executing calc_events')

    synthetic.calc_events(hdf5_file=filename_dict['hdf5_filename'],
                          output_root2=args.output_root,
                          radius_cut=popsycle_config['radius_cut'],
                          obs_time=popsycle_config['obs_time'],
                          n_obs=popsycle_config['n_obs'],
                          theta_frac=popsycle_config['theta_frac'],
                          blend_rad=popsycle_config['blend_rad'],
                          n_proc=args.n_cores_calc_events,
                          seed=args.seed,
                          overwrite=args.overwrite)

    # Write a fle to disk stating that there are no events if
    # calc_events does not produce an events file
    if not os.path.exists(filename_dict['events_filename']):
        Path(filename_dict['noevents_filename']).touch()
        print('No events present, skipping refine_events')
        sys.exit(0)

    # Remove refine_events output if already exists and overwrite=True
    filename = '{0:s}_refined_events_{1:s}_{2:s}.' \
               'fits'.format(args.output_root,
                             popsycle_config['filter_name'],
                             popsycle_config['red_law'])
    if synthetic.check_for_output(filename, args.overwrite):
        sys.exit(1)

    # Run refine_events
    print('-- Executing refine_events')
    synthetic.refine_events(input_root=args.output_root,
                            filter_name=popsycle_config['filter_name'],
                            red_law=popsycle_config['red_law'],
                            overwrite=args.overwrite,
                            output_file='default')


if __name__ == '__main__':
    run()
