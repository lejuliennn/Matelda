import os
import pickle
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
import time

import marshmallow_pipeline.utils.app_logger
from marshmallow_pipeline.error_detection import error_detector
from marshmallow_pipeline.column_grouping_module.grouping_columns import column_grouping
from marshmallow_pipeline.table_grouping_module.grouping_tables import table_grouping
from marshmallow_pipeline.utils.saving_results import get_all_results
from marshmallow_pipeline.utils.loading_results import loading_columns_grouping_results


def init(execution):
    """
    Initialization function to set up configurations, directories, and other necessary variables.
    Loads the configuration file directly from ./config.ini

    Parameters:
        execution (int): A value representing the current execution context, used in generating output paths.

    Returns:
        dict: A dictionary containing all the configurations, paths, and settings needed for the experiment.
    """

    configs = ConfigParser()
    configs.read("./config.ini")
    labeling_budget = int(configs["EXPERIMENTS"]["labeling_budget"])
    exp_name = configs["EXPERIMENTS"]["exp_name"]
    n_cores = int(configs["EXPERIMENTS"]["n_cores"])
    save_mediate_res_on_disk = bool(int(configs["EXPERIMENTS"]["save_mediate_res_on_disk"]))
    final_result_df = bool(int(configs["EXPERIMENTS"]["final_result_df"]))
    sandbox_path = configs["DIRECTORIES"]["sandbox_dir"]
    tables_path = os.path.join(sandbox_path, configs["DIRECTORIES"]["tables_dir"])

    raha_config = {}
    raha_config['save_results'] = bool(int(configs["RAHA"]['save_results']))
    raha_config['strategy_filtering'] = bool(int(configs["RAHA"]['strategy_filtering']))
    raha_config['error_detection_algorithms'] = configs["RAHA"]['error_detection_algorithms'].split(', ')

    experiment_output_path = os.path.join(
        configs["DIRECTORIES"]["output_dir"] + f"_{execution}",
        "_"
        + exp_name
        + "_"
        + configs["DIRECTORIES"]["tables_dir"]
        + "_"
        + str(labeling_budget)
        + "_labels",
    )
    logs_dir = os.path.join(experiment_output_path, configs["DIRECTORIES"]["logs_dir"])
    results_path = os.path.join(
        experiment_output_path, configs["DIRECTORIES"]["results_dir"]
    )
    mediate_files_path = os.path.join(experiment_output_path, "mediate_files")
    aggregated_lake_path = os.path.join(
        experiment_output_path, configs["DIRECTORIES"]["aggregated_lake_path"]
    )

    os.makedirs(experiment_output_path, exist_ok=True)
    os.makedirs(results_path, exist_ok=True)
    os.makedirs(logs_dir + f"_{exp_name}", exist_ok=True)
    os.makedirs(aggregated_lake_path, exist_ok=True)
    os.makedirs(mediate_files_path, exist_ok=True)

    table_grouping_enabled = bool(int(configs["TABLE_GROUPING"]["tg_enabled"]))
    table_grouping_res_available = bool(int(configs["TABLE_GROUPING"]["tg_res_available"]))
    table_grouping_method = configs["TABLE_GROUPING"]["tg_method"]

    column_grouping_enabled = bool(int(configs["COLUMN_GROUPING"]["cg_enabled"]))
    column_grouping_res_available = bool(int(configs["COLUMN_GROUPING"]["cg_res_available"]))
    column_grouping_alg = configs["COLUMN_GROUPING"]["cg_clustering_alg"]
    min_num_labes_per_col_cluster = int(
        configs["COLUMN_GROUPING"]["min_num_labes_per_col_cluster"]
    )

    dirty_files_name = configs["DIRECTORIES"]["dirty_files_name"]
    clean_files_name = configs["DIRECTORIES"]["clean_files_name"]

    marshmallow_pipeline.utils.app_logger.setup_logging(logs_dir + f"_{exp_name}")
    logging.info("Starting the experiment")
    time_start = time.time()
    pool = multiprocessing.Pool(n_cores)

    logging.info("Symlinking sandbox to aggregated_lake_path")
    tables_dict = {}
    for name in os.listdir(tables_path):
        curr_path = os.path.join(tables_path, name)
        if os.path.isdir(curr_path):
            dirty_csv_path = os.path.join(curr_path, dirty_files_name)
            clean_csv_path = os.path.join(curr_path, clean_files_name)
            if os.path.isfile(dirty_csv_path):
                if os.path.exists(os.path.join(aggregated_lake_path, name + ".csv")):
                    os.remove(os.path.join(aggregated_lake_path, name + ".csv"))
                os.link(
                    dirty_csv_path, os.path.join(aggregated_lake_path, name + ".csv")
                )
                tables_dict[os.path.basename(curr_path)] = name + ".csv"

    if save_mediate_res_on_disk:
        with open(os.path.join(experiment_output_path, "tables_dict.pickle"), "wb+") as handle:
            pickle.dump(tables_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
    return {
        "configs": configs,
        "labeling_budget": labeling_budget,
        "exp_name": exp_name,
        "n_cores": n_cores,
        "save_mediate_res_on_disk": save_mediate_res_on_disk,
        "final_result_df": final_result_df,
        "sandbox_path": sandbox_path,
        "tables_path": tables_path,
        "raha_config": raha_config,
        "experiment_output_path": experiment_output_path,
        "logs_dir": logs_dir,
        "results_path": results_path,
        "mediate_files_path": mediate_files_path,
        "aggregated_lake_path": aggregated_lake_path,
        "table_grouping_enabled": table_grouping_enabled,
        "table_grouping_res_available": table_grouping_res_available,
        "table_grouping_method": table_grouping_method,
        "column_grouping_enabled": column_grouping_enabled,
        "column_grouping_res_available": column_grouping_res_available,
        "column_grouping_alg": column_grouping_alg,
        "min_num_labes_per_col_cluster": min_num_labes_per_col_cluster,
        "dirty_files_name": dirty_files_name,
        "clean_files_name": clean_files_name,
        "tables_dict": tables_dict
    }


def init(configs, execution):
    """
    Initialization function to set up configurations, directories, and other necessary variables.

    Parameters:
        configs (dict): The dictionary containing all the configurations.
        execution (int): A value representing the current execution context, used in generating output paths.

    Returns:
        dict: A dictionary containing all the configurations, paths, and settings needed for the experiment.
    """
    labeling_budget = int(configs["EXPERIMENTS"]["labeling_budget"])
    exp_name = configs["EXPERIMENTS"]["exp_name"]
    n_cores = int(configs["EXPERIMENTS"]["n_cores"])
    save_mediate_res_on_disk = bool(int(configs["EXPERIMENTS"]["save_mediate_res_on_disk"]))
    final_result_df = bool(int(configs["EXPERIMENTS"]["final_result_df"]))
    sandbox_path = configs["DIRECTORIES"]["sandbox_dir"]
    tables_path = os.path.join(sandbox_path, configs["DIRECTORIES"]["tables_dir"])

    raha_config = {}
    raha_config['save_results'] = bool(int(configs["RAHA"]['save_results']))
    raha_config['strategy_filtering'] = bool(int(configs["RAHA"]['strategy_filtering']))
    raha_config['error_detection_algorithms'] = configs["RAHA"]['error_detection_algorithms'].split(', ')

    experiment_output_path = os.path.join(
        configs["DIRECTORIES"]["output_dir"] + f"_{execution}",
        "_"
        + exp_name
        + "_"
        + configs["DIRECTORIES"]["tables_dir"]
        + "_"
        + str(labeling_budget)
        + "_labels",
    )
    logs_dir = os.path.join(experiment_output_path, configs["DIRECTORIES"]["logs_dir"])
    results_path = os.path.join(
        experiment_output_path, configs["DIRECTORIES"]["results_dir"]
    )
    mediate_files_path = os.path.join(experiment_output_path, "mediate_files")
    aggregated_lake_path = os.path.join(
        experiment_output_path, configs["DIRECTORIES"]["aggregated_lake_path"]
    )

    os.makedirs(experiment_output_path, exist_ok=True)
    os.makedirs(results_path, exist_ok=True)
    os.makedirs(logs_dir + f"_{exp_name}", exist_ok=True)
    os.makedirs(aggregated_lake_path, exist_ok=True)
    os.makedirs(mediate_files_path, exist_ok=True)

    table_grouping_enabled = bool(int(configs["TABLE_GROUPING"]["tg_enabled"]))
    table_grouping_res_available = bool(int(configs["TABLE_GROUPING"]["tg_res_available"]))
    table_grouping_method = configs["TABLE_GROUPING"]["tg_method"]

    column_grouping_enabled = bool(int(configs["COLUMN_GROUPING"]["cg_enabled"]))
    column_grouping_res_available = bool(int(configs["COLUMN_GROUPING"]["cg_res_available"]))
    column_grouping_alg = configs["COLUMN_GROUPING"]["cg_clustering_alg"]
    min_num_labes_per_col_cluster = int(
        configs["COLUMN_GROUPING"]["min_num_labes_per_col_cluster"]
    )

    dirty_files_name = configs["DIRECTORIES"]["dirty_files_name"]
    clean_files_name = configs["DIRECTORIES"]["clean_files_name"]

    marshmallow_pipeline.utils.app_logger.setup_logging(logs_dir + f"_{exp_name}")
    logging.info("Starting the experiment")
    time_start = time.time()
    pool = multiprocessing.Pool(n_cores)

    logging.info("Symlinking sandbox to aggregated_lake_path")
    tables_dict = {}
    for name in os.listdir(tables_path):
        curr_path = os.path.join(tables_path, name)
        if os.path.isdir(curr_path):
            dirty_csv_path = os.path.join(curr_path, dirty_files_name)
            clean_csv_path = os.path.join(curr_path, clean_files_name)
            if os.path.isfile(dirty_csv_path):
                if os.path.exists(os.path.join(aggregated_lake_path, name + ".csv")):
                    os.remove(os.path.join(aggregated_lake_path, name + ".csv"))
                os.link(
                    dirty_csv_path, os.path.join(aggregated_lake_path, name + ".csv")
                )
                tables_dict[os.path.basename(curr_path)] = name + ".csv"

    if save_mediate_res_on_disk:
        with open(os.path.join(experiment_output_path, "tables_dict.pickle"), "wb+") as handle:
            pickle.dump(tables_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
    return {
        "configs": configs,
        "labeling_budget": labeling_budget,
        "exp_name": exp_name,
        "n_cores": n_cores,
        "save_mediate_res_on_disk": save_mediate_res_on_disk,
        "final_result_df": final_result_df,
        "sandbox_path": sandbox_path,
        "tables_path": tables_path,
        "raha_config": raha_config,
        "experiment_output_path": experiment_output_path,
        "logs_dir": logs_dir,
        "results_path": results_path,
        "mediate_files_path": mediate_files_path,
        "aggregated_lake_path": aggregated_lake_path,
        "table_grouping_enabled": table_grouping_enabled,
        "table_grouping_res_available": table_grouping_res_available,
        "table_grouping_method": table_grouping_method,
        "column_grouping_enabled": column_grouping_enabled,
        "column_grouping_res_available": column_grouping_res_available,
        "column_grouping_alg": column_grouping_alg,
        "min_num_labes_per_col_cluster": min_num_labes_per_col_cluster,
        "dirty_files_name": dirty_files_name,
        "clean_files_name": clean_files_name,
        "tables_dict": tables_dict
    }


def domain_based_folding(configs, pool):
    """
    Domain-based folding function that executes the table grouping process.

    Parameters:
        configs (dict): The dictionary containing all the configurations.
        pool (multiprocessing.Pool): A multiprocessing pool to run parallel tasks.

    Returns:
        tuple: A tuple containing the table grouping dictionary and table size dictionary.
    """
    experiment_output_path = configs['experiment_output_path']
    aggregated_lake_path= configs['aggregated_lake_path']
    table_grouping_enabled = configs['table_grouping_enabled']
    table_grouping_res_available = configs['table_grouping_res_available']
    table_grouping_method = configs['table_grouping_method']
    save_mediate_res_on_disk = configs['save_mediate_res_on_disk']
    n_cores = configs['n_cores']

    column_grouping_enabled = configs['column_grouping_enabled']
    column_grouping_res_available = configs['column_grouping_res_available']
    column_grouping_alg = configs['column_grouping_alg']
    mediate_files_path = configs['mediate_files_path']
    sandbox_path = configs['sandbox_path']
    labeling_budget = configs['labeling_budget']
    min_num_labes_per_col_cluster = configs['min_num_labes_per_col_cluster']
    tables_path = configs['tables_path']

    # Table grouping
    if table_grouping_enabled:
        if not table_grouping_res_available:
            logging.info("Table grouping is enabled")
            logging.info("Table grouping results are not available")
            logging.info("Executing the table grouping")
            before_tg = time.time()
            logging.debug("Thread pool: " + str(before_tg - time.time()))
            table_g_start = time.time()

            table_grouping_dict, table_size_dict = table_grouping(
                aggregated_lake_path, experiment_output_path, table_grouping_method, save_mediate_res_on_disk, pool
            )

            table_g_time = time.time() - table_g_start
            logging.info("Table grouping is done")
            logging.info(f"Table grouping completed in {table_g_time} seconds")
        else:
            logging.info("Table grouping results are available")
            logging.info("Loading the table grouping results...")
            with open(
                os.path.join(experiment_output_path, "table_group_dict.pickle"), "rb"
            ) as handle:
                table_grouping_dict = pickle.load(handle)
            with open(
                os.path.join(experiment_output_path, "table_size_dict.pickle"),
                "rb",
            ) as handle:
                table_size_dict = pickle.load(handle)
    else:
        logging.info("Table grouping is disabled")
        table_grouping_dict = {0: []}
        table_size_dict = {0: -1}
        tables_dict = configs['tables_dict']
        tables_list = tables_dict.values()
        for table in tables_list:
            table_grouping_dict[0].append(table)
        if save_mediate_res_on_disk:
            with open(os.path.join(experiment_output_path, "table_group_dict.pickle"), "wb+") as handle:
                pickle.dump(table_grouping_dict, handle)

    logging.info("Table grouping is done")
    logging.info("I need at least 2 labeled cells per table group to work at all and at least 2 * 6 labeled cells per table group to work effectively! Thant means you need to label {} cells if you want reasonable (!) results:".format(2*6*len(table_grouping_dict)))
    print("I need at least 2 labeled cells per table group to work at all and at least 2 * 6 labeled cells per table group to work effectively! Thant means you need to label {} cells if you want reasonable (!) results:".format(2*6*len(table_grouping_dict)))
    
    # Column Grouping
    if column_grouping_enabled:
        if not column_grouping_res_available:
            logging.info("Column grouping is enabled")
            logging.info("Column grouping results are not available")
            logging.info("Executing the column grouping")

            column_grouping_start = time.time()

            column_grouping(
                aggregated_lake_path,
                table_grouping_dict,
                table_size_dict,
                sandbox_path,
                labeling_budget,
                min_num_labes_per_col_cluster,
                mediate_files_path,
                column_grouping_enabled,
                column_grouping_alg,
                n_cores,
                pool
            )

            column_grouping_time = time.time() - column_grouping_start
            logging.info(f"Column grouping completed in {column_grouping_time} seconds")
            logging.info("Column grouping results are available - loading from disk")
        else:
            # Removing Symlinks
            logging.info("Removing the symlinks")
            for name in os.listdir(tables_path):
                curr_path = os.path.join(tables_path, name)
                if os.path.isdir(curr_path):
                    aggregated_lake_path_csv = os.path.join(aggregated_lake_path, name + ".csv")
                    if os.path.exists(aggregated_lake_path_csv):
                        os.remove(aggregated_lake_path_csv)

            # Loading Column Grouping Results
            logging.info("Loading the column grouping results")
            (
                number_of_col_clusters,
                cluster_sizes_dict,
                column_groups_df_path,
            ) = loading_columns_grouping_results(table_grouping_dict, mediate_files_path)
            logging.info("Column grouping is done")
    else:
        logging.info("Column grouping is disabled")

    logging.info("Domain-based folding completed")    
    return table_grouping_dict, table_size_dict


def quality_based_folding(configs, pool):
    pass