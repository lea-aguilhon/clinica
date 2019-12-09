# coding: utf8

import clinica.pipelines.engine as cpe


class StatisticsSurface(cpe.Pipeline):
    """
    Based on the Matlab toolbox [SurfStat](http://www.math.mcgill.ca/keith/surfstat/), which performs statistical
    analyses of univariate and multivariate surface and volumetric data using the generalized linear model (GLM),
    this pipeline performs analyses including group comparison and correlation with surface-based features e.g.
    cortical thickness from t1-freesurfer or map of activity from PET data from pet-surface pipeline.

    TODO: Refactor StatisticsSurface
        [ ] build_input_node
            [X] Remove current read_parameters_node
            [ ] With the help of statistics_surface_utils.py::check_inputs, use new clinica_file_reader function
                to check and extract surface-based features
            [X] Delete statistics_surface_utils.py::check_inputs function
            [X] Move statistics_surface_cli.py checks of input data in this method
            [ ] Handle overwrite case
            [ ] Display participants, covariates and info regarding the GLM.
        [ ] build_core_nodes
            [X] Use surfstat.inputs.full_width_at_half_maximum = self.parameter['full_width_at_half_maximum']
                instead of connecting read_parameters_node.inputs.full_width_at_half_maximum
                to surfstat.inputs.full_width_at_half_maximum
            [X] Repeat for other keys
            [ ] Use working directory
        [ ] build_output_node
            [ ] Remove path_to_matscript and freesurfer_home: it should be set in runmatlab function
            [ ] Copy results from <WD> to <CAPS>
        [ ] Clean/adapt statistics_surface_utils.py

    Args:
        tsv_file: str, Path to the tsv containing the information for GLM.
        design_matrix: str, the linear model that fits into the GLM, for example '1+group'.
        contrast: string, the contrast matrix for GLM, if the factor you choose is categorized variable, clinica_surfstat will create two contrasts,
                  for example, contrast = 'Label', this will create contrastpos = Label.AD - Label.CN, contrastneg = Label.CN - Label.AD; if the fac-
                  tory that you choose is a continuous factor, clinica_surfstat will just create one contrast, for example, contrast = 'Age', but note,
                  the string name that you choose should be exactly the same with the columns names in your subjects_visits_tsv.
        str_format: string, the str_format which uses to read your tsv file, the typy of the string should corresponds exactly with the columns in the tsv file.
            Defaut parameters, we set these parameters to be some default values, but you can also set it by yourself:
        group_label: current group name for this analysis
        glm_type: based on the hypothesis, you should define one of the glm types, "group_comparison", "correlation"
        full_width_at_half_maximum: fwhm for the surface smoothing, default is 20, integer.
        threshold_uncorrected_pvalue: threshold to display the uncorrected Pvalue, float, default is 0.001.
        threshold_corrected_pvalue: the threshold to display the corrected cluster, default is 0.05, float.
        cluster_threshold: threshold to define a cluster in the process of cluster-wise correction, default is 0.001, float.

    Returns:
        A clinica pipeline object containing the StatisticsSurface pipeline.
    """
    def check_pipeline_parameters(self):
        """Check pipeline parameters."""
        from .statistics_surface_utils import get_t1_freesurfer_custom_file
        from clinica.utils.exceptions import ClinicaException
        from clinica.utils.group import check_group_label

        if 'custom_file' not in self.parameters.keys():
            self.parameters['custom_file'] = get_t1_freesurfer_custom_file()
        if 'feature_label' not in self.parameters.keys():
            self.parameters['feature_label'] = 'ct',
        if 'full_width_at_half_maximum' not in self.parameters.keys():
            self.parameters['full_width_at_half_maximum'] = 20
        if 'threshold_uncorrected_pvalue' not in self.parameters.keys():
            self.parameters['threshold_uncorrected_pvalue'] = 0.001
        if 'threshold_corrected_pvalue' not in self.parameters.keys():
            self.parameters['threshold_corrected_pvalue'] = 0.05,
        if 'cluster_threshold' not in self.parameters.keys():
            self.parameters['cluster_threshold'] = 0.001,

        check_group_label(self.parameters['group_label'])
        if self.parameters['glm_type'] not in ['group_comparison', 'correlation']:
            raise ClinicaException("The glm_type you specified is wrong: it should be group_comparison or "
                                   "correlation (given value: %s)." % self.parameters['glm_type'])
        if self.parameters['full_width_at_half_maximum'] not in [0, 5, 10, 15, 20]:
            raise ClinicaException(
                "FWHM for the surface smoothing you specified is wrong: it should be 0, 5, 10, 15 or 20 "
                "(given value: %s)." % self.parameters['full_width_at_half_maximum'])
        if self.parameters['threshold_uncorrected_pvalue'] < 0 or self.parameters['threshold_uncorrected_pvalue'] > 1:
            raise ClinicaException("Uncorrected p-value threshold should be a lower than 1 "
                                   "(given value: %s)." % self.parameters['threshold_uncorrected_pvalue'])
        if self.parameters['threshold_corrected_pvalue'] < 0 or self.parameters['threshold_corrected_pvalue'] > 1:
            raise ClinicaException("Corrected p-value threshold should be between 0 and 1 "
                                   "(given value: %s)." % self.parameters['threshold_corrected_pvalue'])
        if self.parameters['cluster_threshold'] < 0 or self.parameters['cluster_threshold'] > 1:
            raise ClinicaException("Cluster threshold should be between 0 and 1 "
                                   "(given value: %s)." % self.parameters['cluster_threshold'])

    def check_custom_dependencies(self):
        """Check dependencies that can not be listed in the `info.json` file.
        """
        pass

    def get_input_fields(self):
        """Specify the list of possible inputs of this pipelines.

        Returns:
            A list of (string) input fields name.
        """

        return []

    def get_output_fields(self):
        """Specify the list of possible outputs of this pipelines.

        Returns:
            A list of (string) output fields name.
        """

        return []

    def build_input_node(self):
        """Build and connect an input node to the pipelines.
        """
        import os
        import pandas as pd
        from clinica.utils.exceptions import ClinicaException
        from clinica.utils.stream import cprint

        # Check if the group label has been existed, if yes, give an error to the users
        # Note(AR): if the user wants to compare Cortical Thickness measure with PET measure
        # using the group_id, Clinica won't allow it.
        # TODO: Modify this behaviour
        if os.path.exists(os.path.join(os.path.abspath(self.caps_directory), 'groups', 'group-' + self.parameters['group_label'])):
            error_message = ('Group ID %s already exists, please choose another one or delete the existing folder and '
                             'also the working directory and rerun the pipeline') % self.parameters['group_label']
            raise ClinicaException(error_message)

        # Check input files
        subjects_visits = pd.io.parsers.read_csv(self.tsv_file, sep='\t')
        subjects = list(subjects_visits.participant_id)
        sessions = list(subjects_visits.session_id)
        missing_files = []
        for idx in range(len(subjects)):
            full_path = os.path.join(self.caps_directory,
                                     'subjects',
                                     self.parameters['custom_file'].replace(
                                         '@subject', subjects[idx]).replace(
                                         '@session', sessions[idx]).replace(
                                         '@fwhm', str(self.parameters['full_width_at_half_maximum']))
                                     )
            left_hemi = full_path.replace('@hemi', 'lh')
            right_hemi = full_path.replace('@hemi', 'rh')

            if not os.path.exists(left_hemi):
                missing_files.append(left_hemi)
            if not os.path.exists(right_hemi):
                missing_files.append(right_hemi)

        if len(missing_files) > 0:
            cprint(' ** Missing files **')
            for l in missing_files:
                cprint('Not found: ' + l)
            raise Exception(str(len(missing_files)) + ' files not found !')

        # Print GLM information
        cprint("Parameters used for this pipeline:")
        cprint(self.parameters)

    def build_output_node(self):
        """Build and connect an output node to the pipelines.
        """

        pass

    def build_core_nodes(self):
        """Build and connect the core nodes of the pipelines.
        """
        import clinica.pipelines.statistics_surface.statistics_surface_utils as utils
        import nipype.interfaces.utility as nutil
        import nipype.pipeline.engine as npe
        from nipype.interfaces.io import JSONFileSink

        # Node to fetch the input variables
        data_prep = npe.Node(name='inputnode',
                             interface=nutil.Function(
                                 input_names=['input_directory', 'subjects_visits_tsv', 'group_label', 'glm_type'],
                                 output_names=['path_to_matscript', 'surfstat_input_dir', 'output_directory',
                                               'freesurfer_home', 'out_json'],
                                 function=utils.prepare_data))
        data_prep.inputs.input_directory = self.caps_directory
        data_prep.inputs.subjects_visits_tsv = self.tsv_file
        data_prep.inputs.group_label = self.parameters['group_label']
        data_prep.inputs.glm_type = self.parameters['glm_type']

        # Node to wrap the SurfStat matlab script
        surfstat = npe.Node(name='surfstat',
                            interface=nutil.Function(
                                input_names=['input_directory',
                                             'output_directory',
                                             'subjects_visits_tsv',
                                             'design_matrix',
                                             'contrast',
                                             'str_format',
                                             'glm_type',
                                             'group_label',
                                             'freesurfer_home',
                                             'surface_file',
                                             'path_to_matscript',
                                             'full_width_at_half_maximum',
                                             'threshold_uncorrected_pvalue',
                                             'threshold_corrected_pvalue',
                                             'cluster_threshold',
                                             'feature_label'],
                                output_names=['out_images'],
                                function=utils.run_matlab))
        surfstat.inputs.subjects_visits_tsv = self.tsv_file
        surfstat.inputs.design_matrix = self.parameters['design_matrix']
        surfstat.inputs.contrast = self.parameters['contrast']
        surfstat.inputs.str_format = self.parameters['str_format']
        surfstat.inputs.glm_type = self.parameters['glm_type']
        surfstat.inputs.group_label = self.parameters['group_label']
        surfstat.inputs.full_width_at_half_maximum = self.parameters['full_width_at_half_maximum']
        surfstat.inputs.threshold_uncorrected_pvalue = self.parameters['threshold_uncorrected_pvalue']
        surfstat.inputs.threshold_corrected_pvalue = self.parameters['threshold_corrected_pvalue']
        surfstat.inputs.cluster_threshold = self.parameters['cluster_threshold']
        surfstat.inputs.surface_file = self.parameters['custom_file']
        surfstat.inputs.feature_label = self.parameters['feature_label']

        # Node to create the dictionary for JSONFileSink
        json_dict = npe.Node(name='Jsondict',
                             interface=nutil.Function(
                                 input_names=['glm_type', 'design_matrix', 'str_format', 'contrast', 'group_label',
                                              'full_width_at_half_maximum', 'threshold_uncorrected_pvalue',
                                              'threshold_corrected_pvalue', 'cluster_threshold'],
                                 output_names=['json_dict'],
                                 function=utils.json_dict_create))
        json_dict.inputs.glm_type = self.parameters['glm_type']
        json_dict.inputs.design_matrix = self.parameters['design_matrix']
        json_dict.inputs.str_format = self.parameters['str_format']
        json_dict.inputs.contrast = self.parameters['contrast']
        json_dict.inputs.group_label = self.parameters['group_label']
        json_dict.inputs.full_width_at_half_maximum = self.parameters['full_width_at_half_maximum']
        json_dict.inputs.threshold_uncorrected_pvalue = self.parameters['threshold_uncorrected_pvalue']
        json_dict.inputs.threshold_corrected_pvalue = self.parameters['threshold_corrected_pvalue']
        json_dict.inputs.cluster_threshold = self.parameters['cluster_threshold']

        # Node to write the GLM information into a JSON file
        json_datasink = npe.Node(JSONFileSink(input_names=['out_file']), name='json_datasink')

        # Connection
        # ==========
        self.connect([
            (data_prep, surfstat, [('surfstat_input_dir', 'input_directory')]),
            (data_prep, surfstat, [('path_to_matscript', 'path_to_matscript')]),
            (data_prep, surfstat, [('output_directory', 'output_directory')]),
            (data_prep, surfstat, [('freesurfer_home', 'freesurfer_home')]),
            (data_prep, json_datasink, [('out_json', 'out_file')]),
            (json_dict, json_datasink, [('json_dict', 'in_dict')]),
        ])
