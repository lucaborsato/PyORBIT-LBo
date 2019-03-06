from classes.model_container_multinest import ModelContainerMultiNest
from classes.model_container_polychord import ModelContainerPolyChord
from classes.model_container_emcee import ModelContainerEmcee

from classes.input_parser import yaml_parser, pars_input
from classes.io_subroutines import *
import numpy as np
import os
import matplotlib as mpl
from matplotlib.ticker import FormatStrFormatter
import sys
mpl.use('Agg')
from matplotlib import pyplot as plt
import corner
import classes.constants as constants
import classes.kepler_exo as kepler_exo
import classes.common as common
import classes.results_analysis as results_analysis
import h5py
import csv

__all__ = ["pyorbit_getresults"]


def pyorbit_getresults(config_in, sampler, plot_dictionary):

    try:
        use_tex = config_in['parameters']['use_tex']
    except:
        use_tex = True

    if plot_dictionary['use_getdist']:
        from getdist import plots, MCSamples

    #plt.rc('font', **{'family': 'serif', 'serif': ['Computer Modern Roman']})
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rc('text', usetex=use_tex)

    sample_keyword = {
        'multinest': ['multinest', 'MultiNest', 'multi'],
        'polychord':['polychord', 'PolyChord', 'polychrod', 'poly'],
        'emcee': ['emcee', 'MCMC', 'Emcee']
    }

    if sampler in sample_keyword['emcee']:

        dir_input = './' + config_in['output'] + '/emcee/'
        dir_output = './' + config_in['output'] + '/emcee_plot/'
        os.system('mkdir -p ' + dir_output)

        mc, starting_point, population, prob, state, \
        sampler_chain, sampler_lnprobability, sampler_acceptance_fraction = \
            emcee_load_from_cpickle(dir_input)

        pars_input(config_in, mc, reload_emcee=True)

        if hasattr(mc.emcee_parameters, 'version'):
            emcee_version = mc.emcee_parameters['version'][0]
        else:
            import emcee
            emcee_version = emcee.__version__[0]

        mc.model_setup()
        """ Required to create the right objects inside each class - if defined inside """
        theta_dictionary = results_analysis.get_theta_dictionary(mc)

        nburnin = mc.emcee_parameters['nburn']
        nthin = mc.emcee_parameters['thin']
        nsteps = sampler_chain.shape[1] * nthin

        flat_chain = emcee_flatchain(sampler_chain, nburnin, nthin)
        flat_lnprob = emcee_flatlnprob(sampler_lnprobability, nburnin, nthin, emcee_version)

        flat_BiC = -2*flat_lnprob + mc.ndim * np.log(mc.ndata)

        lnprob_med = common.compute_value_sigma(flat_lnprob)
        chain_med = common.compute_value_sigma(flat_chain)
        chain_MAP, lnprob_MAP = common.pick_MAP_parameters(flat_chain, flat_lnprob)

        print()
        print('Reference Time Tref: {}'.format(mc.Tref))
        print()
        print('Dimensions = {}'.format(mc.ndim))
        print('Nwalkers = {}'.format(mc.emcee_parameters['nwalkers']))
        print()
        print('Steps: {}'.format(nsteps))
        print()

    if sampler in sample_keyword['multinest']:

        plot_dictionary['lnprob_chain'] = False
        plot_dictionary['chains'] = False
        plot_dictionary['traces'] = False

        dir_input = './' + config_in['output'] + '/multinest/'
        dir_output = './' + config_in['output'] + '/multinest_plot/'
        os.system('mkdir -p ' + dir_output)

        mc = nested_sampling_load_from_cpickle(dir_input)

        print mc.bounds
        #pars_input(config_in, mc)

        mc.model_setup()
        mc.initialize_logchi2()
        results_analysis.results_resumen(mc, None, skip_theta=True)

        """ Required to create the right objects inside each class - if defined inside """
        theta_dictionary = results_analysis.get_theta_dictionary(mc)
        print
        print theta_dictionary

        data_in = np.genfromtxt(dir_input + 'post_equal_weights.dat')
        flat_lnprob = data_in[:, -1]
        flat_chain = data_in[:, :-1]
        nsample = np.size(flat_lnprob)

        lnprob_med = common.compute_value_sigma(flat_lnprob)
        chain_med = common.compute_value_sigma(flat_chain)
        chain_MAP, lnprob_MAP = common.pick_MAP_parameters(flat_chain, flat_lnprob)

        print
        print 'Reference Time Tref: ', mc.Tref
        print
        print 'Dimensions = ', mc.ndim
        print
        print 'Samples: ', nsample
        print

    if sampler in sample_keyword['polychord']:

        plot_dictionary['lnprob_chain'] = False
        plot_dictionary['chains'] = False
        plot_dictionary['traces'] = False

        dir_input = './' + config_in['output'] + '/polychord/'
        dir_output = './' + config_in['output'] + '/polychord_plot/'
        os.system('mkdir -p ' + dir_output)

        mc = nested_sampling_load_from_cpickle(dir_input)

        print mc.bounds
        #pars_input(config_in, mc)

        mc.model_setup()
        mc.initialize_logchi2()
        results_analysis.results_resumen(mc, None, skip_theta=True)

        """ Required to create the right objects inside each class - if defined inside """
        theta_dictionary = results_analysis.get_theta_dictionary(mc)
        print theta_dictionary

        data_in = np.genfromtxt(dir_input + 'pyorbit_equal_weights.txt')
        flat_lnprob = data_in[:, 1]
        flat_chain = data_in[:, 2:]
        nsample = np.size(flat_lnprob)


        lnprob_med = common.compute_value_sigma(flat_lnprob)
        chain_med = common.compute_value_sigma(flat_chain)
        chain_MAP, lnprob_MAP = common.pick_MAP_parameters(flat_chain, flat_lnprob)

        print
        print 'Reference Time Tref: ', mc.Tref
        print
        print 'Dimensions = ', mc.ndim
        print
        print 'Samples: ', nsample
        print

    print
    print ' LN posterior: %12f   %12f %12f (15-84 p) ' % (lnprob_med[0], lnprob_med[2], lnprob_med[1])

    MAP_log_priors, MAP_log_likelihood = mc.log_priors_likelihood(chain_MAP)
    BIC = -2.0 * MAP_log_likelihood + np.log(mc.ndata) * mc.ndim
    AIC = -2.0 * MAP_log_likelihood + 2.0 * mc.ndim
    AICc = AIC +  (2.0 + 2.0*mc.ndim) * mc.ndim / (mc.ndata - mc.ndim - 1.0)
    # AICc for small sample

    print
    print ' MAP log_priors     = ', MAP_log_priors
    print ' MAP log_likelihood = ', MAP_log_likelihood
    print ' MAP BIC  (using likelihood)  = ', BIC
    print ' MAP AIC  (using likelihood)  = ', AIC
    print ' MAP AICc (using likelihood) = ', AICc

    MAP_log_posterior = MAP_log_likelihood + MAP_log_priors
    BIC = -2.0 * MAP_log_posterior + np.log(mc.ndata) * mc.ndim
    AIC = -2.0 * MAP_log_posterior + 2.0 * mc.ndim
    AICc = AIC +  (2.0 + 2.0*mc.ndim) * mc.ndim / (mc.ndata - mc.ndim - 1.0)

    print
    print ' MAP BIC  (using posterior)  = ', BIC
    print ' MAP AIC  (using posterior)  = ', AIC
    print ' MAP AICc (using posterior) = ', AICc

    if mc.ndata < 40 * mc.ndim:
        print
        print ' AICc suggested over AIC because NDATA ( %12f ) < 40 * NDIM ( %12f )' % (mc.ndata, mc.ndim)
    else:
        print
        print ' AIC suggested over AICs because NDATA ( %12f ) > 40 * NDIM ( %12f )' % (mc.ndata, mc.ndim)

    print
    print '****************************************************************************************************'
    print
    print ' Print MEDIAN result '
    print

    results_analysis.results_resumen(mc, flat_chain, chain_med=chain_MAP)
    results_analysis.results_derived(mc, flat_chain)

    print
    print '****************************************************************************************************'
    print
    print ' Print MAP result (', lnprob_MAP, ')'
    print

    results_analysis.results_resumen(mc, chain_MAP)
    results_analysis.results_derived(mc, chain_MAP)

    print
    print '****************************************************************************************************'
    print

    if plot_dictionary['lnprob_chain'] or plot_dictionary['chains']:

        print ' Plot FLAT chain '
        print
        #results_analysis.results_resumen(mc, flat_chain)

        if emcee_version == '2':
            fig = plt.figure(figsize=(12, 12))
            plt.xlabel('$\ln \mathcal{L}$')
            plt.plot(sampler_lnprobability.T, '-', alpha=0.5)
            plt.axhline(lnprob_med[0])
            plt.axvline(nburnin/nthin, c='r')
            plt.savefig(dir_output + 'LNprob_chain.png', bbox_inches='tight', dpi=300)
            plt.close(fig)
        else:
            fig = plt.figure(figsize=(12, 12))
            plt.xlabel('$\ln \mathcal{L}$')
            plt.plot(sampler_lnprobability, '-', alpha=0.5)
            plt.axhline(lnprob_med[0])
            plt.axvline(nburnin/nthin, c='r')
            plt.savefig(dir_output + 'LNprob_chain.png', bbox_inches='tight', dpi=300)
            plt.close(fig)

        print
        print '****************************************************************************************************'
        print

    if plot_dictionary['full_correlation']:

        corner_plot = {
            'samples': np.zeros([np.size(flat_chain, axis=0), np.size(flat_chain, axis=1)]),
            'labels': [],
            'truths': []
        }
        import re

        for var, var_dict in theta_dictionary.iteritems():
            corner_plot['samples'][:, var_dict] = flat_chain[:, var_dict]
            corner_plot['labels'].append(re.sub('_', '-', var))
            corner_plot['truths'].append(chain_med[var_dict, 0])

        corner_plot['samples'][:, -1] = flat_lnprob[:]
        corner_plot['labels'].append('ln-prob')
        corner_plot['truths'].append(lnprob_med[0])

        if plot_dictionary['use_getdist']:
            print(' Plotting full_correlation plot with GetDist')
            print(' Ignore the no burnin error warning from getdist, since burnin has been already removed from the chains')

            plt.rc('text', usetex=False)
            samples = MCSamples(samples=corner_plot['samples'], names=corner_plot['labels'], labels=corner_plot['labels'])

            g = plots.getSubplotPlotter()
            g.settings.num_plot_contours = 6
            g.triangle_plot(samples, filled=True)
            g.export(dir_output + "all_internal_variables_corner_getdist.pdf")

        else:
            # plotting mega-corner plot
            print('Plotting full_correlation plot with Corner')
            plt.rc('text', usetex=False)

            fig = corner.corner(np.asarray(corner_plot['samples']).T,
                                labels=corner_plot['labels'], truths=corner_plot['truths'])
            fig.savefig(dir_output + "all_internal_variables_corner_test.pdf", bbox_inches='tight', dpi=300)
            plt.close(fig)
            plt.rc('text', usetex=use_tex)

        print
        print '****************************************************************************************************'
        print

    if plot_dictionary['chains']:
        print 'plotting the chains... '

        os.system('mkdir -p ' + dir_output + 'chains')
        for theta_name, ii in theta_dictionary.iteritems():
            file_name = dir_output + 'chains/' + repr(ii) + '_' + theta_name + '.png'
            fig = plt.figure(figsize=(12, 12))
            plt.plot(sampler_chain[:, :, ii].T, '-', alpha=0.5)
            plt.axvline(nburnin/nthin, c='r')
            plt.savefig(file_name, bbox_inches='tight', dpi=300)
            plt.close(fig)

        print
        print '****************************************************************************************************'
        print

    if plot_dictionary['traces']:
        print 'Plotting the Gelman-Rubin traces... '
        print
        """
        Gelman-Rubin traces are stored in the dedicated folder iniside the _plot folder
        Note that the GR statistics is not robust because the wlakers are not independent 
        """
        os.system('mkdir -p ' + dir_output + 'gr_traces')

        step_sampling = np.arange(nburnin/nthin, nsteps/nthin, 1)

        for theta_name, th in theta_dictionary.iteritems():
            rhat = np.array([GelmanRubin_v2(sampler_chain[:, :steps, th]) for steps in step_sampling])
            print ' Gelman-Rubin: %5i %12f %s ' % (th, rhat[-1], theta_name)
            file_name = dir_output + 'gr_traces/v2_' + repr(th) + '_' + theta_name + '.png'
            fig = plt.figure(figsize=(12, 12))
            plt.plot(step_sampling, rhat[:], '-', color='k')
            plt.axhline(1.01, c='C0')
            plt.savefig(file_name, bbox_inches='tight', dpi=300)
            plt.close(fig)

        print
        print '****************************************************************************************************'
        print

    if plot_dictionary['common_corner']:

        print(' Plotting the common models corner plots')

        plt.rc('text', usetex=False)
        for common_name, common_model in mc.common_models.iteritems():

            print('     Common model: ' + common_name)

            corner_plot = {
                'var_list': [],
                'samples': [],
                'labels': [],
                'truths': []
            }
            variable_values = common_model.convert(flat_chain)
            variable_median = common_model.convert(chain_med[:, 0])

            if len(variable_median) < 1.:
                continue

            n_samplings, n_pams = np.shape(flat_chain)

            """
            Check if the eccentricity and argument of pericenter were set as free parameters or fixed by simply
            checking the size of their distribution
            """
            for var in variable_values.keys():
                if np.size(variable_values[var]) == 1:
                        variable_values[var] = variable_values[var] * np.ones(n_samplings)
                else:
                    corner_plot['var_list'].append(var)

            corner_plot['samples'] = []
            corner_plot['labels'] = []
            corner_plot['truths'] = []
            for var_i, var in enumerate(corner_plot['var_list']):
                corner_plot['samples'].extend([variable_values[var]])
                corner_plot['labels'].append(var)
                corner_plot['truths'].append(variable_median[var])

            """ Check if the semi-amplitude K is among the parameters that have been fitted. 
                If so, it computes the correpsing planetary mass with uncertainty """


            fig = corner.corner(np.asarray(corner_plot['samples']).T, labels=corner_plot['labels'], truths=corner_plot['truths'])
            fig.savefig(dir_output + common_name + "_corners.pdf", bbox_inches='tight', dpi=300)
            plt.close(fig)

        print
        print '****************************************************************************************************'
        print

    if plot_dictionary['dataset_corner']:

        print '****************************************************************************************************'
        print
        print ' Dataset + models corner plots '
        print
        for dataset_name, dataset in mc.dataset_dict.iteritems():

            for model_name in dataset.models:

                variable_values = dataset.convert(flat_chain)
                variable_median = dataset.convert(chain_med[:, 0])

                for common_ref in mc.models[model_name].common_ref:
                    variable_values.update(mc.common_models[common_ref].convert(flat_chain))
                    variable_median.update(mc.common_models[common_ref].convert(chain_med[:, 0]))

                variable_values.update(mc.models[model_name].convert(flat_chain, dataset_name))
                variable_median.update(mc.models[model_name].convert(chain_med[:, 0], dataset_name))

                corner_plot['samples'] = []
                corner_plot['labels'] = []
                corner_plot['truths'] = []
                for var_i, var in enumerate(variable_values):
                    if np.size(variable_values[var]) <= 1: continue
                    corner_plot['samples'].extend([variable_values[var]])
                    corner_plot['labels'].append(var)
                    corner_plot['truths'].append(variable_median[var])

                fig = corner.corner(np.asarray(corner_plot['samples']).T,
                                    labels=corner_plot['labels'], truths=corner_plot['truths'])
                fig.savefig(dir_output + dataset_name + '_' + model_name + "_corners.pdf", bbox_inches='tight', dpi=300)
                plt.close(fig)

                print 'Dataset: ', dataset_name , '    model: ', model_name, ' corner plot  done '

    print
    print '****************************************************************************************************'
    print

    if plot_dictionary['plot_models'] or plot_dictionary['write_models']:

        print ' Writing all the files '

        bjd_plot = {
            'full': {
                'start': None, 'end': None, 'range': None
            }
        }

        # Computation of all the planetary variables
        planet_variables = get_planet_variables(mc, chain_med[:, 0])
        planet_variables_MAP = get_planet_variables(mc, chain_MAP)

        #     """ in this variable we store the physical variables of """
        #     planet_variables = {}
        #     planet_variables_MAP = {}
        #
        #     chain_med[:, 0]
        #     variable_MAP = common_model.convert(chain_MAP)


        kinds = {}
        for dataset_name, dataset in mc.dataset_dict.iteritems():
            if dataset.kind in kinds.keys():
                kinds[dataset.kind].extend([dataset_name])
            else:
                kinds[dataset.kind] = [dataset_name]

            bjd_plot[dataset_name] = {
                'start': np.amin(dataset.x0),
                'end': np.amax(dataset.x0),
                'range': np.amax(dataset.x0)-np.amin(dataset.x0),
            }

            if bjd_plot[dataset_name]['range'] < 0.1 : bjd_plot[dataset_name]['range'] = 0.1

            bjd_plot[dataset_name]['start'] -= bjd_plot[dataset_name]['range'] * 0.10
            bjd_plot[dataset_name]['end'] += bjd_plot[dataset_name]['range'] * 0.10

            if dataset.kind == 'Phot':
                step_size = np.min(bjd_plot[dataset_name]['range']/dataset.n/20.)
            else:
                step_size = 0.10

            bjd_plot[dataset_name]['x0_plot'] = \
                np.arange(bjd_plot[dataset_name]['start'], bjd_plot[dataset_name]['end'], step_size)

            if bjd_plot['full']['range']:
                bjd_plot['full']['start'] = min(bjd_plot['full']['start'], np.amin(dataset.x0))
                bjd_plot['full']['end'] = max(bjd_plot['full']['end'], np.amax(dataset.x0))
                bjd_plot['full']['range'] = bjd_plot['full']['end']-bjd_plot['full']['start']
            else:
                bjd_plot['full']['start'] = np.amin(dataset.x0)
                bjd_plot['full']['end'] = np.amax(dataset.x0)
                bjd_plot['full']['range'] = bjd_plot['full']['end']-bjd_plot['full']['start']

        bjd_plot['full']['start'] -= bjd_plot['full']['range']*0.10
        bjd_plot['full']['end'] += bjd_plot['full']['range']*0.10
        bjd_plot['full']['x0_plot'] = np.arange(bjd_plot['full']['start'], bjd_plot['full']['end'],0.1)

        for dataset_name, dataset in mc.dataset_dict.iteritems():
            if dataset.kind =='RV':
                bjd_plot[dataset_name] = bjd_plot['full']

        bjd_plot['model_out'], bjd_plot['model_x0'] = results_analysis.get_model(mc, chain_med[:, 0], bjd_plot)
        bjd_plot['MAP_model_out'], bjd_plot['MAP_model_x0'] = results_analysis.get_model(mc, chain_MAP, bjd_plot)

        if plot_dictionary['plot_models']:

            for kind_name, kind in kinds.iteritems():
                for dataset_name in kind:
                    fig = plt.figure(figsize=(12, 12))
                    plt.errorbar(mc.dataset_dict[dataset_name].x0,
                                 mc.dataset_dict[dataset_name].y - bjd_plot['model_out'][dataset_name]['systematics'],
                                 yerr=mc.dataset_dict[dataset_name]. e,
                                 fmt='o', zorder=2)
                    plt.plot(bjd_plot[dataset_name]['x0_plot'], bjd_plot['model_x0'][dataset_name]['complete'], zorder=2, c='b')
                    plt.plot(bjd_plot[dataset_name]['x0_plot'], bjd_plot['MAP_model_x0'][dataset_name]['complete'], zorder=1, c='r')

                    plt.savefig(dir_output + 'model_' + kind_name + '_' + dataset_name + '.png', bbox_inches='tight', dpi=300)
                    plt.close(fig)
            print

        if plot_dictionary['write_models']:
            for prepend_keyword in ['', 'MAP_']:
                plot_out_keyword = prepend_keyword + 'model_out'
                plot_x0_keyword = prepend_keyword + 'model_x0'
                file_keyword = prepend_keyword + 'model_files'

                if prepend_keyword == '':
                    planet_vars = planet_variables
                elif prepend_keyword == 'MAP_':
                    planet_vars = planet_variables_MAP

                dir_models = dir_output + file_keyword + '/'
                os.system('mkdir -p ' + dir_models)

                for dataset_name, dataset in mc.dataset_dict.items():
                    for model_name in dataset.models:

                        if getattr(mc.models[model_name], 'systematic_model', False):
                            continue

                        fileout = open(dir_models + dataset_name + '_' + model_name + '.dat', 'w')
                        phase = dataset.x0 * 0.00
                        for common_ref in mc.models[model_name].common_ref:
                            if common_ref in planet_vars:
                                phase = (dataset.x0 / planet_vars[common_ref]['P']) % 1
                                continue

                        fileout.write('descriptor BJD BJD0 pha val,+- sys mod full val_compare,+- res,+- \n')

                        try:
                            len(bjd_plot[plot_out_keyword][dataset_name][model_name])
                        except:
                            bjd_plot[plot_out_keyword][dataset_name][model_name] = \
                                bjd_plot[plot_out_keyword][dataset_name][model_name] * np.ones(dataset.n)

                            bjd_plot[plot_x0_keyword][dataset_name][model_name] = \
                                bjd_plot[plot_x0_keyword][dataset_name][model_name] * np.ones(dataset.n)

                        for x, x0, pha, y, e, sys, mod, com, obs_mod, res in zip(
                            dataset.x, dataset.x0, phase, dataset.y, dataset.e,
                                bjd_plot[plot_out_keyword][dataset_name]['systematics'],
                                bjd_plot[plot_out_keyword][dataset_name][model_name],
                                bjd_plot[plot_out_keyword][dataset_name]['complete'],
                                dataset.y - bjd_plot[plot_out_keyword][dataset_name]['complete'] +
                                        bjd_plot[plot_out_keyword][dataset_name][model_name],
                                dataset.y - bjd_plot[plot_out_keyword][dataset_name]['complete']):

                            fileout.write('{0:f} {1:f} {2:f} {3:f} {4:f} {5:f} {6:1f} {7:f} {8:f} {9:f} {10:f} {11:f}'
                                          '\n'.format(x, x0, pha, y, e, sys, mod, com, obs_mod, e, res, e))
                        fileout.close()

                        fileout = open(dir_models + dataset_name + '_' + model_name + '_full.dat', 'w')

                        if model_name+'_std' in bjd_plot[plot_x0_keyword][dataset_name]:
                            fileout.write('descriptor BJD BJD0 mod,+- \n')
                            for x0, mod, std in zip(bjd_plot[dataset_name]['x0_plot'],
                                               bjd_plot[plot_x0_keyword][dataset_name][model_name],
                                               bjd_plot[plot_x0_keyword][dataset_name][model_name+'_std']):

                                fileout.write('{0:f} {1:f} {2:f} {3:f} \n'.format(x0+mc.Tref, x0, mod, std))
                            fileout.close()
                        else:
                            fileout.write('descriptor BJD BJD0 mod \n')
                            for x0, mod in zip(bjd_plot[dataset_name]['x0_plot'],
                                               bjd_plot[plot_x0_keyword][dataset_name][model_name]):
                                fileout.write('{0:f} {1:f} {2:f} \n'.format(x0+mc.Tref, x0, mod))
                            fileout.close()

                    fileout = open(dir_models + dataset_name + '_full.dat', 'w')
                    fileout.write('descriptor BJD BJD0 mod \n')
                    for x0, mod in zip(bjd_plot[dataset_name]['x0_plot'],
                                       bjd_plot[plot_x0_keyword][dataset_name]['complete']):
                        fileout.write('{0:f} {1:f} {2:f} \n'.format(x0+mc.Tref, x0, mod))
                    fileout.close()

                for model in planet_vars:

                    try:
                        RV_out =  kepler_exo.kepler_RV_T0P(bjd_plot['full']['x0_plot'],
                                                           planet_vars[model]['f'],
                                                           planet_vars[model]['P'],
                                                           planet_vars[model]['K'],
                                                           planet_vars[model]['e'],
                                                           planet_vars[model]['o'])
                        fileout = open(dir_models + 'RV_planet_' + model + '_kep.dat', 'w')
                        fileout.write('descriptor x_range x_range0 m_kepler \n')
                        for x, y in zip(bjd_plot['full']['x0_plot'], RV_out):
                            fileout.write('{0:f} {1:f} {2:f} \n'.format(x+mc.Tref, x, y))
                        fileout.close()

                        x_range = np.arange(-0.50, 1.50, 0.001)
                        RV_out = kepler_exo.kepler_RV_T0P(x_range*planet_vars[model]['P'],
                                                           planet_vars[model]['f'],
                                                           planet_vars[model]['P'],
                                                           planet_vars[model]['K'],
                                                           planet_vars[model]['e'],
                                                           planet_vars[model]['o'])
                        fileout = open(dir_models + 'RV_planet_' + model + '_pha.dat', 'w')
                        fileout.write('descriptor x_phase m_phase \n')
                        for x, y in zip(x_range, RV_out):
                            fileout.write('{0:f} {1:f} \n'.format(x, y))
                        fileout.close()
                    except:
                        pass


    print
    print '****************************************************************************************************'
    print

    veusz_dir = dir_output + '/Veuz_plot/'
    if not os.path.exists(veusz_dir):
        os.makedirs(veusz_dir)

    all_variables_list = {}
    for dataset_name, dataset in mc.dataset_dict.iteritems():
        variable_values = dataset.convert(flat_chain)

        for variable_name, variable in variable_values.iteritems():
            all_variables_list[dataset_name + '_' + variable_name] = variable

        for model_name in dataset.models:
            variable_values = mc.models[model_name].convert(flat_chain, dataset_name)
            for variable_name, variable in variable_values.iteritems():
                all_variables_list[dataset_name + '_' + model_name + '_' + variable_name] = variable

    for model in mc.common_models.itervalues():
        variable_values = model.convert(flat_chain)

        for variable_name, variable in variable_values.iteritems():
            #for common_ref in mc.models[model_name].common_ref:
            all_variables_list[model.common_ref + '_' + variable_name] = variable

    n_int = len(all_variables_list)
    output_plan = np.zeros([n_samplings, n_int], dtype=np.double)
    output_names = []
    for var_index, variable_name in enumerate(all_variables_list):
        output_plan[:, var_index] = all_variables_list[variable_name]
        output_names.extend([variable_name])

    plot_truths = np.percentile(output_plan[:, :], [15.865, 50, 84.135], axis=0)
    n_bins = 30 + 1

    h5f = h5py.File(veusz_dir + '_hist1d.hdf5', "w")
    data_grp = h5f.create_group("hist1d")

    data_lim = np.zeros([n_int, 2], dtype=np.double)
    data_edg = np.zeros([n_int, n_bins], dtype=np.double)
    data_skip = np.zeros(n_int, dtype=bool)

    sigma_minus = plot_truths[1, :] - plot_truths[0, :]
    sigma_plus = plot_truths[2, :] - plot_truths[1, :]
    median_vals = plot_truths[1, :]

    for ii in xrange(0, n_int):

        #sig_minus = plot_truths[1, ii] - plot_truths[0, ii]
        #sig_plus = plot_truths[2, ii] - plot_truths[1, ii]

        if sigma_minus[ii] == 0. and sigma_plus[ii] == 0.:
            data_skip[ii] = True
            continue

        sigma5_selection = (output_plan[:, ii] > median_vals[ii] - 5 * sigma_minus[ii]) & \
                           (output_plan[:, ii] < median_vals[ii] + 5 * sigma_plus[ii])

        data_lim[ii, :] = [np.amin(output_plan[sigma5_selection, ii]), np.amax(output_plan[sigma5_selection, ii])]
        if data_lim[ii, 0] == data_lim[ii, 1]:
            data_lim[ii, :] = [np.amin(output_plan[:, ii]), np.amax(output_plan[:, ii])]
        if data_lim[ii, 0] == data_lim[ii, 1]:
            data_skip[ii] = True
            continue

        data_edg[ii, :] = np.linspace(data_lim[ii, 0], data_lim[ii, 1], n_bins)

    veusz_workaround_descriptor = 'descriptor'
    veusz_workaround_values = ''

    for ii in xrange(0, n_int):

        if data_skip[ii]:
            continue

        x_data = output_plan[:, ii]
        x_edges = data_edg[ii, :]

        for jj in xrange(0, n_int):

            if data_skip[jj]:
                continue

            y_data = output_plan[:, jj]
            y_edges = data_edg[jj, :]

            if ii != jj:

                hist2d = np.histogram2d(x_data, y_data, bins=[x_edges, y_edges], density=True)
                hist1d_y = np.histogram(y_data, bins=y_edges, density=True)

                Hflat = hist2d[0].flatten()
                inds = np.argsort(Hflat)[::-1]
                Hflat = Hflat[inds]
                sm = np.cumsum(Hflat)
                sm /= sm[-1]

                x_edges_1d = (x_edges[1:] + x_edges[:-1])/2
                y_edges_1d = (y_edges[1:] + y_edges[:-1])/2
                h2d_out = np.zeros([n_bins, n_bins])
                h2d_out[0, 1:] = x_edges_1d
                h2d_out[1:, 0] = y_edges_1d
                h2d_out[1:, 1:] = hist2d[0].T *1. / np.amax(hist2d[0])

                h2d_list =  h2d_out.tolist()
                h2d_list[0][0] = ''
                csvfile = veusz_dir + '_hist2d___' + output_names[ii] + '___' + output_names[jj] + '.csv'
                with open(csvfile, "w") as output:
                    writer = csv.writer(output, lineterminator='\n')
                    writer.writerows(h2d_list)

        hist1d = np.histogram(x_data, bins=x_edges)
        hist1d_norm = hist1d[0]*1. / n_samplings
        x_edges_1d = (x_edges[1:]+ x_edges[:-1])/2
        data_grp.create_dataset(output_names[ii]+'_x', data=x_edges_1d, compression="gzip")
        data_grp.create_dataset(output_names[ii]+'_y', data=hist1d_norm, compression="gzip")

        #data_grp.create_dataset(output_names[ii]+'_val', data=median_vals[ii])
        #data_grp.create_dataset(output_names[ii]+'_val_-', data=sigma_minus[ii])
        #data_grp.create_dataset(output_names[ii]+'_val_+', data=sigma_plus[ii])
        #data_grp.attrs[output_names[ii]+'_val'] = median_vals[ii]

        veusz_workaround_descriptor += ' ' + output_names[ii] + ',+,-'
        veusz_workaround_values += ' ' + repr(median_vals[ii]) + ' ' + repr(sigma_plus[ii]) + ' ' + repr(sigma_minus[ii])

    text_file = open(veusz_dir + "veusz_median_sigmas.txt", "w")
    text_file.write('%s \n' % veusz_workaround_descriptor)
    text_file.write('%s \n' % veusz_workaround_values)
    text_file.close()
