import os
import sys
import argparse
import re
import datetime
import shutil
import io
import pandas as pd

from enum import Enum, unique
import subprocess
from mvl_core_pipeline.context import Context
from mvl_core_pipeline.logger import Logger
from mvl_core_pipeline.path_template import resolve_template
from mvl_ingestion_tool.ingest_utils import (validate_path, get_files_and_sequences,
											 copy_files, copy_sequence)
from mvl_core_pipeline.fig import Fig, YAMLConfigDriver

from mvl_ingestion_tool.csvreader import CSVReader
from mvl_ingestion_tool.ingest_utils import check_missing_frames
from mvl_make_dailies.movie_commands import create_movie_from_sequence

logger = Logger(name = "mvl_ingestion_tool", repo_name="mvl_ingestion_tool", level=10).get_logger()

@unique
class INGESTIONPROCESS(Enum):
    INGEST = 1
    EGRESS = 2

class IngestionHandler():

	def __init__(self, args):
		# Support both dict and argparse.Namespace
		if isinstance(args, dict):
			args = argparse.Namespace(**args)

		self.args = args
		self.ctx = Context.from_environment()

		self.resolved_project =  args.project if args.project is not None else self.ctx.project
		self.resolved_vendor = args.vendor
		self.resolved_date = args.input_date
		self.resolved_scene = args.scene if args.scene is not None else self.ctx.container
		self.resolved_shot = args.shot if args.shot is not None else self.ctx.scope

		# If input is directly provided, use that
		if self.resolved_source:
			self.resolved_source = args.input
		# Otherwise, construct path from project/vendor/date
		elif args.project and args.vendor and args.input_date:
			self.resolved_source = self._construct_source_path(
                project= self.resolved_project,
                vendor= self.resolved_vendor,
                date= self.resolved_date,
				scene= self.resolved_scene,
				shot = self.resolved_shot
            )
		else:
			raise ValueError("Either --input or all of --project, --vendor, and --input_date must be provided.")

		self.resolved_out_dir = self._construct_out_path(
			project=self.resolved_project,
			scene = self.resolved_scene,
			shot = self.resolved_shot,
		)
		self.resolved_proxy_ext= args.proxy
		self.resolved_resolution= args.resolution
		self.is_force_ingestion= args.force

	def _construct_out_path(self, project,scene, shot):
		"""
		Construct the destination path
		Args:
			project(str): project from the context
			scene(str) : scene from the context
			shot(str): shot from the context
		"""
		from mvl_core_pipeline.path_template import resolve_template
		#base_path: "{project_root}/{repo}/sequences/{sequence}/{shot}"
		tokens = {
			'project_root': f'j:/{project}',
			'repo':'repo',
			'sequence':scene,
			'shot':shot,
		}

		constructed_path = resolve_template("base_path", "shots:publish", tokens)
		if not os.path.exists(constructed_path):
			os.mkdirs(constructed_path)

		logger.info(f"destination path constructed : {constructed_path}")
		
		return constructed_path

	
	def _construct_source_path(self, project, vendor, date, scene, shot):
		"""
		Construct the source path based on project/vendor/input_date
		Example path: /mnt/projects/<project>/<vendor>/<YYYYMMDD>/
		"""
		try:
			date_obj = datetime.strptime(self.resolved_date, "%Y-%m-%d")
			date_str = date_obj.strftime("%Y%m%d")
		except ValueError:
			raise ValueError("input_date must be in YYYY-MM-DD format.")
		
		cfg = Fig('mvl_ingestion', "path_template", YAMLConfigDriver())
		tokens = {
			'project_root': f'j:/{project}',
			'vendor':vendor,
			'date':date,
			'scene': scene,
			'shot': f"{scene}_{shot}"
		}

		ingest_workspace = cfg['template']['ingest_workspace']
		constructed_path = ingest_workspace.format(**tokens)

		if not os.path.exists(constructed_path):
			raise FileNotFoundError(f"Constructed source path does not exist: {constructed_path}")
		
		logger.info(f"source path constructed : {constructed_path}")

		return constructed_path

	def run(self):
		"""
		Processes folders, gets all files and file sequences and ingest.
		"""
		if os.path.isfile(self.resolved_source):
			copy_files([self.resolved_source], self.resolved_out_dir)
		elif os.path.isdir(self.resolved_source):
			files, sequences = get_files_and_sequences(self.resolved_source)

			if len(files):
				copy_files(files, self.resolved_out_dir)
			if len(sequences):
				copy_sequence(sequences, self.resolved_out_dir)
			
	def parse_filename(self, filename):
		"""Parses the filename and returns the extracted information."""
		pattern = r"^(i|O)_([A-Za-z0-9]+)_(\d+-\d+)(?:_([A-Za-z0-9]+))?_v(\d+)$"
		match = re.match(pattern, filename)

		if match:
			io, project, scene_shot, optional, version = match.groups()
			return {
				"io": io,
				"project": project,
				"scene_shot": scene_shot,
				"optional": optional,
				"version": version,
			}
		else:
			return None

	def generate_output_path(self, base_name, frame_number, extension):
		"""Generates the output file path based on the specified naming convention."""
		#parsed_info = self.parse_filename(base_name
		for key in self.data.keys():
			if self.data.get("scene") in key or self.data.get("shot") in key:
				shot = self.data[key][0].split('_')[-1]
				break

		frame_str = str(frame_number).zfill(4)  # Pad frame number with leading zeros
		output_filename = self.generate_new_filename(frame_str, extension)

		output_path = os.path.join(self.resolved_destination, self.resolved_project, f"SC_{self.resolved_scene}", f"SH_{self.resolved_scene_shot}", "plates")
		if self.data.get("take"):
			output_path = os.path.join(output_path, self.data.get("take"))
		output_path = os.path.join(output_path, output_filename)
		return output_path
	
	def generate_new_filename(self, frame, ext):
		"""
		Generates a new filename based on the provided file information.

		Args:
			file_info (dict): A dictionary containing file information.

		Returns:
			str: The new filename.
		"""

		filename_placeholder = "{sceneshot}_{type}_{camera}_{take}_f{resolution}_{frame_number}{ext}"
 
		for key in self.data.keys():
			if self.data.get("scene") in key or self.data.get("shot") in key:
				csv_data = self.data[key]
				break

		file_data = {
			#"job": self.data.get('project', "gen63"),
			"sceneshot": csv_data[0],
			"type":csv_data[1],
			"resolution": self.data['resolution'],
			"frame_number": frame,
			"ext": ext,
		}

		filename = filename_placeholder.format(**file_data)
		return filename

	def display_results(self, files, sequences):
		"""
		Displays the identified files and sequences.
		Args:
			files (list): A list of individual file paths.
			sequences (list): A list of dictionaries representing file sequences.
		"""

		if files:
			for file_path in files:
				print(f"  - {file_path}")
			else:
				print("  No individual files found.")

			print("\nIdentified File Sequences:")
			if sequences:
				for seq in sequences:
					print(f"  - Base Name: {seq['base_name']}.{'#' * seq['padding']}.{seq['extension']}")
					print(f"    Frame Range: {seq['start']} - {seq['end']}")
					print(f"    Total Frames: {seq['end'] - seq['start'] + 1}")
				else:
					print("  No file sequences found.")

	def create_mov_from_exrs(exr_sequence_path, mov_path):
		"""
		Creates a MOV video from a sequence of EXR images using Gaffer.

		Args:
			exr_sequence_path (str): The path to the EXR sequence (e.g., /path/to/image.%04d.exr).
			mov_path (str): The path to save the MOV video.
			fps (int, optional): Frames per second for the MOV video. Defaults to 24.
			display_window (IECore.Box2i, optional): The display window to use.
			data_window (IECore.Box2i, optional): The data window to use.
			channels (list of str, optional): The channels to include in the MOV.
		"""
		data = {'input': exr_sequence_path, 'output': mov_path}
		create_movie_from_sequence(data)

	def generate_proxy_from_exr_using_convert(input_path, output_path, format):
		"""
		Generates an image file (JPEG or PNG) from an EXR file using OpenImageIO.

		Args:
			input_path (str): Path to the input EXR file.
			output_path (str): Path to save the generated image file.
			format (str): The desired output image format (jpeg or png).
		"""
		# TODO
		# format = format.lower()
		# if format not in ["jpeg", "png"]:
		# 	log.error(f"Error: Unsupported output image format: {format}. Please use 'jpeg' or 'png'.")
		# 	return

		# try:
		# 	# Construct the OpenImageIO command for EXR to image conversion
		# 	command = [
		# 		"openimageio",
		# 		"convert",
		# 		input_path,
		# 		"-o",
		# 		output_path,
		# 		"-format",
		# 		format,
		# 		# Add other OpenImageIO options as needed, e.g., exposure, tone mapping
		# 		# Example for setting exposure:
		# 		# "-e", "0.5",
		# 		# Example for using a specific tone mapping operator:
		# 		# "-tonemap", "aces",
		# 	]

		# 	log.info(f"Running OpenImageIO command: {' '.join(command)}")
		# 	subprocess.run(command, check=True, capture_output=True)
		# 	log.info(f"Successfully generated image: {output_path}")

		# except FileNotFoundError:
		# 	log.info("Error: OpenImageIO command not found. Make sure it's in your system's PATH.")
		# except subprocess.CalledProcessError as e:
		# 	log.error(f"Error generating image with OpenImageIO:")
		# 	log.info(f"Command: {' '.join(e.cmd)}")
		# 	log.info(f"Return Code: {e.returncode}")
		# 	log.info(f"Stdout: {e.stdout.decode()}")
		# 	log.info(f"Stderr: {e.stderr.decode()}")
		# except Exception as e:
		# 	log.error(f"An unexpected error occurred: {e}")

