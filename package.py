name = "mvl_ingestion"

version = "0.2.0"

requires = [
    "~python-3",
    "PyYAML-6",
]

private_build_requires = [
    "python-3",
    "mvl_core_pipeline",
    "mvl_rez_package_builder",
]

tools = [
    "ingest"
]

build_command = 'python {root}/build.py {install}'

def commands():
    env.PYTHONPATH.append("{root}/python")
    env.PATH.append("{root}/bin")

tests = {
    "unit":{
        "command": "python -m unittest discover -s tests",
        "requires": ["python-3"],
    }
}
