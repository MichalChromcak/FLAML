'''Require: pip install torch transformers datasets wandb flaml[blendsearch,ray]
'''
#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
import os, argparse, subprocess
import datetime
import json
import shutil
from flaml.nlp import AutoTransformers
from flaml.nlp import flush_and_upload, flush_and_upload_prediction
from utils import get_wandb_azure_key

global azure_log_path
global azure_key

dataset_names = [["glue"], ["glue"], ["glue"], ["super_glue"], ["super_glue"], ["super_glue"]]
subdataset_names = ["cola", "mrpc", "rte", "wic", "rte", "copa"]

resplit_modes = ["resplit", "origin"]

pretrained_models = [("xlnet-base-cased", "base"),
                     ("albert-large-v1", "small"),
                     ("distilbert-base-uncased", "base"),
                     ("microsoft/deberta-base", "base"),
                     ("funnel-transformer/small-base", "base"),
                     ("microsoft/deberta-large", "large"),
                     ("funnel-transformer/large-base", "large"),
                     ("funnel-transformer/intermediate-base", "intermediate"),
                     ("funnel-transformer/xlarge-base", "xlarge")]

search_algos = ["BlendSearch", "BlendSearch", "Optuna", "Optuna", "CFO", "CFO"]
scheduler_names = ["None", "ASHA", "None", "ASHA", "None", "ASHA"]

hpo_searchspace_modes = ["hpo_space_generic", "hpo_space_gridunion_other", "hpo_space_generic", "hpo_space_gridunion_other"]
search_algo_args_modes = ["default", "default", "experiment", "experiment"]
num_sample_time_budget_mode = "custom"

def get_resplit_portion(this_dataset_name, this_subset_name):
    if this_dataset_name == ["glue"] and this_subset_name in {"mnli", "qqp"}:
        return {"source": ["train", "validation"], "train": [0, 0.25], "validation": [0.25, 0.275], "test": [0.275, 0.3]}
    elif this_dataset_name[0] in {"imdb", "dbpedia_14", "yelp_review_full"}:
        return {"source": ["train", "test"], "train": [0, 0.05], "validation": [0.05, 0.055], "test": [0.055, 0.06]}
    else:
        return {"source": ["train", "validation"], "train": [0, 0.8], "validation": [0.8, 0.9], "test": [0.9, 1.0]}

def get_preparedata_setting(args, this_dataset_name, this_subset_name, each_pretrained_model, each_model_size_type):
    preparedata_setting = {
        "dataset_config": {"task": "text-classification",
                           "dataset_name": this_dataset_name,
                           "subdataset_name": this_subset_name,
                           },
        "model_name": each_pretrained_model,
        "model_size_type": each_model_size_type,
        "server_name": args.server_name,
        "split_mode": resplit_modes[args.resplit_idx],
        "data_root_path": args.data_root_dir,
        "max_seq_length": 128,
        }
    if args.resplit_idx == 0:
        preparedata_setting["resplit_portion"] = get_resplit_portion(this_dataset_name, this_subset_name)
    if ("albert" in each_pretrained_model and this_dataset_name == "squad") or \
        ("funnel" in each_pretrained_model and isinstance(this_dataset_name, str) and this_dataset_name in {"imdb", "yelp_review_full", "yelp_polarity", "amazon_polarity", "amazon_review_multi"}):
        preparedata_setting["max_seq_length"] = 512
    if this_dataset_name[0] == "glue" and this_subset_name and this_subset_name == "mnli":
        preparedata_setting["dataset_config"]["fold_name"] = ['train', 'validation_matched', 'test_matched']
    return preparedata_setting

def get_autohf_settings_grid(args):
    autohf_settings = {"resources_per_trial": {"gpu": 1, "cpu": 1},
                           "search_algo_name": args.algo_mode,
                           "scheduler_name": "None",
                           "ckpt_per_epoch": 1,
                           }
    return autohf_settings

def get_autohf_settings(args, this_search_algo, this_scheduler_name, hpo_searchspace_mode, search_algo_args_mode = None):
    autohf_settings = {"resources_per_trial": {"gpu": 1, "cpu": 1},
                       "search_algo_name": this_search_algo,
                       "scheduler_name": this_scheduler_name,
                       "ckpt_per_epoch": 1,
                       "search_algo_args_mode": search_algo_args_mode,
                      }
    autohf_settings["hpo_searchspace_mode"] = hpo_searchspace_mode
    autohf_settings["num_sample_time_budget_mode"] = num_sample_time_budget_mode
    autohf_settings["custom_num_samples"] = args.sample_num
    autohf_settings["custom_time_budget"] = args.time_budget
    if args.ds_config:
        autohf_settings["ds_config"] = args.ds_config
    else:
        autohf_settings["ds_config"] = None
    return autohf_settings

