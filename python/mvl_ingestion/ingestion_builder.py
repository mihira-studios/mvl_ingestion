import os
import sys
import re
import time
import threading
import concurrent.futures

from mvl_ingestion.ingestion_utils import logger, generate_sequence_output_paths, get_resolution_string

def print_slow(text, delay=0.03):
    for c in text:
        sys.stdout.write(c)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def spinner(msg, stop_event):
    spinner_seq = "|/-\\"
    idx = 0
    sys.stdout.write(msg + " ")
    sys.stdout.flush()
    while not stop_event.is_set():
        sys.stdout.write(spinner_seq[idx % len(spinner_seq)])
        sys.stdout.flush()
        time.sleep(0.1)
        sys.stdout.write('\b')
        idx += 1
    sys.stdout.write("✔️\n")

class SequenceBuilder:
    def __init__(self, sequence, copy_op, proxy_op, mov_op):
        self.sequence = sequence  # dict with 'paths' key
        self.copy_op = copy_op
        self.proxy_op = proxy_op
        self.mov_op = mov_op
        self.copied_paths = []
        self.out_paths = {}

    def copy_sequence(self, metadata):
        copied = []
        start_frame = metadata.get('start_frame', 1001) # Default start frame
        overwrite = metadata.get('overwrite', False)
        if not isinstance(self.sequence, dict) or not self.sequence or not self.sequence.get('paths'):
            logger.error(f"No valid sequence paths found {self.sequence}")
            return  
        
        frame_counter = start_frame
        tasks = []
        num_workers = os.cpu_count() or 4  # Fallback to 4 if detection fails

        self.out_paths = generate_sequence_output_paths(self.sequence, metadata)
        print_slow("[COPY] Copying exrs...", 0.02)
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            for src, dest in self.out_paths.get('plate_path').items():
                tasks.append(executor.submit(self.copy_op.execute, src, dest, overwrite))
                copied.append(dest)
               
            # Wait for all copies to finish
            for task in concurrent.futures.as_completed(tasks):
                task.result()
        self.copied_paths = copied

        folder_name = os.path.dirname(dest)
        logger.info(f"Copy complete for sequence in folder: {folder_name} ({len(self.copied_paths)} files)")

    def generate_proxies(self, proxy_fmt, proxy_res_fmt):
        if not self.copied_paths:
            return
        
        proxy_dir = str(self.out_paths.get('proxy_path'))
        normalized_path = os.path.normpath(proxy_dir)
        if proxy_dir and not os.path.exists(normalized_path):
            os.makedirs(normalized_path)  # creates the directory and any intermediate folders

        # Get proxy res
        proxy_res= get_resolution_string(proxy_res_fmt) 

        print_slow("[PROXY] Generating proxies...", 0.02)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for exr_path in self.copied_paths:
                filename_with_proxy_res = re.sub(r'\d{3,5}x\d{3,5}', proxy_res, os.path.basename(exr_path))
                proxy_path = os.path.join(normalized_path, filename_with_proxy_res.replace('.exr', f'.{proxy_fmt}'))
                futures.append(executor.submit(self.proxy_op.execute, os.path.normpath(exr_path), proxy_path, proxy_res))
            for future in concurrent.futures.as_completed(futures):
                future.result()
        
        logger.info(f"Proxy generation completed for sequence in folder: {normalized_path}")

    def generate_mov(self, metadata):
        if not self.copied_paths:
            logger.info(f"No file seqeuence found.")
            return
        seq_path = self.copied_paths[0].replace('1001', '%04d')  # adjust as needed
        mov_path = os.path.join(self.out_paths.get('movie_path'), os.path.basename(seq_path).replace('exr', 'mov'))
        # Check if the file exists and `--force` flag is not set
        if os.path.exists(mov_path) and not metadata.get('force'):
            logger.info(f"Movie already exists at {mov_path}, skipping. Use --force to overwrite the file.")
        else:
            print_slow("[MOV] Generating Dailies...", 0.02)
            self.mov_op.execute(seq_path, mov_path, metadata)

    def build(self, parallel_proxy=False, metadata= None):
        self.copy_sequence(metadata)
        if metadata.get('proxy_format') and parallel_proxy:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(self.generate_proxies, metadata.get('proxy_format'))
                executor.submit(self.generate_mov)
        else:
            if metadata.get('use_proxy'):
                proxy_fmt = metadata.get('proxy', 'jpeg')
                proxy_res = metadata.get('proxy_res', "2K_DCP")
                self.generate_proxies(proxy_fmt=proxy_fmt, proxy_res_fmt = proxy_res)
            if metadata.get('mov'):
                self.generate_mov(metadata)