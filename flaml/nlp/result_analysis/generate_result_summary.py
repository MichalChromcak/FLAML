
def extract_ranked_config_score(console_args, partial_config_dict):
    from .azure_utils import AzureUtils
    import numpy as np
    azure_utils = AzureUtils(console_args)

    for method, each_partial_config in partial_config_dict.items():
        dataset2configscorelist = azure_utils.get_config_and_score_from_partial_config(each_partial_config, ["dat", "subdat"], method)
        for each_dataset, configscorelist in dataset2configscorelist.items():
            for config_idx in range(len(configscorelist)):
                avg_scores = configscorelist[config_idx][0][1]
                top_config = configscorelist[config_idx][0][0]
                # print(method + "," + str(each_dataset) + ",rep=" + str(config_idx))
                # print("avg score :" + str(avg_scores))
                # print(''.join(['{0}={1}\n'.format(key, top_config[key]) for key in sorted(top_config.keys())]))

def extract_sorted_config_list(dataset2configscorelist, topk):
    dataset2topkconfigs = {}
    for dataset, configscorelist in dataset2configscorelist.items():
        all_configscorelist = []
        for scorelist in configscorelist:
            for item in scorelist:
                if item[0] not in [x[0] for x in all_configscorelist]:
                    all_configscorelist.append(item)
        sorted_all_configscorelist = sorted(all_configscorelist, key = lambda x:x[1], reverse = True)
        topk_configs = []

        for each_hp in ("learning_rate", "num_train_epochs", "per_device_train_batch_size", "warmup_ratio", "weight_decay", "adam_epsilon"):
            topk_configs.append((each_hp, [sorted_all_configscorelist[x][0][each_hp] for x in range(topk)]))
        topk_configs.append(("perf", [sorted_all_configscorelist[x][1] for x in range(topk)]))

        dataset2topkconfigs[dataset] = topk_configs
    return dataset2topkconfigs

def dict2tuple(this_dict):
    tuple_list = []
    for key in sorted(this_dict.keys()):
        tuple_list.append(this_dict[key])
    return tuple(tuple_list)

def merge_configscore_list(small_dataset2configscorelist):
    dataset2merged_configscorelist = {}
    for (dataset, each_configscore_list) in small_dataset2configscorelist.items():
        merged_configscore_list = {}
        for rep_id in range(len(each_configscore_list)):
            for each_configscore_entry in each_configscore_list[rep_id]:
                is_exist = False
                for configscore in merged_configscore_list.keys():
                    if configscore[0] == each_configscore_entry[0]:
                        is_exist = True
                        break
                if is_exist is False:
                    merged_configscore_list[dict2tuple(each_configscore_entry[0])] = each_configscore_entry[1]
        dataset2merged_configscorelist[dataset] = merged_configscore_list
    return dataset2merged_configscorelist

def compare_small_vs_large(console_args):
    from .azure_utils import AzureUtils, JobID
    azure_utils = AzureUtils(console_args)

    # partial_jobid_config = JobID()
    # partial_jobid_config.pre = "funnel"
    # partial_jobid_config.mod = "list"
    # partial_jobid_config.spa = "uni"
    # partial_jobid_config.presz = "xlarge"
    #
    # small_large_dataset2configscorelist = azure_utils.get_config_and_score_from_partial_config(partial_jobid_config,
    #                                                                                           ["dat", "subdat"], "list")
    # small_large_merged_configscorelist = merge_configscore_list(small_large_dataset2configscorelist)
    #
    # partial_jobid_config = JobID()
    # partial_jobid_config.pre = "funnel"
    # partial_jobid_config.mod = "list"
    # partial_jobid_config.spa = "uni"
    # partial_jobid_config.presz = "small"
    #
    # only_small_dataset2configscorelist = azure_utils.get_config_and_score_from_partial_config(partial_jobid_config,
    #                                                                                      ["dat", "subdat"], "list")
    #
    # only_small_merged_configscorelist = merge_configscore_list(only_small_dataset2configscorelist)

    partial_jobid_config = JobID()
    partial_jobid_config.pre = "deberta"
    partial_jobid_config.mod = "hpo"
    partial_jobid_config.spa = "uni"
    partial_jobid_config.presz = "base"

    small_dataset2configscorelist = azure_utils.get_config_and_score_from_partial_config(partial_jobid_config,
                                                                                   ["dat", "subdat"], "list")

    small_mergedconfiglist = merge_configscore_list(small_dataset2configscorelist)

    partial_jobid_config = JobID()
    partial_jobid_config.pre = "deberta"
    partial_jobid_config.mod = "hpo"
    partial_jobid_config.spa = "uni"
    partial_jobid_config.presz = "large"

    large_dataset2configscorelist = azure_utils.get_config_and_score_from_partial_config(partial_jobid_config,
                                                                                         ["dat", "subdat"], "hpo")

    large_mergedconfiglist = merge_configscore_list(large_dataset2configscorelist)

    for (each_dataset, merged_small_configlist) in small_mergedconfiglist.items():
        merged_large_configlist = large_mergedconfiglist[each_dataset]
        print(each_dataset)
        print()
        for (each_tuple, large_score) in sorted(merged_large_configlist.items(), key = lambda x:x[1], reverse=True):
            #small_score = merged_small_configlist[each_tuple]
            is_in_onlysmall = each_tuple in small_mergedconfiglist[each_dataset]
            for each_val in each_tuple:
                print(each_val, end=", ")
            print(large_score, is_in_onlysmall, sep=",")
        print()
        for (each_tuple, small_score) in sorted(small_mergedconfiglist[each_dataset].items(), key = lambda x:x[1], reverse=True):
            is_in_large = each_tuple in large_mergedconfiglist[each_dataset]
            for each_val in each_tuple:
                print(each_val, end=", ")
            print(small_score, is_in_large, sep=",")
