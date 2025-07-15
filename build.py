import sys
import os
from mvl_rez_package_builder import python_builder

if __name__ == '__main__':
    pckg_builder = python_builder.PythonBuilder(
        source_path=os.environ['REZ_BUILD_SOURCE_PATH'],
        build_path=os.environ['REZ_BUILD_PATH'],
        install_path=os.environ['REZ_BUILD_INSTALL_PATH'],
        directory_list=["python", "bin", "configs"]
    )
    pckg_builder.build()

    targets = sys.argv[1:]

    if "install" in targets:
        pckg_builder.install()