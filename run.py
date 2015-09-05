
import train_model
import json_to_sig

import gaia2.fastyaml as yaml
import sys
import os
import json
import glob
from optparse import OptionParser

template = {"type": "singleClass",
            "version": 1.0,
            "className": "",
            "groundTruth": {}
    }

def get_files_in_dir(dirname, extension):
    return glob.glob(os.path.join(dirname, "*.%s" % extension))

def main(dirname, options):
    print "running in dir", dirname
    project_dir = os.path.abspath(dirname)
    projname = os.path.basename(dirname)

    # if config/results exist, need force to rm them
    project_file = os.path.join(project_dir, "%s.project" % projname)
    results_model_file = os.path.join(project_dir, "%s.history" % projname)
    resultsdir = os.path.join(project_dir, "results")
    datasetsdir = os.path.join(project_dir, "datasets")

    if os.path.exists(resultsdir):
        print >> sys.stderr, "Results directory already exists. Use -f to delete and re-run"
        return

    classes = [d for d in os.listdir(project_dir) \
            if os.path.isdir(os.path.join(project_dir, d))]
    print classes

    groundtruth_name = os.path.join(project_dir, "groundtruth.yaml")
    json_name = os.path.join(project_dir, "filelist.yaml")
    yaml_name = os.path.join(project_dir, "filelist-yaml.yaml")

    filelist = {}
    groundtruth = template
    missingsig = False
    for c in classes:
        files = get_files_in_dir(os.path.join(project_dir, c), "json")
        yamlfiles = get_files_in_dir(os.path.join(project_dir, c), "sig")

        if len(files) != len(yamlfiles):
            missingsig = True

        print "got", len(files), "files in", c
        for f in files:
            id = os.path.splitext(os.path.basename(f))[0]
            groundtruth["groundTruth"][id] = c
            filelist[id] = os.path.join(project_dir, c, f)

    # check directories for sig and convert
    groundtruth["className"] = projname
    yaml.dump(filelist, open(json_name, "w"))
    yaml.dump(groundtruth, open(groundtruth_name, "w"))

    if missingsig:
        print "converting sig"
        json_to_sig.convertJsonToSig(json_name, yaml_name)

    # run
    train_model.trainModel(groundtruth_name, yaml_name, project_file, project_dir, results_model_file)

if __name__ == "__main__":
    parser = OptionParser(usage = '%prog directory\n' +
"""
Generates a model of the files in `directory`. Converts to yaml
if needed.
""")

    options, args = parser.parse_args()

    try:
        directory = args[0]
    except:
        parser.print_help()
        sys.exit(1)
    main(directory, options)
