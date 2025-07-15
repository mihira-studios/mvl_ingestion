from fastapi import FastAPI, HTTPException
from pathlib import Path
import os
from typing import List, Dict

app = FastAPI()

def list_files_in_directory(directory_path: str) -> List[Dict[str, str]]:
    """
    Lists files in a directory, returning a list of dictionaries.  Handles errors.

    Args:
        directory_path: The path to the directory to list.

    Returns:
        A list of dictionaries, where each dictionary represents a file or directory.
        Each dictionary contains:
            - "name": The name of the file or directory.
            - "type": "file" or "directory".
            - "path": The full path to the file or directory.
        Returns an empty list if the directory is empty, does not exist, or if there is an error.
    """
    files = []
    try:
        # Use Path for more robust path handling
        path = Path(directory_path)

        print (f"path: {path}")
        # Check if the path exists and is a directory
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory_path}")

        # Use os.scandir for better performance and more information
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.is_file():
                    files.append({
                        "name": entry.name,
                        "type": "file",
                        "path": str(Path(directory_path, entry.name).resolve()), # Resolve for absolute path
                    })
                elif entry.is_dir():
                    files.append({
                        "name": entry.name,
                        "type": "directory",
                        "path": str(Path(directory_path, entry.name).resolve()), # Resolve for absolute path
                    })
    except (FileNotFoundError, NotADirectoryError) as e:
        # Log the error (optional, but recommended for debugging)
        print(f"Error: {e}")
        #  Don't return the error message directly in the response,
        #  but you could raise an HTTPException with a 404 or 500 status
        #  if you want the API to return a specific error code.
        #  For this example, I'll return an empty list, but you might
        #  want to handle this differently in a production environment.
        return []  # Return an empty list in case of error, or raise an exception
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

    return files


# TODO needs to be updated with the fastapi calls
tasks  = { "Tasks" : 
    {
    "description": "Vfx tasks",
    "children": {
    "Composition": {
        "description": "Combining multiple visual elements into a single image or sequence.",
        "aliases": ["Comp", "Compositing"]
    },
    "Matchmove": {
        "description": "Tracking camera or object motion for compositing.",
        "aliases": ["Camera Tracking", "Object Tracking"]
    },
    "Nuke": {
        "description": "General Nuke scripts and projects.",
        "aliases": ["Generic Nuke", "Nuke Scripts"]
    },
    "Lighting": {
        "description": "Creating and manipulating light sources in 3D scenes.",
        "aliases": ["Light", "Lighting Setup"]
    },
    "Animation": {
        "description": "Creating movement and performance of 3D characters or objects.",
        "aliases": ["Anim"]
    },
    "Modeling": {
        "description": "Creating 3D models of characters, environments, and props.",
        "aliases": ["Model", "3D Modeling"]
    },
    "Rendering": {
        "description": "Generating 2D images from 3D scenes.",
        "aliases": ["Render", "Image Rendering"]
    },
    "Texturing": {
        "description": "Creating and applying surface textures to 3D models.",
        "aliases": ["Texture", "Surface Texturing"]
    },
    "Rigging": {
        "description": "Creating control systems for 3D models for animation.",
        "aliases": ["Rig", "Character Rigging"]
    },
    "FX": {
        "description": "Creating visual effects such as explosions, fire, and smoke.",
        "aliases": ["Effects", "Visual Effects"]
    },
    "Layout": {
        "description": "Setting up the initial camera and object placement in a 3D scene.",
        "aliases": ["Scene Layout", "Previs"]
    },
    "Rotoscoping": {
        "description": "Manually tracing over live-action footage.",
        "aliases": ["Roto"]
    },
    "Paint": {
        "description": "Removing unwanted elements or repairing footage.",
        "aliases": ["Cleanup"]
    },
    "Color Grading":{
        "description": "Adjusting the color and tone of footage.",
        "aliases": ["Color", "Colour"]
    },
    "Editorial":{
        "description": "Editing and assembling footage.",
        "aliases": ["Edit"]
    },
    "Previsualization":{
        "description":"Creating a rough version of the final product",
        "aliases": ["Previs"]
    }
    }
    }
}

# Dummy data for Marvel characters

Assets = {'Assets': {'description': 'Marvel character assets','children': {} } , 'Shots': {'description': 'Marvel character shots','children': {} }}

Assets['Assets']['children'] = {
    "Iron_Man": {
        "path": "/assets/Iron_Man"
    },
    "Captain_America": {
        "path": "/assets/Captain_America"
    },
    "Thor": {
        "path": "/assets/Thor"
    },
    "Hulk": {
        "path": "/assets/Hulk"
    },
    "Black_Widow": {
        "path": "/assets/Black_Widow"
    },
}

