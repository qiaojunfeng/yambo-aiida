# -*- coding: utf-8 -*-
"""Classes for calcs e wfls analysis. hybrid AiiDA and not_AiiDA...hopefully"""
from __future__ import absolute_import
import numpy as np
from scipy.optimize import curve_fit
from matplotlib import pyplot as plt, style
import pandas as pd
import copy
import cmath

try:
    from aiida.orm import Dict, Str, load_node, KpointsData
    from aiida.plugins import CalculationFactory, DataFactory
    from aiida_yambo.utils.common_helpers import *
    from aiida_yambo.utils.parallelism_finder import *
except:
    pass

################################################################################
'''
PAR_def_mode= "balanced"       # [PARALLEL] Default distribution mode ("balanced"/"memory"/"workload")
'''
################################################################################
def fix_parallelism(resources, failed_calc):

    bands, qp, last_qp, runlevels = find_gw_info(failed_calc.inputs)
    nscf = find_pw_parent(failed_calc,calc_type=['nscf']) 
    occupied = gap_mapping_from_nscf(nscf.pk,)['valence']
    mesh = nscf.inputs.kpoints.get_kpoints_mesh()[0]
    kpoints = mesh[0]*mesh[1]*mesh[2]/2  #moreless... to fix

    if 'gw0' or 'HF_and_locXC' in runlevels:
        new_parallelism, new_resources = find_parallelism_qp(resources['num_machines'], resources['num_mpiprocs_per_machine'], \
                                                        resources['num_cores_per_mpiproc'], bands, \
                                                        occupied, qp, kpoints,\
                                                        last_qp, namelist = {})
    elif 'bse' in runlevels:
        pass
    
    return new_parallelism, new_resources

def fix_memory(resources, failed_calc, exit_status, max_nodes, iteration):
        
    bands, qp, last_qp, runlevels = find_gw_info(failed_calc.inputs)
    nscf = find_pw_parent(failed_calc,calc_type=['nscf']) 
    occupied = gap_mapping_from_nscf(nscf.pk,)['valence']
    mesh = nscf.inputs.kpoints.get_kpoints_mesh()[0]
    kpoints = mesh[0]*mesh[1]*mesh[2]/2  #moreless... to fix

    if resources['num_mpiprocs_per_machine']==1 or failed_calc.outputs.output_parameters.get_dict()['has_gpu'] or iteration > 1: #there should be a limit
        
        new_nodes = int(2*resources['num_machines'])
        #new_nodes += new_nodes%2
        
        if new_nodes <= max_nodes:
            resources['num_machines'] = new_nodes
        else:
            resources['num_machines'] = max_nodes
        
        resources['num_mpiprocs_per_machine'] *= 2
        resources['num_cores_per_mpiproc'] /= 2

    if 'gw0' or 'HF_and_locXC' in runlevels:
        new_parallelism, new_resources = find_parallelism_qp(resources['num_machines'], resources['num_mpiprocs_per_machine']/2, \
                                                        resources['num_cores_per_mpiproc']*2, bands, \
                                                        occupied, qp, kpoints,\
                                                        last_qp, namelist = {})
    elif 'bse' in runlevels:
        pass
    
    return new_parallelism, new_resources

def fix_time(options, restart, max_walltime):
    options['max_wallclock_seconds'] = \
                            int(options['max_wallclock_seconds']*1.5*restart)

    if options['max_wallclock_seconds'] > max_walltime:
        options['max_wallclock_seconds'] = int(max_walltime)

    return options
