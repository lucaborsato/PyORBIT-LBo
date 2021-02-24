from __future__ import print_function
#from pyorbit.classes.common import *
from pyorbit.classes.model_container_ultranest import ModelContainerUltranest
from pyorbit.classes.input_parser import yaml_parser, pars_input
from pyorbit.classes.io_subroutines import nested_sampling_save_to_cpickle, \
    nested_sampling_load_from_cpickle, nested_sampling_create_dummy_file, \
    ultranest_sampler_save_to_cpickle

import pyorbit.classes.results_analysis as results_analysis
import os
import sys
import re
import argparse
import numpy as np
import multiprocessing
import matplotlib.pyplot as plt

__all__ = ["pyorbit_ultranest", "yaml_parser"]

"""
def show(filepath):
    # open the output (pdf) file for the user
    if os.name == 'mac': subprocess.call(('open', filepath))
    elif os.name == 'nt': os.startfile(filepath)
"""


def pyorbit_ultranest(config_in, input_datasets=None, return_output=None):

    mc = ModelContainerUltranest()
    pars_input(config_in, mc, input_datasets)

    if mc.nested_sampling_parameters['shutdown_jitter']:
        'Jitter term not included for evidence calculation'
        print()
        for dataset_name, dataset in mc.dataset_dict.items():
            dataset.shutdown_jitter()

    mc.model_setup()
    mc.create_variables_bounds()
    mc.initialize_logchi2()

    mc.create_starting_point()

    results_analysis.results_resumen(mc, None, skip_theta=True)

    theta_dictionary = results_analysis.get_theta_dictionary(mc)
    labels_array = [None] * len(theta_dictionary)
    for key_name, key_value in theta_dictionary.items():
        labels_array[key_value] = re.sub('_', '-', key_name)

    mc.output_directory = './' + config_in['output'] + '/ultranest/'
    if not os.path.exists(mc.output_directory):
        os.makedirs(mc.output_directory)

    if 'nlive_mult' in mc.nested_sampling_parameters:
        nlive = mc.ndim * mc.nested_sampling_parameters['nlive_mult']
    else:
        nlive = mc.nested_sampling_parameters['nlive']

    print('Number of minimum live points:', nlive)
    print('Desired accuracy:', mc.nested_sampling_parameters['desired_accuracy'])
    print('Minimum number of effective samples:', mc.nested_sampling_parameters['min_ess'])

    print()
    print('Reference Time Tref: ', mc.Tref)
    print()
    print('*************************************************************')
    print()

    try:
        from ultranest import ReactiveNestedSampler
    except ImportError:
        print("ERROR: ultranest not installed, this will not work")
        quit()


    sampler = ReactiveNestedSampler(
        labels_array,
        mc.ultranest_call,
        transform=mc.ultranest_transform,
        log_dir=mc.output_directory, # folder where to store files
        resume=True, # whether to resume from there (otherwise start from scratch)
    )

    sampler.run(
        min_num_live_points=nlive,
        dlogz=mc.nested_sampling_parameters['desired_accuracy'], # desired accuracy on logz
        min_ess=mc.nested_sampling_parameters['min_ess'], # number of effective samples
        max_num_improvement_loops=mc.nested_sampling_parameters['improvement_loops'] # how many times to go back and improve
    )

    sampler.print_results()

    print()
    sampler.plot()
    sampler.plot_trace()
    sampler.plot_run()

    """ A dummy file is created to let the cpulimit script to proceed with the next step"""
    nested_sampling_create_dummy_file(mc)
    nested_sampling_save_to_cpickle(mc)
    # ultranest_sampler_save_to_cpickle(mc.output_directory, sampler)

    if return_output:
        return mc
    else:
        return
