import numpy as np
import h5py
import time as timemodule
import pycbc
from pycbc.waveform import utils

"""Includes a method to append echoes to a given waveform 
and a tapering function used for the echo's form 
relative to the original waveform."""

def truncfunc(t, t0, t_merger, omega_of_t):

    """A tapering function used to smoothly introduce the echo waveforms
    from the original waveform."""

    theta = 0.5 * (1 + np.tanh(0.5 * omega_of_t * (t - t_merger - t0)))
    return theta


def add_echoes(hp, hc, t0trunc, t_echo, del_t_echo, n_echoes, amplitude, gamma,
               timestep=None):
    """Takes waveform timeseries' of plus and cross polarisation, 
    produces echoes of the waveform and returns the original 
    waveform timeseries' with the echoes appended. 
    The original starting time is lost, however.

    Parameters:
    hp, hc : timeseries
        Plus and cross polarisation timeseries' of the original waveform.
    t0trunc : float
        Truncation time parameter for the echo form, time difference taken 
        with respect to time of merger. Thought to be negative, in seconds.
    t_echo : float
        Time difference between original waveform and first echo, in seconds.
    del_t_echo : float
        Time difference between subsequent echoes, in seconds.
    n_echoes : integer
        Number of echoes to be appended. 
    amplitude : float
        Strain amplitude of first echo with respect to original wave amplitude.
    gamma : float
        Dampening factor between two successive echoes. (n+1)st echo has 
        amplitude of (n)th echo multiplied with gamma.
    
    Returns:
    hp, hc: timeseries
        Waveform timeseries' for plus and cross polarisation with echoes 
        appended.    
    """
    
    if timestep is None:
        timestep = hp.delta_t
    
    hp_numpy = hp.numpy()
    hc_numpy = hc.numpy()

    template = (hp_numpy + 1j*hc_numpy)
    
    # Finding the merger time as time of maximum strain amplitude.
    sampletimesarray = hp.sample_times
    t_merger = sampletimesarray[np.argmax(np.absolute(template))]
    
    # Counting leading zeros. Calculate angular frequency for trimmed waveform. For leading/trailing zeros, use first/last frequency found. Use np.nonzero instead?
    
    omega = 2. * np.pi * utils.frequency_from_polarizations(hp.trim_zeros(), 
                                                        hc.trim_zeros())
    
    omega_temp = np.zeros(len(template))
    first_zero_index_hp = 0
    first_zero_index_hc = 0
    
    if hp[0] == 0 and hc[0] == 0:
        print('Active')
        
        while hp[first_zero_index_hp] == 0:
            first_zero_index_hp += 1
        
        while hc[first_zero_index_hc] == 0:
            first_zero_index_hc += 1
        
        if first_zero_index_hp != first_zero_index_hc:
            print('Polarisations have unequal number of leading zeroes.')
        
        omega_temp[:max(first_zero_index_hp,first_zero_index_hc)] = omega[max(first_zero_index_hp,first_zero_index_hc)]
        omega = omega_temp
    
    omega.resize(len(template))
    
    #Producing the tapered waveform from the original one for the echoes:
    length = len(hp)
    tapercoeff = truncfunc(
                        sampletimesarray.numpy(), 
                        t0trunc, 
                        t_merger, 
                        omega
                    )
                    
    hp_numpy = (hp_numpy * tapercoeff)
    hc_numpy = (hc_numpy * tapercoeff)
    
    #Appending first echo after t_echo.

    hparray = np.zeros(
                    len(hp) 
                    + int(np.ceil((t_echo + n_echoes * del_t_echo) * 1.0/timestep))
                    )
    
    hcarray = np.zeros(
                    len(hc) 
                    + int(np.ceil((t_echo + n_echoes * del_t_echo) * 1.0/timestep))
                    )

# uncomment below to add in original event    
#    hparray[:length] += hp.numpy()
#    hcarray[:length] += hc.numpy()
    
    t_echo_steps = int(round(t_echo * 1.0/timestep))
    
    hparray[
        t_echo_steps:(t_echo_steps+len(hp_numpy))
        ] += hp_numpy * amplitude * -1.0
        
    hcarray[
        t_echo_steps:(t_echo_steps+len(hc_numpy))
        ] += hc_numpy * amplitude * -1.0

    #Appending further echoes. 

    for j in range(1, int(n_echoes)):

        del_t_echo_steps = int(round((t_echo + del_t_echo * j) * 1.0/timestep))
        
        hparray[
                del_t_echo_steps:(del_t_echo_steps+length)
                ] += hp_numpy * amplitude * gamma**(j) * ((-1.0)**(j+1))
        
        hcarray[
                del_t_echo_steps:(del_t_echo_steps+length)
                ] += hc_numpy * amplitude * gamma**(j) * ((-1.0)**(j+1))

    hp = pycbc.types.TimeSeries(initial_array=hparray, delta_t=timestep, epoch=hp.sample_times[0])
    hc = pycbc.types.TimeSeries(initial_array=hcarray, delta_t=timestep, epoch=hc.sample_times[0])
    
    return hp, hc
