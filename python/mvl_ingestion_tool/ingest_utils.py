import os
import re
import shutil
import sys
from mvl_ingestion_tool.csvreader import CSVReader
from mvl_core_pipeline.logger import Logger
from mvl_core_pipeline.path_template import resolve_template


logger = Logger(name = "mvl_ingestion_tool", repo_name="mvl_ingestion_tool", level=10).get_logger()

def check_missing_frames(sequence):
    """
    Checks for missing frames in the given files and sequences.

    Args:
        sequence (list): List of image paths.

    Returns:
        bool: True if there is a missing frame, False otherwise.
    """
    frame_numbers = []
    for path in sequence:
        try:
            frame_number = int(os.path.splitext(os.path.basename(path))[0].split('_')[-1])
            frame_numbers.append(frame_number)
        except Exception as e:
            logger.error(f"Error extracting frame number from {os.path.basename(path)}: {e}")

    if not frame_numbers:
        return False

    frame_numbers.sort()
    missing = [f for f in range(frame_numbers[0], frame_numbers[-1] + 1) if f not in frame_numbers]
    if missing:
        logger.info(f"Missing frames: {missing}")
        return True
    return False

def mapping_scene_shots_util(mapping_file_path)->dict:
	"""
    Mappig module to adjust the scene and shot name from provided csv
	Returns:
        dict : mapping vlaues for new scene or shot names
	"""
	data  = {}
	cwd =  os.getcwd()
	reader_no_header = CSVReader(mapping_file_path)
	reader_no_header.read_csv(skip_header=False)
	
	first_column_mapping_no_header = reader_no_header.create_dictionary_mapping(skip_header=False)
	for key, values in first_column_mapping_no_header.items():
		data[key] = values
	return data

def copy_files(files, dest):
    """
    Copy files to destination

    Args:
        files: list of file paths

    """  
    for file_path in files:
        try:
            base_name, extension = os.path.splitext(os.path.basename(file_path))
            if validate_path(dest):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(file_path, dest)
                logger.info(f"Copied file: {os.path.basename(file_path)} to {dest}")
        except Exception as e:
            logger.error(f"Error copying file {os.path.basename(file_path)}: {e}")
            sys.exit(1)

def copy_sequence(sequences, dest, force_copy= False):
    """
    Copy Sequence to the dest 
    Args:
        sequences: list for file paths which makes a sequence
        dest : str path for out dir
    """
    
    for seq in sequences:
        
        sorted_paths = sorted(seq['paths'], key=lambda path: int(os.path.splitext(os.path.basename(path))[0].split('_')[-1]))
        is_frame_missing = check_missing_frames(sorted_paths)
        if is_frame_missing and not force_copy:
            continue
        
        frame_counter = 1001
        for path in sorted_paths:
            if path is None:
                logger.error("Warning: Encountered a None path in the sequence.")
                continue  # Skip to the next iteration
            try:
                base_name, extension = os.path.splitext(os.path.basename(path))
                output_path = resolve_out_path(
                                source=path,
                                project="your_project",           # replace with your project variable
                                sequence_code="your_sequence",    # replace with your sequence variable
                                shot_code="your_shot",            # replace with your shot variable
                                task="your_task",                 # replace with your task variable
                                dest=dest,
                                frame_counter=frame_counter,
                                dcc="nuke",                       # or your DCC variable
                                ext=extension,
                                base_dir="work/sequences"
                            )
                if output_path:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    shutil.copy2(path, os.path.join(output_path))
                    print(f"Copied sequence file: {os.path.basename(path)} to {os.path.join(dest, os.path.basename(path))}")
                    frame_counter += 1
            except Exception as e:
                error_msg = f"Error copying sequence file {os.path.basename(path)}: {e}"


def get_files_and_sequences(source):
    """
    Scans a directory for individual files and numbered image sequences.

    Args:
        source (str): Path to the directory.

    Returns:
        tuple:
            - files (list of str): List of individual file paths.
            - sequences (list of dict): List of dictionaries describing sequences:
                {
                    'base_name': str,
                    'padding': int,
                    'start': int,
                    'end': int,
                    'extension': str,
                    'paths': list of str
                }
    """
    files = []
    sequences = []
    processed_files = set()
    
    # Matches: name_####.ext (underscore is optional)
    sequence_regex = re.compile(r"^(.+?)[._](\d+)\.([a-zA-Z0-9]+)$")

    all_items = sorted(os.listdir(source))
    
    for item in all_items:
        item_path = os.path.join(source, item)
        if not os.path.isfile(item_path) or item_path in processed_files:
            continue

        match = sequence_regex.match(item)
        if match:
            base_name, frame_number_str, extension = match.groups()
            padding = len(frame_number_str)
            frame_number = int(frame_number_str)

            sequence_files = []
            start_frame = end_frame = frame_number

            for other_item in all_items:
                other_path = os.path.join(source, other_item)
                if not os.path.isfile(other_path) or other_path in processed_files:
                    continue

                other_match = sequence_regex.match(other_item)
                if (other_match and
                    other_match.group(1) == base_name and
                    other_match.group(3).lower() == extension.lower() and
                    len(other_match.group(2)) == padding):
                    
                    seq_frame = int(other_match.group(2))
                    sequence_files.append(other_path)
                    processed_files.add(other_path)
                    start_frame = min(start_frame, seq_frame)
                    end_frame = max(end_frame, seq_frame)

            if len(sequence_files) > 1:
                sequences.append({
                    'base_name': base_name,
                    'padding': padding,
                    'start': start_frame,
                    'end': end_frame,
                    'extension': extension,
                    'paths': sorted(sequence_files)
                })
            else:
                files.append(item_path)
        else:
            files.append(item_path)

    return files, sequences


def validate_path(path):
    if not dir:
        logger.error(f"Not a valid path {path}.")
        return False
    if not os.path.isdir(path):
        logger.error(f"directory does not exist: {path}")
        return False
    if not os.access(path, os.W_OK):
        logger.error(f"directory is not writable: {path}")
        return False
    
    logger.info(f"directory is valid: {path}")
    return True

def resolve_out_path(source, project, sequence_code, shot_code, task, dest,  frame_counter, step, ext=".exr", base_dir= "work/sequences"):
    """
    Constructs the output path for a file using the given tokens and padding.
    base_path: "{project_root}/work/sequences/{sequence}/{shot}/{step}/{task}/{user}/{dcc}/{name}"
    Args:
        sequence (str): Sequence name or number.
        shot (str): Shot name or number.
        task (str): Task name (e.g., 'comp', 'lighting').
        dcc (str): DCC name (e.g., 'maya', 'nuke').
        name (str): Base name for the file (should include frame with padding if needed).
        ext (str): File extension (with or without dot).
        base_dir (str): Base directory for output (default: 'work/sequences').

    Returns:
        str: The constructed output file path.
    """

    
    name, ext = os.path.splitext(os.path.basename(source))

    resolved_name = f"{project}_{sequence_code}_{shot_code}_{task}_{dcc}_{name}"
    try:
        tokens = {
            'project_root': f"{os.path.join(dest, project)}",
            'sequence': sequence_code,
            'shot': shot_code,
            'task':  task,
            'step': step,
            'name': resolved_name
        }

        resolved_path = resolve_template('shots_workfile', tokens)
        return resolved_path
    except Exception as e:
        logger.info(f"fail to resove path template with tokens: {tokens}")
        sys.exit(1)
    


   