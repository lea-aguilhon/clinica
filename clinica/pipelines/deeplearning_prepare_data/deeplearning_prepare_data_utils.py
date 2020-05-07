# coding: utf8

"""Deeplearning prepare data - Clinica Utilities.
This file has been generated automatically by the `clinica generate template`
command line tool. See here for more details:
http://clinica.run/doc/InteractingWithClinica/
"""


def step1(t1w, in_hello_word):
    """Example function for Step 1.
    """
    from clinica.utils.stream import cprint

    cprint(in_hello_word + " from the step 1 of the Deeplearning prepare data Clinica pipeline for" + t1w)


def step2(t1w, in_advanced_arg):
    """Example function for Step 2.
    """
    from clinica.utils.stream import cprint

    cprint(in_advanced_arg + " arg from the step 2 of the Deeplearning prepare data Clinica pipeline for" + t1w)
