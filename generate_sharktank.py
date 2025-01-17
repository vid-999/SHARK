# Lint as: python3
"""SHARK Tank"""
# python generate_sharktank.py, you have to give a csv tile with [model_name, model_download_url]
# will generate local shark tank folder like this:
#   /SHARK
#     /gen_shark_tank
#       /tflite
#         /albert_lite_base
#         /...model_name...
#       /tf
#       /pytorch
#

import os
import urllib.request
import csv
import argparse
from shark.shark_importer import SharkImporter

# All generated models and metadata will be saved under this directory.
WORKDIR = os.path.join(os.path.dirname(__file__), "gen_shark_tank")


def save_torch_model(torch_model_list):
    from tank.model_utils import get_hf_model
    from tank.model_utils import get_vision_model
    import torch

    with open(torch_model_list) as csvfile:
        torch_reader = csv.reader(csvfile, delimiter=",")
        fields = next(torch_reader)
        for row in torch_reader:
            torch_model_name = row[0]
            tracing_required = row[1]
            model_type = row[2]

            tracing_required = False if tracing_required == "False" else True

            model = None
            input = None
            if model_type == "vision":
                model, input, _ = get_vision_model(torch_model_name)
            elif model_type == "hf":
                model, input, _ = get_hf_model(torch_model_name)

            torch_model_name = torch_model_name.replace("/", "_")
            torch_model_dir = os.path.join(WORKDIR, str(torch_model_name))
            os.makedirs(torch_model_dir, exist_ok=True)

            mlir_importer = SharkImporter(
                model,
                (input,),
                frontend="torch",
            )
            mlir_importer.import_debug(
                is_dynamic=False,
                tracing_required=tracing_required,
                dir=torch_model_dir,
                model_name=torch_model_name,
            )


def save_tf_model(tf_model_list):
    print("tf sharktank not implemented yet")
    pass


def save_tflite_model(tflite_model_list):
    from shark.tflite_utils import TFLitePreprocessor

    with open(tflite_model_list) as csvfile:
        tflite_reader = csv.reader(csvfile, delimiter=",")
        for row in tflite_reader:
            tflite_model_name = row[0]
            tflite_model_link = row[1]
            print("tflite_model_name", tflite_model_name)
            print("tflite_model_link", tflite_model_link)
            tflite_model_name_dir = os.path.join(
                WORKDIR, str(tflite_model_name)
            )
            os.makedirs(tflite_model_name_dir, exist_ok=True)
            print(f"TMP_TFLITE_MODELNAME_DIR = {tflite_model_name_dir}")

            tflite_tosa_file = "/".join(
                [
                    tflite_model_name_dir,
                    str(tflite_model_name) + "_tflite.mlir",
                ]
            )

            # Preprocess to get SharkImporter input args
            tflite_preprocessor = TFLitePreprocessor(str(tflite_model_name))
            raw_model_file_path = tflite_preprocessor.get_raw_model_file()
            inputs = tflite_preprocessor.get_inputs()
            tflite_interpreter = tflite_preprocessor.get_interpreter()

            # Use SharkImporter to get SharkInference input args
            my_shark_importer = SharkImporter(
                module=tflite_interpreter,
                inputs=inputs,
                frontend="tflite",
                raw_model_file=raw_model_file_path,
            )
            mlir_model, func_name = my_shark_importer.import_mlir()

            if os.path.exists(tflite_tosa_file):
                print("Exists", tflite_tosa_file)
            else:
                mlir_str = mlir_model.decode("utf-8")
                with open(tflite_tosa_file, "w") as f:
                    f.write(mlir_str)
                print(f"Saved mlir in {tflite_tosa_file}")


# Validates whether the file is present or not.
def is_valid_file(arg):
    if not os.path.exists(arg):
        return None
    else:
        return arg


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--torch_model_csv",
        type=lambda x: is_valid_file(x),
        default="./tank/pytorch/torch_model_list.csv",
        help="""Contains the file with torch_model name and args. 
             Please see: https://github.com/nod-ai/SHARK/blob/main/tank/pytorch/torch_model_list.csv""",
    )
    parser.add_argument(
        "--tf_model_csv",
        type=lambda x: is_valid_file(x),
        default="./tank/tf/tf_model_list.csv",
        help="Contains the file with tf model name and args.",
    )
    parser.add_argument(
        "--tflite_model_csv",
        type=lambda x: is_valid_file(x),
        default="./tank/tflite/tflite_model_list.csv",
        help="Contains the file with tf model name and args.",
    )
    parser.add_argument("--upload", type=bool, default=False)

    args = parser.parse_args()
    if args.torch_model_csv:
        save_torch_model(args.torch_model_csv)

    if args.tf_model_csv:
        save_tf_model(args.torch_model_csv)

    if args.tflite_model_csv:
        save_tflite_model(args.torch_model_csv)

    if args.upload:
        print("uploading files to gs://shark_tank/")
        os.system("gsutil cp -r ./gen_shark_tank/* gs://shark_tank/")