def get_autohf_settings_enumeratehp():
    autohf_settings = {"resources_per_trial": {"gpu": 1, "cpu": 1},
                           "search_algo_name": "grid_search_enumerate",
                           "scheduler_name": "None",
                           "ckpt_per_epoch": 1,
                           "hp_to_fix": ("warmup_ratio", 0.05),
                           "hp_to_tune": ("learning_rate", [1e-5 * x for x in range(1, 11)]),
                            "hpo_searchspace_mode": "enumerate_onehp",
                           }
    return autohf_settings

def output_predict(args, test_dataset, autohf, fout, save_file_name):
    if test_dataset:
        predictions, output_metric = autohf.predict(test_dataset)
        if output_metric:
            fout.write(str(output_metric[autohf.metric_name]) + "\n")
            fout.write("test " + (autohf.metric_name) + ":" + json.dumps(output_metric) + "\n")
            fout.write(args.yml_file + "\n\n")
            flush_and_upload(fout, args, azure_log_path)
        else:
            fout.write("\n\n" + args.yml_file + "\n\n")
            fout.flush()
            flush_and_upload(fout, args, azure_log_path)
        if autohf.split_mode == "origin":
            azure_save_file_name = azure_log_path.split("/")[-1][:-4]
            output_prediction_path = os.path.join(args.data_root_dir + "result/", azure_save_file_name + ".zip")
            autohf.output_prediction(predictions,
                                     output_prediction_path= args.data_root_dir + "result/",
                                     output_dir_name=azure_save_file_name)
            flush_and_upload_prediction(fout, args, output_prediction_path)

def rm_home_result():
    from os.path import expanduser
    home = expanduser("~")
    if os.path.exists(home + "/ray_results/"):
        shutil.rmtree(home + "/ray_results/")

def write_exception(args, save_file_name, fout):
    fout.write(save_file_name + ":\n")
    fout.write("timestamp:" + str(str(datetime.datetime.now()))  + ":\n")
    fout.write("failed, no checkpoint found\n")
    flush_and_upload(fout, args, azure_log_path)

def write_regular(autohf, args, validation_metric, save_file_name, fout, sample_num=None):
    fout.write(save_file_name + ":\n")
    fout.write("timestamp:" + str(str(datetime.datetime.now())) + ":\n")
    fout.write("validation " + (autohf.metric_name) + ":" + json.dumps(validation_metric) + "\n")
    fout.write("duration:" + str(autohf.last_run_duration) + "\n")
    if not sample_num:
        sample_num = 0
    fout.write("sample_num: " + str(sample_num) + "\n")
    fout.write(save_file_name.split("_")[-1] + "," + str(sample_num) + "," + str(autohf.last_run_duration) + "," + str(validation_metric) + ",")
    flush_and_upload(fout, args, azure_log_path)

def _test_grid(args, fout, autohf):
        this_dataset_name = dataset_names[args.dataset_idx]
        this_subset_name = subdataset_names[args.dataset_idx]

        each_pretrained_model = pretrained_models[args.pretrained_idx][0]
        each_model_size_type = pretrained_models[args.pretrained_idx][1]
        #clean_outdated_results(args, dataset_names, subdataset_names)
        preparedata_setting = get_preparedata_setting(args, this_dataset_name, this_subset_name, each_pretrained_model, each_model_size_type)
        train_dataset, eval_dataset, test_dataset = \
        autohf.prepare_data(**preparedata_setting)
        autohf_settings = get_autohf_settings_grid(args)

        try:
            validation_metric, analysis = autohf.fit(train_dataset,
                       eval_dataset,
                       **autohf_settings,)
        except AssertionError as err:
            raise err

        write_regular(autohf, args, validation_metric, autohf.group_name, fout, len(analysis.trials))
        output_predict(args, test_dataset, autohf, fout, autohf.group_name)
        rm_home_result()

