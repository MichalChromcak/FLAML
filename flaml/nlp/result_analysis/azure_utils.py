import re
import pathlib
import os
from datetime import datetime
from dataclasses import dataclass, field
import json


@dataclass
class JobID:
    dat: list = field(default=None)
    subdat: str = field(default=None)
    mod: str = field(default=None)
    spa: str = field(default=None)
    arg: str = field(default=None)
    alg: str = field(default=None)
    pru: str = field(default=None)
    pre_full: str = field(default=None)
    pre: str = field(default=None)
    presz: str = field(default=None)
    spt: str = field(default=None)
    rep: int = field(default=0)
    sddt: int = field(default=None)
    sdhf: int = field(default=None)
    var1: float = field(default=None)
    var2: float = field(default=None)

    def __init__(self,
                 console_args=None):
        if console_args:
            self.set_jobid_from_console_args(console_args)

    def set_unittest_config(self):
        """
            set the JobID config for unit test
        """
        self.dat = ["glue"]
        self.subdat = "mrpc"
        self.mod = "hpo"
        self.spa = "uni_test"
        self.arg = "dft"
        self.alg = "bs"
        self.pru = "None"
        self.pre_full = "google/mobilebert-uncased"
        self.pre = "mobilebert"
        self.presz = "small"
        self.spt = "rspt"
        self.rep = 0
        self.sddt = 43
        self.sdhf = 42

    def is_match(self, partial_jobid):
        """
            return a boolean variable whether the current object matches the partial jobid defined
            in partial_jobid. For example,
            self = JobID(dat = ['glue'],
                            subdat = 'cola',
                            mod = 'bestnn',
                            spa = 'buni',
                            arg = 'cus',
                            alg = 'bs',
                            pru = 'None',
                            pre = 'funnel',
                            presz = 'xlarge',
                            spt = 'rspt',
                            rep = 0,
                            sddt = 43,
                            sdhf = 42)
            partial_jobid1 = JobID(dat = ['glue'],
                                  subdat = 'cola',
                                  mod = 'hpo')
           partial_jobid2 = JobID(dat = ['glue'],
                                  subdat = 'cola',
                                  mod = 'bestnn')
            return False for partial_jobid1 and True for partial_jobid2
        """
        is_not_match = False
        for key, val in partial_jobid.__dict__.items():
            if val is None:
                continue
            if getattr(self, key) != val:
                is_not_match = True
        return not is_not_match

    def to_wandb_string(self):
        """
            preparing for the job ID for wandb
        """
        field_dict = self.__dict__
        keytoval_str = "_".join([JobID.dataset_list_to_str(field_dict[key])
                                 if type(field_dict[key]) == list
                                 else str(field_dict[key])
                                 for key in field_dict.keys() if not key.endswith("_full")])
        return keytoval_str

    def to_jobid_string(self):
        """
            convert the current JobID into a blob name string which contains all the fields
        """
        list_keys = list(JobID.__dataclass_fields__.keys())
        field_dict = self.__dict__
        keytoval_str = "_".join([key + "=" + JobID.dataset_list_to_str(field_dict[key])
                                 if type(field_dict[key]) == list
                                 else key + "=" + str(field_dict[key])
                                 for key in list_keys if not key.endswith("_full")])
        return keytoval_str

    def to_partial_jobid_string(self):
        """
            convert the current JobID into a blob name string which only contains the fields whose values are not "None"
        """
        list_keys = list(JobID.__dataclass_fields__.keys())
        field_dict = self.__dict__  # field_dict contains fields whose values are not None
        keytoval_str = "_".join([key + "=" + JobID.dataset_list_to_str(field_dict[key])
                                 if type(field_dict[key]) == list
                                 else key + "=" + str(field_dict[key])
                                 for key in list_keys if key in field_dict.keys()])
        return keytoval_str

    @staticmethod
    def blobname_to_jobid_dict(keytoval_str):
        """
            converting an azure blobname to a JobID config,
            e.g., blobname = "dat=glue_subdat=cola_mod=bestnn_spa=buni_arg=cus_
                              alg=bs_pru=None_pre=funnel_presz=xlarge_spt=rspt_rep=0.json"
            the converted jobid dict = {dat = ['glue'], subdat = 'cola', mod = 'bestnn',
                                   spa = 'buni', arg = 'cus', alg = 'bs', pru = 'None',
                                   pre = 'funnel', presz = 'xlarge', spt = 'rspt',
                                   rep = 0, sddt = 43, sdhf = 42)
        """
        field_keys = [key for key in list(JobID.__dataclass_fields__.keys()) if not key.endswith("_full")]
        regex_expression = ".*"
        is_first = True
        for key in field_keys:
            if is_first:
                prefix = ""
                is_first = False
            else:
                prefix = "_"
            if key.startswith("sd") or key.startswith("var"):
                regex_expression += "(" + prefix + key + "=(?P<" + key + ">.*))?"
            else:
                regex_expression += prefix + key + "=(?P<" + key + ">.*)"
        regex_expression += ".(json|zip)"
        result = re.search(regex_expression, keytoval_str)
        if result:
            result_dict = {}
            for key in field_keys:
                if key == "dat":
                    result_dict[key] = [result.group(key)]
                elif key == "rep":
                    try:
                        result_dict[key] = int(result.group(key))
                    except:
                        result_dict[key] = -1
                else:
                    result_dict[key] = result.group(key)
            return result_dict
        else:
            return None

    @staticmethod
    def dataset_list_to_str(dataset_name, key = "dat"):
        if isinstance(dataset_name, list):
            return "-".join(dataset_name)
        else:
            return dataset_name

    @staticmethod
    def set_jobid_from_arg_list(self,
                                **jobid_list
                                ):
        """
            set the jobid from a dict object
        """

        for key in jobid_list.keys():
            assert key in JobID.__dataclass_fields__.keys()
            setattr(self, key, jobid_list[key])

    @staticmethod
    def convert_blobname_to_jobid(blobname):
        """
            converting a blobname string to a JobID object
        """
        jobconfig_dict = JobID.blobname_to_jobid_dict(blobname)
        if jobconfig_dict:
            jobconfig = JobID()
            jobconfig.set_jobid_from_arg_list(**jobconfig_dict)
            return jobconfig
        else:
            return None

    @staticmethod
    def get_full_data_name(dataset_name:list or str, subdataset_name=None):
        """
            convert a dataset name and sub dataset name to a full dataset name
        """
        if isinstance(dataset_name, list):
            full_dataset_name = JobID.dataset_list_to_str(dataset_name)
        else:
            full_dataset_name = dataset_name
        if subdataset_name:
            full_dataset_name = full_dataset_name + "_" + subdataset_name
        return full_dataset_name

    def get_jobid_full_data_name(self):
        """
            get the full dataset name of the current JobID object
        """
        return JobID.get_full_data_name(JobID.dataset_list_to_str(self.dat), self.subdat)

    @staticmethod
    def _extract_model_type_with_keywords_match(pre_full):
        from ..hpo.grid_searchspace_auto import HF_MODEL_LIST
        matched_model_type = []
        for each_model_type in HF_MODEL_LIST:
            if each_model_type in pre_full:
                matched_model_type.append(each_model_type)
        assert len(matched_model_type) > 0
        return max(enumerate(matched_model_type), key=lambda x: len(x[1]))[1]

    @staticmethod
    def extract_model_type(full_model_name):
        try:
            from transformers import AutoConfig
            model_config = AutoConfig.from_pretrained(full_model_name)
            config_json_file = model_config.get_config_dict(full_model_name)[0]
            try:
                model_type = config_json_file["model_type"]
            except KeyError:
                model_type = JobID._extract_model_type_with_keywords_match()
            return model_type
        except ImportError:
            pass

    def set_jobid_from_console_args(self, console_args):
        self.dat = console_args.dataset_subdataset_name.split(":")[0].split(",")
        self.subdat = console_args.dataset_subdataset_name.split(":")[1]
        self.mod = console_args.algo_mode
        self.spa = console_args.space_mode
        self.arg = console_args.search_alg_args_mode
        self.alg = console_args.algo_name
        self.pru = console_args.pruner
        self.pre_full = console_args.pretrained_model_size.split(":")[0]
        self.pre = JobID.extract_model_type(self.pre_full)
        self.presz = console_args.pretrained_model_size.split(":")[1]
        self.spt = console_args.resplit_mode
        self.rep = console_args.rep_id
        self.sddt = console_args.seed_data
        self.sdhf = console_args.seed_transformers
        self.var1 = console_args.varying_arg1
        self.var2 = console_args.varying_arg2

