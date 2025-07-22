import os
import sys
import re
import logging
import datetime
import shutil
import pandas as pd
from enum import Enum, unique
import subprocess
import concurrent.futures
import logging
import argparse


from mvl_core_pipeline.fig import Fig, YAMLConfigDriver
from mvl_core_pipeline.context import Context

from mvl_ingestion.ingestion_operations import ProxyGenerationOperation, CopyFileOperation, MovGenerationOperation

from mvl_ingestion.ingestion_utils import check_missing_frames
from mvl_ingestion.ingestion_builder import SequenceBuilder
from mvl_ingestion.ingestion_utils import get_files_and_sequences
from mvl_ingestion.ingestion_utils import logger

@unique
class INGESTIONPROCESS(Enum):
    INGEST = 1
    EGRESS = 2
	
class MVLIngestionProcessor():

	def __init__(self, args):
		self.data = vars(args)
		
		self.copy_op = CopyFileOperation()
		self.proxy_op = ProxyGenerationOperation()
		self.mov_op = MovGenerationOperation()

		# Support both dict and argparse.Namespace
		if isinstance(args, dict):
			args = argparse.Namespace(**args)
		self.args = args

		try:
			self.ctx = Context.from_environment()
		except ValueError as e:
			logger.warning(f"{e} — Falling back to CLI arguments.")
			self.ctx = None  # Or a dummy object if needed
			# Check if output path is provided; if not, exit
			if not getattr(args, "output", None):
				logger.error("Context resolution failed and --output was not provided. Cannot continue.")
				sys.exit(1)

		self.resolved_project = args.project or (self.ctx.project if self.ctx else "gen63")
		self.resolved_scene = args.scene or (self.ctx.container if self.ctx else None)
		self.resolved_shot = args.shot or (self.ctx.scope if self.ctx else None)

		self.resolved_vendor = args.vendor
		self.resolved_date = args.input_date
		
		# If input is directly provided, use that
		if args.input:
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

		if args.output:
			self.resolved_out_dir = args.output
		else:
			self.resolved_out_dir = self._construct_out_path(
				project=self.resolved_project,
				scene = self.resolved_scene,
				shot = self.resolved_shot,
			)
		self.resolved_proxy_ext= args.proxy
		self.resolved_resolution= args.resolution
		self.is_force_ingestion= args.force

	def _construct_source_path(self, project, vendor, input_date):
		from datetime import datetime

		try:
			date_obj = datetime.strptime(input_date, "%Y-%m-%d")
			date_str = date_obj.strftime("%Y%m%d")
		except ValueError:
			raise ValueError("input_date must be in YYYY-MM-DD format.")

		cfg = Fig('mvl_ingestion', "path_template", YAMLConfigDriver())
		tokens = {
			'project_root': f'j:/{project}',
			'vendor': vendor,
			'date': date_str,
			'scene': self.resolved_scene,
			'shot': f"{self.resolved_scene}_{self.resolved_shot}"
		}

		ingest_workspace = cfg['template']['ingest_workspace']
		constructed_path = ingest_workspace.format(**tokens)

		if not os.path.exists(constructed_path):
			raise FileNotFoundError(f"Constructed source path does not exist: {constructed_path}")

		return constructed_path
	
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
			'repo':'plate',
			'sequence':scene,
			'shot':shot,
		}

		constructed_path = resolve_template("path", "shots:publish:base_path", tokens)
		if not os.path.exists(constructed_path):
			os.mkdirs(constructed_path)

		logger.info(f"destination path constructed : {constructed_path}")
		
		return constructed_path
	
	def validate_destination(self):
		destination_dir = self.data.get("destination")
		if not destination_dir:
			logging.error("Destination directory not provided.")
			exit(1)

		if not os.path.isdir(destination_dir):
			dest = self.data.get("destination")
			logging.info(f"Error: {dest} is not a valid directory.")
			return

		if not self.data.get("project"):
			logging.info(f"Error: {self.data.get('project')} is not a valid project.")
			return 
    
	def process_from_mvl(self):
		return NotImplementedError("Not implement yet!")
	
	def execute(self):
		"""
		Processes folders, gets all files and file sequences and ingest.
		"""
		file_tasks =  []
		sequence_tasks = []

		logger.info(f"source : {self.resolved_source}")

		if os.path.isfile(self.resolved_source):
			file_tasks[self.resolved_source]
		elif os.path.isdir(self.resolved_source):
			files, sequences = get_files_and_sequences(self.resolved_source, scene=self.resolved_scene, shot=self.resolved_shot)
			if files:
				file_tasks.append(files)
			if sequences:
				sequence_tasks.append(sequences)

		#logger.info(f"files : {file_tasks}, ###########\n sequence: {sequence_tasks}")

		# Run file and sequence copy tasks in parallel
		with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
			# File copy tasks
			all_files = [file_path for files_list in file_tasks for file_path in files_list]
			file_futures = [executor.submit(self.copy_file, file_path) for file_path in all_files]
			all_sequences = [seq for seq_list in sequence_tasks for seq in seq_list]
			# Sequence copy tasks
			sequence_futures = [
				executor.submit(
					SequenceBuilder(
						sequence=seq,
						copy_op=self.copy_op,
						proxy_op=self.proxy_op,
						mov_op=self.mov_op
					).build, False, self.data
				) for seq in all_sequences
			]
			# Wait for all to finish
			for future in concurrent.futures.as_completed(file_futures + sequence_futures):
				future.result()
        
	def parse_filename(self, filename):
		"""
		Parses the filename and returns the extracted information.
		Args:
		filename(str) :  source file name 
		"""
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

	def copy_file(self, file_path):
		"""
			Copies a single file to the output path.
			Args:
				file_path(str) : path of the file to copy
		"""
		try:
			base_name, extension = os.path.splitext(os.path.basename(file_path))
			output_path = generate_output_paths(1001, extension.lower(), self.data)  # 1001 for single files
			plate_path = output_path['plate']
			if output_path:
				os.makedirs(os.path.dirname(plate_path), exist_ok=True)
				shutil.copy2(file_path, plate_path)
				logging.info(f"Copied file: {os.path.basename(file_path)} to {plate_path}")
		except Exception as e:
			error_msg = f"Error copying file {os.path.basename(file_path)}: {e}"
			return False

	def copy_sequences(self, sequences):
		"""
			Copies the selected files and sequences to the created folder structure.
			Args:
				files(list) : list of files paths
				sequences(list) : list all the sequence found in paths
		"""
		if sequences:
			for seq in sequences:
				builder = SequenceBuilder(
					sequence=seq,
					copy_op=self.copy_op,
					proxy_op=self.proxy_op,
					mov_op=self.mov_op
				)
				builder.build(False, self.data)

		return True
	
	def display_results(self, files, sequences):
		"""Displays the identified files and sequences."""
		logging.info("Identified Files:")
		if files:
			for file_path in files:
				logging.info(f"  - {file_path}")
			else:
				logging.info("  No individual files found.")

			logging.info("\nIdentified File Sequences:")
			if sequences:
				for seq in sequences:
					logging.info(f"  - Base Name: {seq['base_name']}.{'#' * seq['padding']}.{seq['extension']}")
					logging.info(f"    Frame Range: {seq['start']} - {seq['end']}")
					logging.info(f"    Total Frames: {seq['end'] - seq['start'] + 1}")
				else:
					logging.info("  No file sequences found.")

	def generate_proxy_from_exr_using_convert(input_path, output_path, format):
		"""
		Generates an image file (JPEG or PNG) from an EXR file using OpenIMAJIO.

		Args:
			input_path (str): Path to the input EXR file.
			output_path (str): Path to save the generated image file.
			format (str): The desired output image format (jpeg or png).
		"""
		format = format.lower()
		if format not in ["jpeg", "png"]:
			logging.info(f"Error: Unsupported output image format: {format}. Please use 'jpeg' or 'png'.")
			return

		try:
			# Construct the OpenImageIO command for EXR to image conversion
			command = [
				"openimageio",
				"convert",
				input_path,
				"-o",
				output_path,
				"-format",
				format,
				# Add other OpenImageIO options as needed, e.g., exposure, tone mapping
				# Example for setting exposure:
				# "-e", "0.5",
				# Example for using a specific tone mapping operator:
				# "-tonemap", "aces",
			]

			logging.info(f"Running OpenImageIO command: {' '.join(command)}")
			subprocess.run(command, check=True, capture_output=True)
			logging.info(f"Successfully generated image: {output_path}")

		except FileNotFoundError:
			logging.info("Error: OpenImageIO command not found. Make sure it's in your system's PATH.")
		except subprocess.CalledProcessError as e:
			logging.info(f"Error generating image with OpenImageIO:")
			logging.info(f"Command: {' '.join(e.cmd)}")
			logging.info(f"Return Code: {e.returncode}")
			logging.info(f"Stdout: {e.stdout.decode()}")
			logging.info(f"Stderr: {e.stderr.decode()}")
		except Exception as e:
			logging.info(f"An unexpected error occurred: {e}")

	def exr_to_ffmpeg_pattern(self, outpath):
		"""
			Converts an EXR file path to an ffmpeg sequence pattern.
			Example: ..._1001_f4448x3096.exr -> ..._%04d_f4448x3096.exr
			Returns None if no frame number pattern is found.
		"""
		dir_name, file_name = os.path.split(outpath)
		# Try to match a frame number pattern
		match = re.search(r'_(\d{4})_', file_name) and not re.search(r'_(\d{4})(?=\.exr$)', file_name)
		logging.info (f"match : {match}")
		if not match:
			return None
		# Replace the frame number (e.g., 1001) with %04d
		pattern = re.sub(r'_(\d{4})_', r'_%04d_', file_name)
		# If frame number is at the end before .exr, handle that too
		pattern = re.sub(r'_(\d{4})(?=\.exr$)', r'_%04d', pattern)
		return os.path.join(dir_name, pattern)