def _test_hpo_hf(args, fout, autohf):
    for data_idx in range(args.dataset_idx, args.dataset_idx + 1):
        this_dataset_name = dataset_names[data_idx]
        this_subset_name = subdataset_names[data_idx]
        each_pretrained_model = pretrained_models[args.pretrained_idx][0]
        each_model_size_type = pretrained_models[args.pretrained_idx][1]
        preparedata_setting = get_preparedata_setting(args, this_dataset_name, this_subset_name,
                                                      each_pretrained_model, each_model_size_type)
        #clean_outdated_results(args, dataset_names, subdataset_names)
        train_dataset, eval_dataset, test_dataset = \
            autohf.prepare_data(**preparedata_setting)
        try:
            autohf_settings = {"resources_per_trial": {"gpu": 1, "cpu": 1},
                               "num_sample_time_budget_mode": "custom",
                               "custom_num_samples": args.sample_num,
                               "custom_time_budget": args.time_budget}
            validation_metric = autohf.fit_hf(train_dataset,
                                                         eval_dataset,
                                                        **autohf_settings)
        except AssertionError:
            write_exception(args, autohf.group_name, fout)
            continue
        write_regular(autohf, args, validation_metric, autohf.group_name, fout)
        output_predict(args, test_dataset, autohf, fout, autohf.group_name)
        rm_home_result()

def _test_hpo(args, fout, autohf):
    this_dataset_name = dataset_names[args.dataset_idx]
    this_subset_name = subdataset_names[args.dataset_idx]

    this_search_algo = search_algos[args.algo_idx]
    this_scheduler_name = scheduler_names[args.algo_idx]

    each_pretrained_model = pretrained_models[args.pretrained_idx][0]
    each_model_size_type = pretrained_models[args.pretrained_idx][1]
    #clean_outdated_results(args, dataset_names, subdataset_names)
    hpo_searchspace_mode = hpo_searchspace_modes[args.space_idx]
    search_algo_args_mode = search_algo_args_modes[args.space_idx]
    preparedata_setting = get_preparedata_setting(args, this_dataset_name, this_subset_name,
                                                  each_pretrained_model, each_model_size_type)
    train_dataset, eval_dataset, test_dataset = \
        autohf.prepare_data(**preparedata_setting)
    autohf_settings = get_autohf_settings(args, this_search_algo, this_scheduler_name, hpo_searchspace_mode, search_algo_args_mode)

    try:
        validation_metric, analysis = autohf.fit(train_dataset,
                   eval_dataset,
                   **autohf_settings,)
    except AssertionError:
        write_exception(args, autohf.group_name, fout)
        return

    write_regular(autohf, args, validation_metric, autohf.group_name, fout, len(analysis.trials))
    output_predict(args, test_dataset, autohf, fout, autohf.group_name)
    rm_home_result()

    fout.close()

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--server_name', type=str, help='server name', required=True,
                            choices=["tmdev", "dgx", "azureml"])
    arg_parser.add_argument('--algo_mode', type=str, help='hpo or grid search', required=True,
                            choices=["grid_search", "grid_search_bert", "hpo", "hpo_hf"])
    arg_parser.add_argument('--data_root_dir', type=str, help='data dir', required=True)
    arg_parser.add_argument('--dataset_idx', type=int, help='data index', required=False)
    arg_parser.add_argument('--is_rerun', action='store_true', help='whether to rerun')
    arg_parser.add_argument('--space_idx', type=int, help='space index', required=False)
    arg_parser.add_argument('--algo_idx', type=int, help='algorithm index', required=False)
    arg_parser.add_argument('--pretrained_idx', type=int, help='pretrained index', required=False)
    arg_parser.add_argument('--sample_num', type=int, help='sample num', required=False)
    arg_parser.add_argument('--time_budget', type=int, help='time budget', required=False)
    arg_parser.add_argument('--rep_id', type=int, help='rep id', required=False)
    arg_parser.add_argument('--azure_key', type=str, help='azure key', required=False)
    arg_parser.add_argument('--resplit_idx', type=int, help='resplit mode', required=True)
    arg_parser.add_argument('--ds_config', type=str, help='deep speed config file path', required = False)
    arg_parser.add_argument('--yml_file', type=str, help='yml file path', required=True)
    args = arg_parser.parse_args()

    if os.path.exists("wandb"):
        shutil.rmtree("wandb")

    wandb_key, args.azure_key = get_wandb_azure_key(os.path.abspath("../../"))
    subprocess.run(["wandb", "login", "--relogin", wandb_key])
    os.environ["WANDB_API_KEY"] = wandb_key

    from flaml.nlp.result_analysis.utils import get_azurepath
    azure_log_path = get_azurepath(args, dataset_names, subdataset_names)

    fout = open(azure_log_path, "a")
    if args.algo_mode.startswith("grid"):
        _test_grid(args, fout, autohf = AutoTransformers())
    elif args.algo_mode == "hpo":
        _test_hpo(args, fout, autohf = AutoTransformers())
    else:
        _test_hpo_hf(args, fout, autohf = AutoTransformers())

    fout.close()