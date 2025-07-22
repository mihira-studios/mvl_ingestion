
import os
import re
import logging
from pathlib import Path
import coloredlogs

from mvl_ingestion.csv_file_reader import MVLCSVReader
from mvl_core_pipeline.logger import Logger
from mvl_core_pipeline.fig import Fig, YAMLConfigDriver
from mvl_core_pipeline.path_template import resolve_template


logger = Logger(name='movie_generator', repo_name='mvl_ingestion').get_logger()
logger.setLevel(logging.DEBUG)
coloredlogs.install(level='INFO', logger=logger)

def get_parser_config_template():
    fig = Fig('mvl_ingestion', 'parser_template', YAMLConfigDriver())
    return fig.get_config()['template']

def get_resolution_config_template():
    fig = Fig('mvl_ingestion', 'resolution_template', YAMLConfigDriver())
    return fig.get_config()['template']

def normalize(s):
    return s.strip().replace('\r', '').replace('\n', '')

def extract_scene_shot_from_path(file_base_name):
    parts = file_base_name.split("_")
    scene = parts[2] 
    shot  = f"{scene}/{parts[3]}"
    
    return scene, shot

def extract_resolution_from_path(file_path):
    """
    Extracts resolution from a file path (e.g., '4448x3096').

    Returns:
        str or None: The resolution string if found, else None.
    """
    parts = file_path.replace("\\", "/").split("/")
    for part in parts:
        if re.match(r"^\d{3,5}x\d{3,5}$", part):
            return part
    return None

def getNodeAtrribs(list_of_dicts)->list:
    attr = [d["name"].replace("--", "").replace('no-', "") for d in list_of_dicts if "name" in d]
    return attr

def get_parser_flags():
    """
    Returns a list of keys used for writer metadata in the Nuke template.
    These keys are used to extract writer related arguments from the command line arguments.
    """
    return getNodeAtrribs(get_parser_config_template()['args'])

def ingestion_args():
    """
    Retuns the dict to fill arg parser
    """
    return get_parser_config_template()['args']

def get_next_version(base_path):
    """
    Scan for existing version folders (v001, v002, ...) and return the next available version.
    """
    if not os.path.exists(base_path):
        return "v001"

    versions = []
    for item in os.listdir(base_path):
        match = re.match(r"v(\d{3})", item)
        if match:
            versions.append(int(match.group(1)))

    if versions:
        next_version = max(versions) + 1
    else:
        next_version = 1

    return f"v{next_version:03d}"  # Always 3 digits

def generate_sequence_output_paths(seq, metadata):

    current_scene = seq.get("scene")
    if not current_scene:	
        logging.error("No current scene found in the metadata.")
        return	

    current_shot = seq.get("shot")
    if not current_shot:	
        logging.error("No current shot found in the metadata.")
        return
    
    current_resolution = seq.get("resolution")
    if not current_resolution:	
        logging.error("No resolution found in the metadata.")
        
    	
    current_project = metadata.get("project")
    if not current_project:	
        logging.error("No current project found in the metadata.")
        return 	
    
    destination = metadata.get("output")
    if not destination:
        logging.error("No destination found in the metadata.")
        return
    
    mapping = read_csv(metadata.get('csv_path'))
    matching_key = None
    parts = None
    matching_key = None
    for key in mapping.keys():
        if current_scene in key:
            parts = key.split('/')
            if len(parts) != 2:
                continue
            if current_shot.strip() == key.strip():
                matching_key = key
                break

    if not matching_key:
        logging.error(f"generate_output_paths : No matching key found for scene {current_scene} and shot {current_shot}. \n Please check --csv_path for mapping.")
        exit(1)
    

    scene_shot_data, scene_shot_type = mapping.get(matching_key, [None, None])
    if not scene_shot_data or not scene_shot_type:
        logger.error(f"Invalid mapping for key: {matching_key}")
        return

    parts = scene_shot_type.strip('_').split('_')
    variant = parts[0] if parts else None
    product_type = parts[1] if len(parts) == 3 else ""
    version = parts[-1] if len(parts) >= 2 else None

    tokens = {
        "project_root": f"{destination}/{current_project}",
        "repo": "repo",
        "sequence": f"SC_{current_scene}",
        "shot": f"SH_{scene_shot_data.split('_')[-1]}",
    }

    base_path = resolve_template("path", "shots:publish:base_path", tokens)
    version = get_next_version(base_path=base_path)
    resolution = get_resolution_string(metadata.get('proxy_res', '2K_DCP'))

    output_paths = {}
    frame_counter = 1001

    plate_path = os.path.join(base_path, variant, product_type, version)
    proxy_path = os.path.join(base_path, variant, 'proxy', version, resolution)
    mov_path = os.path.join(base_path, variant, 'mov', version)

    plates_path = {}
    for src in sorted(seq['paths']):
        orig_filename = Path(src)
        filename = generate_out_filename(frame_counter, orig_filename.suffix, scene_shot_data, scene_shot_type, current_resolution)
        if filename:
            plates_path.update({src: os.path.join(plate_path, filename)})
        frame_counter += 1  

    output_paths = { 
        'plate_path': plates_path,
        'proxy_path': proxy_path,
        'movie_path': mov_path  
    }
    return output_paths
			
