#!/usr/bin/env python3

import json
import os
import subprocess
import pyspark
from pyspark.sql import SparkSession
from pyspark import SparkContext

# Fetch worker VM IPs from Terraform output
def get_worker_ips():
    command = "terraform output --json worker_vm_ips".split()
    try:
        ip_data = json.loads(subprocess.run(command, capture_output=True, encoding='UTF-8').stdout)
        return list(ip_data)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to fetch worker IPs: {e}")
        return []

# Configuration constants
WORKERS = get_worker_ips()
CHUNK_SIZE = 100

# Read total PDB files from the specified file
def get_all_data_files(filepath='./datapaths.txt'):
    try:
        with open(filepath, 'r') as f:
            total_files = int(f.readline().split()[0])
        return total_files
    except Exception as e:
        print(f"[ERROR] Failed to read total PDB files: {e}")
        return 0

ALL_DATA_FILES = get_all_data_files()

# Directories for input, output, and the analysis script
REMOTE_SCRIPT_PATH = "/home/almalinux/pipeline/pipeline_script_v1.py"
INPUT_DIR = "/home/almalinux/input/"
OUTPUT_DIR = "/home/almalinux/output/"

def generate_tasks(total_files, chunk_size):
    """
    Generates (start_index, end_index) tuples for each chunk.
    Each task corresponds to a range of file indices to be processed.
    """
    tasks = []
    start = 1
    while start <= total_files:
        end = min(start + chunk_size - 1, total_files)
        tasks.append((start, end))
        start += chunk_size
    return tasks

def run_spark_analysis(task):
    """
    Runs the analysis for a specific chunk of files using Apache Spark.
    This includes:
    1. Copying input files to the worker.
    2. Running the analysis script on the Spark cluster.
    3. Uploading results and cleaning up.
    """
    start_idx, end_idx = task
    try:
        # Step 1: Copy files to worker's input directory (using Spark RDD)
        print(f"[INFO] Assigning files {start_idx}-{end_idx} to worker.")
        cmd = (
            f"sed -n '{start_idx},{end_idx}p' /home/almalinux/paths.txt | "
            f"xargs -I{{}} -n1 -P4 mc cp local/input/{{}} {INPUT_DIR}{{}}"
        )
        subprocess.run(cmd, shell=True, check=True)

        # Step 2: Run the analysis script on the worker
        cmd = f"python {REMOTE_SCRIPT_PATH}"
        print(f"[INFO] Analyzing files {start_idx}-{end_idx} on Spark.")
        subprocess.run(cmd, shell=True, check=True)

        # Step 3: Upload results and clean up
        cmd = (
            f"mc cp --recursive {OUTPUT_DIR} local/output; "
            f"rm -r {INPUT_DIR}* {OUTPUT_DIR}*"
        )
        print(f"[INFO] Uploading and cleaning files {start_idx}-{end_idx}.")
        subprocess.run(cmd, shell=True, check=True)

    except Exception as e:
        print(f"[ERROR] Analysis failed for files {start_idx}-{end_idx}: {e}")

def main():
    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("PDB File Processing") \
        .getOrCreate()

    sc = spark.sparkContext

    # Step 1: Generate tasks (chunks of files)
    tasks = generate_tasks(ALL_DATA_FILES, CHUNK_SIZE)

    # Step 2: Parallelize tasks using Spark
    tasks_rdd = sc.parallelize(tasks)

    # Step 3: Run analysis tasks in parallel on the Spark cluster
    tasks_rdd.foreach(run_spark_analysis)

    print("[INFO] All PDB files have been analyzed.")

    # Stop Spark session after processing
    spark.stop()

if __name__ == "__main__":
    main()