Assets['Shots']['children'] = {
    "SC_48": {
        "description": "MVL character shots",
        "children":{
            "SH_0160": {"old_shot": "14", "new_shot": "0160", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0160"},
            "SH_0270": {"old_shot": "21", "new_shot": "0270", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0270"},
            "SH_0300": {"old_shot": "22", "new_shot": "0300", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0300"},
            "SH_0310": {"old_shot": "26", "new_shot": "0310", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0310"},
            "SH_0380": {"old_shot": "32", "new_shot": "0380", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0380"},
            "SH_0380_ball": {"old_shot": "32ball", "new_shot": "0380", "naming": "_chrome_ball_v001", "renamed": "GEN63_SC_48_SH_0380"},
            "SH_0380_empty": {"old_shot": "32empty", "new_shot": "0380", "naming": "_clean_plate_v001", "renamed": "GEN63_SC_48_SH_0380"},
            "SH_0390": {"old_shot": "33", "new_shot": "0390", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0390"},
            "SH_0400": {"old_shot": "34", "new_shot": "0400", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0400"},
            "SH_0410": {"old_shot": "35", "new_shot": "0410", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0410"},
            "SH_0410_ref-1": {"old_shot": "35ref-1", "new_shot": "0410", "naming": "_ref_v001", "renamed": "GEN63_SC_48_SH_0410"},
            "SH_0410_ball": {"old_shot": "35ball", "new_shot": "0410", "naming": "_chrome_ball_v001", "renamed": "GEN63_SC_48_SH_0410"},
            "SH_0410_02": {"old_shot": "35_02", "new_shot": "0410", "naming": "_main_plate_v002", "renamed": "GEN63_SC_48_SH_0410"},
            "SH_0420_A_02": {"old_shot": "35A_02", "new_shot": "0420", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0420"},
            "SH_0420_Aref-1": {"old_shot": "35Aref-1", "new_shot": "0420", "naming": "_ref_v001", "renamed": "GEN63_SC_48_SH_0420"},
            "SH_0420_Aref-1_02": {"old_shot": "35Aref-1_02", "new_shot": "0420", "naming": "_ref_v002", "renamed": "GEN63_SC_48_SH_0420"},
            "SH_0420_Aref-1_03": {"old_shot": "35Aref-1_03", "new_shot": "0420", "naming": "_ref_v003", "renamed": "GEN63_SC_48_SH_0420"},
            "SH_0440_Aref-1": {"old_shot": "35Aref-1", "new_shot": "0440", "naming": "_ref_v001", "renamed": "GEN63_SC_48_SH_0440"},
            "SH_0450": {"old_shot": "37", "new_shot": "0450", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0450"},
            "SH_0450_02": {"old_shot": "37_02", "new_shot": "0450", "naming": "_chrome_ball_v001", "renamed": "GEN63_SC_48_SH_0450"},
            "SH_0470": {"old_shot": "39", "new_shot": "0470", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0470"},
            "SH_0470_ref-1": {"old_shot": "39ref-1", "new_shot": "0470", "naming": "_ref_v001", "renamed": "GEN63_SC_48_SH_0470"},
            "SH_0480_ball": {"old_shot": "40ball", "new_shot": "0480", "naming": "_chrome_ball_v001", "renamed": "GEN63_SC_48_SH_0480"},
            "SH_0480_ball_02": {"old_shot": "40ball_02", "new_shot": "0480", "naming": "_chrome_ball_v002", "renamed": "GEN63_SC_48_SH_0480"},
            "SH_0490": {"old_shot": "41", "new_shot": "0490", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0490"},
            "SH_0500": {"old_shot": "42", "new_shot": "0500", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0500"},
            "SH_0500_ref-1": {"old_shot": "42ref-1", "new_shot": "0500", "naming": "_ref_v001", "renamed": "GEN63_SC_48_SH_0500"},
            "SH_0510": {"old_shot": "43", "new_shot": "0510", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0510"},
            "SH_0510_ref-1": {"old_shot": "43ref-1", "new_shot": "0510", "naming": "_ref_v001", "renamed": "GEN63_SC_48_SH_0510"},
            "SH_0510_ball": {"old_shot": "43ball", "new_shot": "0510", "naming": "_chrome_ball_v001", "renamed": "GEN63_SC_48_SH_0510"},
            "SH_0530_A": {"old_shot": "45A", "new_shot": "0530", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0530"},
            "SH_0530_Aref": {"old_shot": "45Aref", "new_shot": "0530", "naming": "_ref_v001", "renamed": "GEN63_SC_48_SH_0530"},
            "SH_0540_B": {"old_shot": "45B", "new_shot": "0540", "naming": "_main_plate_v001", "renamed": "GEN63_SC_48_SH_0540"},
            "SH_0540_Bref": {"old_shot": "45Bref", "new_shot": "0540", "naming": "_ref_v001", "renamed": "GEN63_SC_48_SH_0540"},
        }
    }
}


@app.get("/assets/", response_model=Dict[str, Dict])
async def get_marvel_assets():
    """
    Returns the Marvel character assets as JSON.
    """
    return Assets

@app.get("/tasks/", response_model=Dict[str, Dict])
async def get_tasks():
    """
    Returns the tasks.
    """
    return tasks

@app.get("/files/")
async def read_directory(dir_path: str = "."):
    """
    Reads the contents of a directory and returns a list of files and subdirectories.

    Args:
        dir_path: The path to the directory to read.  Defaults to the current directory.
                   The path is relative to the server's current working directory.

    Returns:
        A JSON response containing a list of dictionaries, where each dictionary
        represents a file or subdirectory.  Each dictionary contains the keys:
            - "name": The name of the file or directory.
            - "type": "file" or "directory".
            - "path": The absolute path to the file or directory.

    Raises:
        HTTPException:
            - 400: If the provided path is not a directory.
            - 404: If the provided path does not exist.
            - 500: For other unexpected errors.

    Examples:
        - To list files in the current directory:
            /files/
        - To list files in a subdirectory named "data":
            /files/?dir_path=data
        - To list files in a directory located at "/tmp/my_data":
            /files/?dir_path=/tmp/my_data
    """
    try:
        files = list_files_in_directory( os.path.join( "J:", dir_path))
        if not files:
             raise HTTPException(status_code=404, detail="Directory not found or empty")
        return files
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
        #  Important:  Log the error here.  Don't just send the raw error
        #  to the client in a production environment.  Use a proper
        #  logging library (e.g., `import logging`) to record the error.
        #  Example (replace print with logging):
        #  logging.exception("Unexpected error while reading directory")

@app.get("/vendors/")
async def read_vendors(dir_path: str = "."):
    """
    Reads the contents of a vendor directory and returns a list of vendor subdirectories.

    Args:
        dir_path: The path to the directory to read. Defaults to the current directory.
                  The path is relative to the server's current working directory.

    Returns:
        A JSON response containing a list of dictionaries, where each dictionary
        represents a vendor subdirectory. Each dictionary contains the keys:
            - "name": The name of the vendor directory.
            - "type": "directory".
            - "path": The absolute path to the vendor directory.

    Raises:
        HTTPException:
            - 400: If the provided path is not a directory.
            - 404: If the provided path does not exist.
            - 500: For other unexpected errors.
    """
    try:
        # Use the same logic as `list_files_in_directory` but filter for directories only
        vendors = list_files_in_directory(os.path.join("J:", dir_path))
        vendor_directories = [v for v in vendors if v["type"] == "directory"]

        if not vendor_directories:
            raise HTTPException(status_code=404, detail="No vendor directories found or directory is empty")

        return vendor_directories
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.get("/dates/")
async def read_dates(dir_path: str = "."):
    """
    Reads the contents of a date directory and returns a list of date subdirectories.

    Args:
        dir_path: The path to the directory to read. Defaults to the current directory.
                  The path is relative to the server's current working directory.

    Returns:
        A JSON response containing a list of dictionaries, where each dictionary
        represents a date subdirectory. Each dictionary contains the keys:
            - "name": The name of the date directory.
            - "type": "directory".
            - "path": The absolute path to the date directory.

    Raises:
        HTTPException:
            - 400: If the provided path is not a directory.
            - 404: If the provided path does not exist.
            - 500: For other unexpected errors.
    """
    try:
        # Use the same logic as `list_files_in_directory` but filter for directories only
        dates = list_files_in_directory(os.path.join("J:", dir_path))
        date_directories = [d for d in dates if d["type"] == "directory"]

        if not date_directories:
            raise HTTPException(status_code=404, detail="No date directories found or directory is empty")

        return date_directories
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.get("/ingest_types/")
async def read_ingest_types(dir_path: str = "."):
    """
    Reads the contents of an ingest type directory and returns a list of ingest type subdirectories.

    Args:
        dir_path: The path to the directory to read. Defaults to the current directory.
                  The path is relative to the server's current working directory.

    Returns:
        A JSON response containing a list of dictionaries, where each dictionary
        represents an ingest type subdirectory. Each dictionary contains the keys:
            - "name": The name of the ingest type directory.
            - "type": "directory".
            - "path": The absolute path to the ingest type directory.

    Raises:
        HTTPException:
            - 400: If the provided path is not a directory.
            - 404: If the provided path does not exist.
            - 500: For other unexpected errors.
    """
    
    ingest_types_data = {
            "Ingest Types": {
                "description": "VFX ingest types",
                "children": {
                    "Plate": {
                        "description": "VFX plate ingest types",
                        "children": {
                            "Editorial": {"description": "Editorial plate ingest type", "children": {}}
                        }
                    },
                    "Editorial": {
                        "description": "VFX editorial ingest types",
                        "children": {}
                    }
                }
            }
        }

    return ingest_types_data
