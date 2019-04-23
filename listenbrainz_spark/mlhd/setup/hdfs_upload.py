import listenbrainz_spark.config as config
import os
import shutil
import subprocess
import tempfile
import time


from listenbrainz_spark import hdfs_connection


def process_tar_file(file_dir, file_name):
    t0 = time.time()
    tmp_dir = tempfile.mkdtemp()
    print("Extracting file %s..." % file_name)
    subprocess.check_output(['tar', '-xf', os.path.join(file_dir, file_name), '-C', tmp_dir])
    print(len(os.listdir(tmp_dir)))
    print("Extracting listen files...")
    te = time.time()
    extracted = 0
    for gz_file in os.listdir(tmp_dir):
        if gz_file.endswith('.gz'):
            subprocess.check_output(['gunzip', os.path.join(tmp_dir, gz_file)])
            extracted += 1
    print("extracted %d files in %.2f s" % (extracted, time.time() - te))
    print("Uploading files to HDFS...")
    uploaded = 0
    tu = time.time()
    hdfs_path = os.path.join('/data', 'mlhd', file_name.split('.')[0])
    hdfs_connection.client.makedirs(hdfs_path)
    for listen_file in os.listdir(tmp_dir):
        if listen_file.endswith('.txt'):
            hdfs_connection.client.upload(hdfs_path=os.path.join(hdfs_path, listen_file), local_path=os.path.join(tmp_dir, listen_file))
            uploaded += 1
    print("uploaded %d files in %.2f s" % (uploaded, time.time() - tu))
    shutil.rmtree(tmp_dir)
    print("file %s done in %.2f s!" % (file_name, time.time() - t0))


def main(mlhd_dir):
    hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
    for mlhd_file in os.listdir(mlhd_dir):
        if mlhd_file.endswith('.avro'):
            print('Uploading ', mlhd_file)
            hdfs_connection.client.upload(hdfs_path=os.path.join('/data/mlhd', mlhd_file), local_path=os.path.join(mlhd_dir, mlhd_file))
            print('Done')


if __name__ == '__main__':
    main('/home/param/mlhd')
