import logging
import os
from pathlib import Path
import subprocess
from os import path
from typing import List

from multiversx_sdk_cli import dependencies, errors, myprocess, utils
from multiversx_sdk_cli.projects.project_base import Project, rename_wasm_files

logger = logging.getLogger("ProjectCpp")


class ProjectCpp(Project):
    def __init__(self, directory: Path):
        super().__init__(directory)

    def perform_build(self):
        self.build_configuration = CppBuildConfiguration(self, self.debug)
        self.unit = self.find_file_globally("*.cpp")
        self.file_ll = self.unit.with_suffix(".ll")
        self.file_o = self.unit.with_suffix(".o")
        self.file_export = self.unit.with_suffix(".export")

        try:
            self._do_clang()
            self._do_llc()
            self._do_wasm()
        except subprocess.CalledProcessError as err:
            raise errors.BuildError(err.output)

    def _do_clang(self):
        logger.info("_do_clang")
        tool = path.join(self._get_llvm_path(), "clang-9")
        args = [
            tool,
            "-cc1", "-emit-llvm",
            "-triple=wasm32-unknown-unknown-wasm",
            "-ObjC++",
            "-std=c++17",
            "-nostdinc++",
            "-nobuiltininc",
            "-fno-builtin",
        ]
        if self.options.get("optimized", False):
            args.append("-Ofast")
        else:
            args.append("-O0")
        args.append(str(self.unit))
        myprocess.run_process(args)

    def _do_llc(self):
        logger.info("_do_llc")
        tool = path.join(self._get_llvm_path(), "llc")
        args = [tool]
        if self.options.get("optimized", False):
            args.append("-O3")
        else:
            args.append("-O0")
        args.extend(["-filetype=obj", self.file_ll, "-o", self.file_o])
        myprocess.run_process(args)

    def _do_wasm(self):
        logger.info("_do_wasm")
        tool = path.join(self._get_llvm_path(), "wasm-ld")
        args = [
            tool,
            "--no-entry",
            str(self.file_o),
            "-o", self.find_file_globally("*.cpp").with_suffix(".wasm"),
            "--strip-all",
            "--allow-undefined",
            "--demangle"
        ]

        if self.options.get("verbose", False):
            args.append("--verbose")

        for export in self.build_configuration.exports:
            args.append(f"-export={export}")

        myprocess.run_process(args)

    def _do_after_build_custom(self) -> List[Path]:
        source_file = self.find_file_globally("*.cpp")
        output_wasm_file = self._copy_to_output(source_file.with_suffix(".wasm"))
        os.remove(source_file.with_suffix(".wasm"))
        os.remove(source_file.with_suffix(".ll"))
        os.remove(source_file.with_suffix(".o"))
        
        paths = rename_wasm_files([output_wasm_file], self.options.get("wasm-name"))
        return paths

    def _get_llvm_path(self):
        return dependencies.get_module_directory("llvm")

    def get_dependencies(self):
        return ["llvm"]


class CppBuildConfiguration:
    def __init__(self, project: Project, debug):
        self.project = project
        self.debug = debug
        self.exports = self._get_exports()

    def _get_exports(self):
        file_export = self.project.find_file_globally("*.export")
        lines = utils.read_lines(file_export)
        return lines