def parse_arguments():
	"""
	Parses command-line arguments.
	"""
	parser = argparse.ArgumentParser(
		description="""
		A file browser with the ability to preview
		images and caches using Gaffer's viewers. This
		is the same as the Browser panel from the main
		gui application, but running as a standalone
		application.
		"""
	)

	parser.add_argument(
		"--input",
		type=str,
		help="The source directory to process.",
	)
	parser.add_argument(
		"--output",
		type=str,
		help="The Out dir to inget the data for further processing within pipeline.",
	)
	parser.add_argument(
		"--project",
		type=str,
		help="The name of the project.",
		default="gen63",
	)
	parser.add_argument(
		"--input_date",
		type=str,
		help="Date in YYYYMMDD format.",  # Changed format to be more standard
		required=True,
	)
	parser.add_argument(
		"--data_type",
		type=str,
		help="Search for specific file types (e.g., exr, jpg).",
		default="exr",
	)
	parser.add_argument(
		"--mov",
		action="store_true",
		help="Generate MOV files from exr.",
		default=False,
	)
	parser.add_argument(
		"--process",
		type=int,
		choices=[0, 1],
		help="1: Ingest, 0: Egress (not yet implemented).",
		default=1,
	)
	parser.add_argument(
		"--vendor",
		type=str,
		help="Optional: Vendor name to look into vendor or vendor/date directory.",
		default="",
		required=True,
	)
	parser.add_argument(
		"--hires",
		action="store_true",
		help="High resolution exrs.",
		default=False,
	)
	parser.add_argument(
		"--camera",
		type=str,
		help="Camera name.",
		default="",
	)
	parser.add_argument(
		"--take",
		type=str,
		help="Take number.",
		default="",
	)
	parser.add_argument(
		"--resolution",
		type=str,
		help="Resolution (e.g., 4448x3096).",
		default="4448x3096",
	)
	parser.add_argument(
		"--force",
		action="store_true",
		help="Force ingestion.",
		default=False,
	)
	parser.add_argument(
		"--proxy",
		type=str,
		help="Create a proxy file with the specified format (e.g., jpeg, png).",
		metavar="FORMAT",
	)
	parser.add_argument(
		"--scene",
		type=str,
		help="specify the scene name (e.g., SC_48).",
		metavar="FORMAT",
	)
	parser.add_argument(
		"--shot",
		type=str,
		help="specify the shot name (e.g., SH_14).",
		metavar="FORMAT",
	)

	args = parser.parse_args()
	return vars(args)

def run_ingest():
	args = parse_arguments()
	processor = IngestionHandler(args)
	processor.run()

if __name__=="__main__":
    run_ingest()