def generate_out_filename(frame, ext, sceneshot=None, type=None, resolution=None):
    """
    Generates a new filename based on the provided file information.

    Args:
        file_info (dict): A dictionary containing file information.

    Returns:
        str: The new filename.
    """

    filename_placeholder = "{sceneshot}_{type}_f{resolution}_{frame_number}{ext}"
    file_data = {
        "sceneshot": sceneshot,
        "type": type,
        "frame_number": frame,
        "resolution": resolution,
        "ext": ext,
    }

    filename = filename_placeholder.format(**file_data)
    return filename

def check_missing_frames(paths):
    """
    Checks for missing frames in the given files and sequences.

    Args:
        paths (list): list of file with frame numbers

    Returns:
        bool: True if there is a missing frame, False otherwise.
    """
    frame_numbers = []
    for path in paths:
        try:
            frame_number = int(os.path.splitext(os.path.basename(path))[0].split('_')[-1])
            frame_numbers.append(frame_number)
        except Exception as e:
            logging.info(f"Error extracting frame number from {os.path.basename(path)}: {e}")
    if not frame_numbers:
        logging.info(f"Could not find any frame numbers at path {path}")
        return True

    frame_numbers.sort()
    missing = [f for f in range(frame_numbers[0], frame_numbers[-1] + 1) if f not in frame_numbers]
    if missing:
        logging.info(f"frames missing: {missing}")
        return True

    return False

def get_files_and_sequences(root_dirs, scene=None, shot=None, resolution=None):
    """
    Reads a directory and identifies individual files and file sequences.
    Returns:
        tuple: A tuple containing two lists:
            - files (list): A list of individual file paths.
            - sequences (list): A list of dictionaries representing file sequences.
    """
    files = [] 
    sequences = []
    # Matches: basename_frame.ext (frame is one or more digits)
    sequence_regex = re.compile(r"^(.+?)_(\d+)\.([a-zA-Z0-9]+)$")

    if not isinstance(root_dirs, list):
        root_dirs = [root_dirs]

    for root_dir in root_dirs:
        all_items = sorted([os.path.join(root_dir, item) for item in os.listdir(root_dir)])
        # Group files by (base_name, extension, padding)
        seq_groups = {}
        for item_path in all_items:
            if os.path.isfile(item_path):
                match = sequence_regex.match(os.path.basename(item_path))
                if match:
                    base_name, frame_number_str, extension = match.groups()
                    padding = len(frame_number_str)
                    key = (base_name, extension, padding)
                    seq_groups.setdefault(key, []).append((int(frame_number_str), item_path))
                else:
                    files.append(item_path)
        # Now process the groups
        for (base_name, extension, padding), frames in seq_groups.items():

            if scene is None:
                scene,shot = extract_scene_shot_from_path(base_name)
                logger.info(f"scene {scene}, shot {shot} found!")

            if len(frames) > 1:
                frames_sorted = sorted(frames)
                sequence_files = [f[1] for f in frames_sorted]
                start_frame = frames_sorted[0][0]
                end_frame = frames_sorted[-1][0]
                sequences.append({
					'scene': scene,
					'shot': shot,
                    'base_name': base_name,
                    'padding': padding,
                    'start': start_frame,
                    'end': end_frame,
                    'extension': extension,
                    'paths': sequence_files,
					'resolution': resolution if resolution else extract_resolution_from_path(sequence_files[0])
                })
            else:
                # Only one file with this pattern, treat as single file
                files.append(frames[0][1])

    return files, sequences

def read_csv(csv_file_path):    
    mapping = None
    reader_no_header = MVLCSVReader(csv_file_path)
    reader_no_header.read_csv(skip_header=False)
    # Create mapping where the first column is the key (no header)
    mapping = reader_no_header.create_dictionary_mapping(skip_header=False)
    return mapping

def get_supported_proxy_resolutions():
    return getNodeAtrribs(get_resolution_config_template()['res'])

def get_resolution_string(res_name: str, fallback: str = "2048x1080"):
    res_config = get_resolution_config_template()
    resolutions = res_config.get("res", [])

    # First, check if it's a named preset like "2K (DCI)"
    for item in resolutions:
        if item["name"].lower() == res_name.lower():
            width, height = item["resolution"]
            return f"{width}x{height}"

    # If not a preset, try parsing "1920x1080"-like input
    if "x" in res_name.lower():
        try:
            width, height = map(int, res_name.lower().split("x"))
            return f"{width}x{height}"
        except ValueError:
            pass  # fall through to fallback

    # Fallback resolution
    try:
        width, height = map(int, fallback.lower().split("x"))
        return f"{width}x{height}"
    except Exception:
        raise ValueError(f"Unsupported resolution: {res_name}")


 