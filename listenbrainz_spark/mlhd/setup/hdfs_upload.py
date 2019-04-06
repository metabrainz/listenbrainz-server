import listenbrainz_spark.config as config
import os
import shutil
import subprocess
import tempfile


from listenbrainz_spark import hdfs_connection

def process_tar_file(file_dir, file_name):
    tmp_dir = tempfile.mkdtemp()
    shutil.copy(src=os.path.join(file_dir, file_name), dst=os.path.join(tmp_dir, file_name))
    subprocess.check_output(['tar', '-xf', os.path.join(tmp_dir, file_name)])
    subprocess.check_output(['gunzip', os.path.join(tmp_dir, '*.gz')])
    for listen_file in os.listdir(tmp_dir):
        if listen_file.endswith('.txt'):
            hdfs_path = os.path.join('/data', 'mlhd', listen_file[0], listen_file[0:2], listen_file)
            hdfs_connection.client.upload(hdfs_path=hdfs_path, local_path=os.path.join(tmp_dir, listen_file))
    shutil.rmtree(tmp_dir)


def main(mlhd_dir):
    hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
    for mlhd_file in os.listdir(mlhd_dir):
        if mlhd_file.endswith('.tar'):
            process_tar_file(mlhd_dir, mlhd_file)


if __name__ == '__main__':
    main('/home/param/mlhd')
