from typing import List

from clinica.pipelines.engine import GroupPipeline


class T1VolumeDartel2MNI(GroupPipeline):
    """T1VolumeDartel2MNI - Dartel template to MNI.

    Returns:
        A clinica pipeline object containing the T1VolumeDartel2MNI pipeline.
    """

    def _check_pipeline_parameters(self) -> None:
        """Check pipeline parameters."""
        self.parameters.setdefault("tissues", [1, 2, 3])
        self.parameters.setdefault("voxel_size", None)
        self.parameters.setdefault("modulate", True)
        self.parameters.setdefault("smooth", [8])

    def _check_custom_dependencies(self) -> None:
        """Check dependencies that can not be listed in the `info.json` file."""
        pass

    def get_input_fields(self) -> List[str]:
        """Specify the list of possible inputs of this pipeline.

        Returns
        -------
        list of str :
            A list of (string) input fields name.
        """
        return ["native_segmentations", "flowfield_files", "template_file"]

    def get_output_fields(self) -> List[str]:
        """Specify the list of possible outputs of this pipeline.

        Returns
        -------
        list of str :
            A list of (string) output fields name.
        """
        return ["normalized_files", "smoothed_normalized_files", "atlas_statistics"]

    def _build_input_node(self):
        """Build and connect an input node to the pipeline."""
        import nipype.interfaces.utility as nutil
        import nipype.pipeline.engine as npe

        from clinica.utils.exceptions import ClinicaCAPSError, ClinicaException
        from clinica.utils.input_files import (
            t1_volume_deformation_to_template,
            t1_volume_final_group_template,
            t1_volume_native_tpm,
        )
        from clinica.utils.inputs import (
            clinica_file_reader,
            clinica_group_reader,
            clinica_list_of_files_reader,
            format_clinica_file_reader_errors,
        )
        from clinica.utils.stream import cprint
        from clinica.utils.ux import (
            print_groups_in_caps_directory,
            print_images_to_process,
        )

        if not self.group_directory.exists():
            print_groups_in_caps_directory(self.caps_directory)
            raise ClinicaException(
                f"Group {self.group_label} does not exist. "
                "Did you run t1-volume or t1-volume-create-dartel pipeline?"
            )

        all_errors = []
        read_input_node = npe.Node(
            name="LoadingCLIArguments",
            interface=nutil.IdentityInterface(
                fields=self.get_input_fields(), mandatory_inputs=True
            ),
        )

        # Segmented Tissues
        # =================
        try:
            tissues_input = clinica_list_of_files_reader(
                self.subjects,
                self.sessions,
                self.caps_directory,
                [
                    t1_volume_native_tpm(tissue_number)
                    for tissue_number in self.parameters["tissues"]
                ],
            )
            # Tissues_input has a length of len(self.parameters['mask_tissues']). Each of these elements has a size of
            # len(self.subjects). We want the opposite : a list of size len(self.subjects) whose elements have a size of
            # len(self.parameters['mask_tissues']. The trick is to iter on elements with zip(*my_list)
            tissues_input_rearranged = []
            for subject_tissue_list in zip(*tissues_input):
                tissues_input_rearranged.append(subject_tissue_list)
                read_input_node.inputs.native_segmentations = tissues_input_rearranged
        except ClinicaException as e:
            all_errors.append(e)

        # Flow Fields
        # ===========
        read_input_node.inputs.flowfield_files, flowfield_errors = clinica_file_reader(
            self.subjects,
            self.sessions,
            self.caps_directory,
            t1_volume_deformation_to_template(self.group_label),
        )
        if flowfield_errors:
            all_errors.append(format_clinica_file_reader_errors(flowfield_errors))

        # Dartel Template
        # ================
        try:
            read_input_node.inputs.template_file = clinica_group_reader(
                self.caps_directory,
                t1_volume_final_group_template(self.group_label),
            )
        except ClinicaException as e:
            all_errors.append(e)

        if any(all_errors):
            error_message = "Clinica faced error(s) while trying to read files in your CAPS/BIDS directories.\n"
            for msg in all_errors:
                error_message += str(msg)
            raise ClinicaCAPSError(error_message)

        if len(self.subjects):
            print_images_to_process(self.subjects, self.sessions)
            cprint("The pipeline will last a few minutes per image.")

        self.connect(
            [
                (
                    read_input_node,
                    self.input_node,
                    [
                        ("native_segmentations", "native_segmentations"),
                        ("flowfield_files", "flowfield_files"),
                        ("template_file", "template_file"),
                    ],
                ),
            ]
        )

    def _build_output_node(self):
        """Build and connect an output node to the pipeline."""
        import nipype.interfaces.io as nio
        import nipype.pipeline.engine as npe

        from clinica.utils.filemanip import zip_nii

        write_normalized_node = npe.MapNode(
            name="write_normalized_node",
            iterfield=["container", "normalized_files", "smoothed_normalized_files"],
            interface=nio.DataSink(
                infields=["normalized_files", "smoothed_normalized_files"]
            ),
        )
        write_normalized_node.inputs.base_directory = str(self.caps_directory)
        write_normalized_node.inputs.parameterization = False
        write_normalized_node.inputs.container = [
            "subjects/"
            + self.subjects[i]
            + "/"
            + self.sessions[i]
            + f"/t1/spm/dartel/{self.group_id}"
            for i in range(len(self.subjects))
        ]
        write_normalized_node.inputs.regexp_substitutions = [
            (r"(.*)c1(sub-.*)(\.nii(\.gz)?)$", r"\1\2_segm-graymatter_probability\3"),
            (r"(.*)c2(sub-.*)(\.nii(\.gz)?)$", r"\1\2_segm-whitematter_probability\3"),
            (r"(.*)c3(sub-.*)(\.nii(\.gz)?)$", r"\1\2_segm-csf_probability\3"),
            (r"(.*)c4(sub-.*)(\.nii(\.gz)?)$", r"\1\2_segm-bone_probability\3"),
            (r"(.*)c5(sub-.*)(\.nii(\.gz)?)$", r"\1\2_segm-softtissue_probability\3"),
            (r"(.*)c6(sub-.*)(\.nii(\.gz)?)$", r"\1\2_segm-background_probability\3"),
            (
                r"(.*)mw(sub-.*)_probability(\.nii(\.gz)?)$",
                r"\1\2_space-Ixi549Space_modulated-on_probability\3",
            ),
            (
                r"(.*)w(sub-.*)_probability(\.nii(\.gz)?)$",
                r"\1\2_space-Ixi549Space_modulated-off_probability\3",
            ),
            (r"(.*)/normalized_files/(sub-.*)$", r"\1/\2"),
            (
                r"(.*)/smoothed_normalized_files/(fwhm-[0-9]+mm)_(sub-.*)_probability(\.nii(\.gz)?)$",
                r"\1/\3_\2_probability\4",
            ),
            (r"trait_added", r""),
        ]

        self.connect(
            [
                (
                    self.output_node,
                    write_normalized_node,
                    [
                        (("normalized_files", zip_nii, True), "normalized_files"),
                        (
                            ("smoothed_normalized_files", zip_nii, True),
                            "smoothed_normalized_files",
                        ),
                    ],
                )
            ]
        )

    def _build_core_nodes(self):
        """Build and connect the core nodes of the pipeline."""
        import nipype.interfaces.spm as spm
        import nipype.interfaces.utility as nutil
        import nipype.pipeline.engine as npe

        from clinica.utils.filemanip import unzip_nii
        from clinica.utils.spm import use_spm_standalone_if_available

        from ..t1_volume_dartel2mni import (
            t1_volume_dartel2mni_utils as dartel2mni_utils,
        )

        use_spm_standalone_if_available()

        unzip_tissues_node = npe.MapNode(
            nutil.Function(
                input_names=["in_file"], output_names=["out_file"], function=unzip_nii
            ),
            name="unzip_tissues_node",
            iterfield=["in_file"],
        )
        unzip_flowfields_node = npe.MapNode(
            nutil.Function(
                input_names=["in_file"], output_names=["out_file"], function=unzip_nii
            ),
            name="unzip_flowfields_node",
            iterfield=["in_file"],
        )
        unzip_template_node = npe.Node(
            nutil.Function(
                input_names=["in_file"], output_names=["out_file"], function=unzip_nii
            ),
            name="unzip_template_node",
        )

        # DARTEL2MNI Registration
        # =======================
        dartel2mni_node = npe.MapNode(
            spm.DARTELNorm2MNI(),
            name="dartel2MNI",
            iterfield=["apply_to_files", "flowfield_files"],
        )
        if self.parameters["voxel_size"] is not None:
            dartel2mni_node.inputs.voxel_size = tuple(self.parameters["voxel_size"])
        dartel2mni_node.inputs.modulate = self.parameters["modulate"]
        dartel2mni_node.inputs.fwhm = 0

        if self.parameters["smooth"] is not None and len(self.parameters["smooth"]) > 0:
            smoothing_node = npe.MapNode(
                spm.Smooth(), name="smoothing_node", iterfield=["in_files"]
            )

            smoothing_node.iterables = [
                ("fwhm", [[x, x, x] for x in self.parameters["smooth"]]),
                (
                    "out_prefix",
                    ["fwhm-" + str(x) + "mm_" for x in self.parameters["smooth"]],
                ),
            ]
            smoothing_node.synchronize = True

            join_smoothing_node = npe.JoinNode(
                interface=nutil.Function(
                    input_names=["smoothed_normalized_files"],
                    output_names=["smoothed_normalized_files"],
                    function=dartel2mni_utils.join_smoothed_files,
                ),
                joinsource="smoothing_node",
                joinfield="smoothed_normalized_files",
                name="join_smoothing_node",
            )
            self.connect(
                [
                    (
                        dartel2mni_node,
                        smoothing_node,
                        [("normalized_files", "in_files")],
                    ),
                    (
                        smoothing_node,
                        join_smoothing_node,
                        [("smoothed_files", "smoothed_normalized_files")],
                    ),
                    (
                        join_smoothing_node,
                        self.output_node,
                        [("smoothed_normalized_files", "smoothed_normalized_files")],
                    ),
                ]
            )
        else:
            self.output_node.inputs.smoothed_normalized_files = []

        self.connect(
            [
                (
                    self.input_node,
                    unzip_tissues_node,
                    [("native_segmentations", "in_file")],
                ),
                (
                    self.input_node,
                    unzip_flowfields_node,
                    [("flowfield_files", "in_file")],
                ),
                (self.input_node, unzip_template_node, [("template_file", "in_file")]),
                (unzip_tissues_node, dartel2mni_node, [("out_file", "apply_to_files")]),
                (
                    unzip_flowfields_node,
                    dartel2mni_node,
                    [
                        (
                            (
                                "out_file",
                                dartel2mni_utils.prepare_flowfields,
                                self.parameters["tissues"],
                            ),
                            "flowfield_files",
                        )
                    ],
                ),
                (unzip_template_node, dartel2mni_node, [("out_file", "template_file")]),
                (
                    dartel2mni_node,
                    self.output_node,
                    [("normalized_files", "normalized_files")],
                ),
            ]
        )
