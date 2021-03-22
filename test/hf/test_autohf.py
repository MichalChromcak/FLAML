'''Require: pip install torch transformers datasets flaml[blendsearch,ray]
'''
import ray

from flaml.nlp.autohf import AutoHuggingFace

def test_electra(method='BlendSearch'):
    # setting wandb key
    wandb_key = "f38cc048c956367de27eeb2749c23e6a94519ab8"

    autohf = AutoHuggingFace()

    preparedata_setting = {
        "dataset_config": {"task": "text-classification",
                            "dataset_name": ["glue"],
                            "subdataset_name": "rte"},
        "model_name": "google/mobilebert-uncased",
        "split_mode": "origin",
        "output_path": "../../../data/",
        "max_seq_length": 128,
    }

    train_dataset, eval_dataset, test_dataset =\
        autohf.prepare_data(**preparedata_setting)

    autohf_settings = {"metric_name": "accuracy",
                       "mode_name": "max",
                       "resources_per_trial": {"cpu": 2},
                       "wandb_key": wandb_key,
                       "search_algo": method,
                       "num_samples": 1,
                       "time_budget": 7200,
                       "fp16": False,
                       "points_to_evaluate": [{
                           "num_train_epochs": 1,
                           "per_device_train_batch_size": 16, }]
                       }

    autohf.fit(train_dataset,
               eval_dataset,
               **autohf_settings,)

    predictions = autohf.predict(test_dataset)

if __name__ == "__main__":
    test_electra()
