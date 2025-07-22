
import argparse
from mvl_ingestion.ingestion_processor import MVLIngestionProcessor
from mvl_ingestion.ingestion_utils import logger, ingestion_args, get_supported_proxy_resolutions


def add_arguments_from_keys(parser, keys):
    type_map = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool
    }

    for arg in keys:
        arg = arg.copy()  # so you don't mutate the input
        name = arg.pop("name")

        try:
            # Convert "type" string to callable
            if "type" in arg and isinstance(arg["type"], str):
                arg["type"] = type_map[arg["type"].strip().lower()]
            if "type" in arg and isinstance(arg['type'], float):
                logger.info(f"add_arguments_from_keys float type {arg['type']} for node {name}")
                
            parser.add_argument(name, **arg)
        except KeyError as e:
            logger.error(f"Invalid type in argument '{name}': {e}")
        except Exception as e:
            logger.error(f"Failed to add argument '{name}': {e}")
            
def parse_arguments():
	"""
	Parses command-line arguments for the file browser application.
	"""
	parser = argparse.ArgumentParser(
		description="""
			MVL Ingestion Tool - Command-line utility to ingest files or image sequences (e.g. EXRs)
			from vendor deliveries into the pipeline's organized project structure.

			This tool can:
			- Copy raw assets (files or sequences) into their resolved destination folder
			- Resolve paths based on project, scene, shot, and vendor
			- Generate MOV files from EXRs
			- Create proxy images in JPEG/PNG format
			- Handle contextual fallback using environment variables or CLI inputs

			Use --input to specify a direct path, or --project, --vendor, and --input_date
			to auto-resolve source paths.

			Example:
			ingest --project gen63 --vendor from_da --input_date 2025-07-15 --scene SC_48 --shot SH_14
		"""
	)
     
	add_arguments_from_keys(parser, ingestion_args())
	parser.add_argument(
		"--proxy-res",
		choices= get_supported_proxy_resolutions(),
		help=f"Preset resolution name from YAML. Options: {', '.join(get_supported_proxy_resolutions())}"
	)
	args = parser.parse_args()
	return args

def main():
	args = parse_arguments()
    
	logger.info(f"args : {args}")
	processor = MVLIngestionProcessor(args)
	processor.execute()

if __name__=="__main__":
    main()