class AzureUtils:

    def __init__(self,
                 root_log_path=None,
                 console_args=None,
                 jobid=None,
                 autohf=None):
        from ..utils import get_wandb_azure_key
        if root_log_path:
            self.root_log_path = root_log_path
        else:
            self.root_log_path = "logs_azure"
        self.jobid = jobid
        self.console_args = console_args
        self.autohf = autohf
        if console_args:
            wandb_key, azure_key, container_name = get_wandb_azure_key(console_args.key_path)
            self._container_name = container_name
            self._azure_key = azure_key

    def _get_complete_connection_string(self):
        return "DefaultEndpointsProtocol=https;AccountName=docws5141197765;AccountKey=" \
               + self._azure_key + ";EndpointSuffix=core.windows.net"

    def _init_azure_clients(self):
        try:
            from azure.storage.blob import ContainerClient
            connection_string = self._get_complete_connection_string()
            container_client = ContainerClient.from_connection_string(conn_str=connection_string,
                                                                      container_name=self._container_name)
            return container_client
        except ImportError:
            pass

    def _init_blob_client(self,
                          local_file_path):
        try:
            from azure.storage.blob import BlobServiceClient

            connection_string = self._get_complete_connection_string()
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            blob_client = blob_service_client.get_blob_client(container=self._container_name, blob=local_file_path)
            return blob_client
        except ImportError:
            pass

    def upload_local_file_to_azure(self, local_file_path):
        blob_client = self._init_blob_client(local_file_path)
        with open(local_file_path, "rb") as fin:
            blob_client.upload_blob(fin, overwrite=True)

    def download_azure_blob(self, blobname):
        blob_client = self._init_blob_client(blobname)
        pathlib.Path(re.search("(?P<parent_path>^.*)/[^/]+$", blobname).group("parent_path")).mkdir(
            parents=True, exist_ok=True)
        with open(blobname, "wb") as fout:
            fout.write(blob_client.download_blob().readall())

    def write_exception(self):
        result_json = {
            "timestamp": datetime.now(),
        }
        local_file_path = self.generate_local_json_path()
        self.create_local_json_and_upload(result_json, local_file_path)

    def extract_log_from_analysis(self,
                                  analysis):
        """
            Extracting a json object for storing the key information returned from tune.run
        """
        json_log = []
        for each_trial in analysis.trials:
            trial_id = each_trial.trial_id
            start_time = each_trial.start_time
            last_update_time = each_trial.last_update_time
            config = each_trial.config
            try:
                metric_score = each_trial.metric_analysis["eval_" + analysis.default_metric]
                time_stamp = each_trial.metric_analysis['timestamp']
                json_log.append({"trial_id": trial_id,
                                 "start_time": start_time,
                                 "last_update_time": last_update_time,
                                 "config": config,
                                 "metric_score": metric_score,
                                 "time_stamp": time_stamp})
            except KeyError:
                pass
        return json_log

    def write_autohf_output(self,
                            json_log=None,
                            valid_metric=None,
                            predictions=None,
                            duration=None):
        """
            write the key info from a job and upload to azure blob storage
        """
        local_file_path = self.generate_local_json_path()
        output_json = {}
        if json_log:
            output_json["val_log"] = json_log
        if valid_metric:
            output_json["valid_metric"] = valid_metric
        if duration:
            output_json["duration"] = duration
        if len(output_json) > 0:
            self.create_local_json_and_upload(output_json, local_file_path)
        if predictions is not None:
            self.create_local_prediction_and_upload(local_file_path, predictions)

    def generate_local_json_path(self):
        """
            return a path string for storing the json file locally
        """
        full_dataset_name = self.jobid.get_jobid_full_data_name()
        jobid_str = self.jobid.to_jobid_string()
        local_file_path = os.path.join(self.root_log_path, full_dataset_name, jobid_str + ".json")
        pathlib.Path(os.path.join(self.root_log_path, full_dataset_name)).mkdir(parents=True, exist_ok=True)
        return local_file_path

    def create_local_json_and_upload(self, result_json, local_file_path):
        with open(local_file_path, "w") as fout:
            fout.write(json.dumps(result_json))
            fout.flush()
            self.upload_local_file_to_azure(local_file_path)


    def create_local_prediction_and_upload(self,
                                           local_json_file,
                                           predictions):
        """
            store predictions (a .zip file) locally and upload
        """
        azure_save_file_name = local_json_file.split("/")[-1][:-5]
        local_archive_path = self.autohf.output_prediction(predictions,
                                                           output_prediction_path=self.console_args.data_root_dir + "result/",
                                                           output_zip_file_name=azure_save_file_name)
        self.upload_local_file_to_azure(local_archive_path)

    def get_ranked_configs(self, metric_mode):
        """
            extract the configs (ranked in descebding order by the score) for the azure file of the current object
            (defined by self.jobid_config)
        """
        azure_file_path = self.generate_local_json_path()
        self.download_azure_blob(azure_file_path)

        json_log = json.load(open(azure_file_path, "r"))
        assert "val_log" in json_log

        trialid_to_score = {}
        trialid_to_config = {}

        for each_entry in json_log["val_log"]:
            trial_id = each_entry["trial_id"]
            config = each_entry["config"]
            this_score = each_entry["metric_score"][metric_mode]
            trialid_to_config[trial_id] = config
            trialid_to_score[trial_id] = this_score

        sorted_trialid_to_score = sorted(trialid_to_score.items(), key=lambda x: x[1], reverse=True)
        return [trialid_to_config[entry[0]] for entry in sorted_trialid_to_score]

    @staticmethod
    def is_after_earliest_time(this_blob, earliest_time):
        import pytz
        utc = pytz.UTC
        if this_blob.last_modified >= utc.localize(datetime(earliest_time[0], earliest_time[1], earliest_time[2])):
            return True
        return False

    def get_blob_list_matching_partial_jobid(self, root_log_path, partial_jobid, earliest_time=None):
        """
            get all blobs whose jobid configs match the partial_jobid
        """
        blob_list = []
        container_client = self._init_azure_clients()
        jobid_config = JobID()
        for each_blob in container_client.list_blobs():
            if each_blob.name.startswith(root_log_path):
                each_jobconfig = jobid_config.convert_blobname_to_jobid(each_blob.name)
                is_append = False
                if each_jobconfig:
                    if each_jobconfig.is_match(partial_jobid):
                        is_append = True
                    if earliest_time and not AzureUtils.is_after_earliest_time(each_blob, earliest_time):
                        is_append = False
                    if is_append:
                        blob_list.append((each_jobconfig, each_blob))
        return blob_list

    @staticmethod
    def extract_config_and_score(blobname):
        data_json = json.load(open(blobname, "r"))
        return [(x['config'], x['metric_score']["max"], x['start_time']) for x in data_json['val_log']]

    def get_config_and_score_from_partial_jobid(self,
                                                root_log_path,
                                                partial_jobid,
                                                group_attrs,
                                                method,
                                                earliest_time=None):
        """
            get the best config and best score for each job matching the partial_jobid
        """
        matched_blob_list = self.get_blob_list_matching_partial_jobid(
            root_log_path,
            partial_jobid,
            earliest_time=earliest_time)
        group_dict = {}
        for (each_jobconfig, each_blob) in matched_blob_list:
            self.download_azure_blob(each_blob.name)
            config_and_score = AzureUtils.extract_config_and_score(each_blob.name)
            if method == "unsorted":
                sorted_config_and_score = config_and_score
            elif method == "sort_time":
                sorted_config_and_score = sorted(config_and_score, key=lambda x: x[2], reverse=False)
            else:
                sorted_config_and_score = sorted(config_and_score, key=lambda x: x[1], reverse=True)
            group_attr_list = []
            for each_attr in group_attrs:
                group_val = getattr(each_jobconfig, each_attr)
                if isinstance(group_val, list):
                    group_attr_list.append(JobID.dataset_list_to_str(group_val))
                else:
                    group_attr_list.append(group_val)
            group_attr_tuple = tuple(group_attr_list)
            group_dict.setdefault(group_attr_tuple, [])
            group_dict[group_attr_tuple].append([(config, score, each_blob.name)
                                                 for (config, score, ts) in sorted_config_and_score])
        return group_dict

    def get_validation_perf(self, console_args=None, partial_jobid_config=None):
        """
            get the validation score for all blobs matching the partial_jobid_config
        """
        if partial_jobid_config.pre == "electra":
            dataset_namelist = ["wnli", "rte", "mrpc", "cola", "stsb", "sst2", "qnli", "mnli"]
        else:
            dataset_namelist = ["wnli", "rte", "mrpc", "cola", "stsb", "sst2"]
        dataset_vallist1 = [0] * len(dataset_namelist)
        dataset_vallist2 = [0] * len(dataset_namelist)

        matched_blob_list = self.get_blob_list_matching_partial_jobid(console_args.azure_root_log_path,
                                                                      partial_jobid_config)
        for (each_jobconfig, each_blob) in matched_blob_list:
            subdat_name = each_jobconfig.subdat
            self.download_azure_blob(each_blob.name)
            data_json = json.load(open(each_blob.name, "r"))
            print(len(data_json["val_log"]))
            validation_metric = data_json['valid_metric']
            try:
                dataset_idx = dataset_namelist.index(subdat_name)
                dataset_vallist1[dataset_idx], dataset_vallist2[dataset_idx] \
                    = self.get_validation_metricstr(validation_metric)
            except ValueError:
                pass
        # print(" & ".join(dataset_vallist1))
        # print(", ,".join(dataset_vallist2))

    def get_validation_metricstr(self, validation_metric):
        """
            get a string representing validations for pasting to Google spreadsheet
        """
        validation_str1 = validation_str2 = ""
        is_first = True
        for key in ["f1", "accuracy", "pearson", "spearmanr", "matthews_correlation"]:
            if "eval_" + key in validation_metric.keys():
                if is_first:
                    validation_str1 += str("%.1f" % (validation_metric["eval_" + key] * 100))
                    validation_str2 += str(validation_metric["eval_" + key] * 100)
                    is_first = False
                else:
                    validation_str1 += "/" + str("%.1f" % (validation_metric["eval_" + key] * 100))
                    validation_str2 += "," + str(validation_metric["eval_" + key] * 100)
        return validation_str1, validation_str2

    def get_test_perf(self, partial_jobid_config=None, result_root_dir=None):
        """
            get the test scores for all blobs matching the partial_jobid_config
        """
        import shutil
        from flaml.nlp.dataset.submission_auto import file_name_mapping_glue, output_blank_tsv
        matched_blob_list = self.get_blob_list_matching_partial_jobid("data/", partial_jobid_config)
        partial_jobid_str = partial_jobid_config.to_partial_jobid_string()
        output_dir = os.path.join(result_root_dir, partial_jobid_str)
        if os.path.exists(output_dir):
            assert os.path.isdir(output_dir)
        else:
            os.mkdir(output_dir)
        output_blank_tsv(output_dir)

        for (each_jobconfig, each_blob) in matched_blob_list:
            subdat_name = each_jobconfig.subdat
            self.download_azure_blob(each_blob.name)
            import zipfile
            if os.path.exists(each_blob.name[:-4]):
                assert os.path.isdir(each_blob.name[:-4])
            else:
                os.mkdir(each_blob.name[:-4])
            with zipfile.ZipFile(each_blob.name, 'r') as zip_ref:
                zip_ref.extractall(each_blob.name[:-4])
            src = os.path.join(each_blob.name[:-4], file_name_mapping_glue[subdat_name][0])
            dst = os.path.join(output_dir, file_name_mapping_glue[subdat_name][0])
            shutil.copy(src, dst)
        shutil.make_archive(os.path.join(output_dir), 'zip', output_dir)

    def get_best_perf_config(self, console_args, jobid_config):
        """
            get the config of the best performed trial
        """
        matched_blob_list = self.get_blob_list_matching_partial_jobid(console_args.azure_root_log_path, jobid_config)
        try:
            assert len(matched_blob_list) == 1
        except AssertionError:
            import pdb
            pdb.set_trace()

        each_jobconfig, each_blob = matched_blob_list[0]
        self.download_azure_blob(each_blob.name)
        data_json = json.load(open(each_blob.name, "r"))

        sorted_entries = sorted(data_json['val_log'], key=lambda x: x['metric_score']['max'], reverse=True)
        best_config = sorted_entries[0]['config']
        if jobid_config.subdat != "mrpc":
            best_score = sorted_entries[0]['metric_score']['max']
        else:
            best_score = (data_json["valid_metric"]["eval_f1"], data_json["valid_metric"]["eval_accuracy"])
        return best_config, best_score
