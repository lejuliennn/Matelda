import os
import pickle
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
import time
import os
import pickle
import logging
import sys
import pandas as pd

import ipywidgets as widgets
from IPython.display import display, clear_output, HTML

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

from marshmallow_pipeline.error_detection_demo import (before_user_labeling,
                                                       error_detector)

import marshmallow_pipeline.utils.app_logger
#from marshmallow_pipeline.error_detection import error_detector
from marshmallow_pipeline.column_grouping_module.grouping_columns import column_grouping
from marshmallow_pipeline.table_grouping_module.grouping_tables import table_grouping
from marshmallow_pipeline.utils.saving_results import get_all_results
from marshmallow_pipeline.utils.loading_results import loading_columns_grouping_results
#from marshmallow_pipeline.cell_grouping_module.cell_folding import cell_cluster_sampling_labeling, cluster_column_group

from marshmallow_pipeline.cell_grouping_module.extract_table_group_charset import (
    extract_charset,
)
from marshmallow_pipeline.cell_grouping_module.generate_cell_features import (
    get_cells_features,
)
from marshmallow_pipeline.cell_grouping_module.sampling_labeling import (
    get_n_labels,
    update_n_labels,
)

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


###########################
# from error_detection.py #
###########################

"""
####################
# ToDo: Remove notes
# Note: Error Detector generates features for each cell 
# (afterwards cell clustering and then sampling labeling)
# We want to show user the cell fold
def error_detector(
    cell_feature_generator_enabled,
    sandbox_path,
    col_groups_dir,
    output_path,
    results_path,
    n_labels,
    labels_per_cell_group,
    cluster_sizes_dict,
    tables_dict,
    min_num_labes_per_col_cluster,
    dirty_files_name,
    clean_files_name,
    n_cores,
    cell_clustering_res_available,
    save_mediate_res_on_disk,
    pool,
    classification_mode,
    raha_config
):
    logging.info("Starting error detection")

    logging.info("Extracting table charsets")
    table_charset_dict = extract_charset(col_groups_dir)

    logging.info("Generating cell features")
    if cell_feature_generator_enabled:
        logging.info("Generating cell features enabled")
        features_dict, tables_tuples_dict = get_cells_features(
            sandbox_path, output_path, table_charset_dict, tables_dict, dirty_files_name, clean_files_name, save_mediate_res_on_disk, pool, raha_config
        )
    else:
        logging.info("Generating cell features disabled, loading from previous results from disk")
        with open(os.path.join(output_path, "features.pickle"), "rb") as pickle_file:
            features_dict = pickle.load(pickle_file)
        with open(os.path.join(output_path, "tables_tuples.pickle"), "rb") as pickle_file:
            tables_tuples_dict = pickle.load(pickle_file)

    logging.info("Selecting label")
    cluster_sizes_df = pd.DataFrame.from_dict(cluster_sizes_dict)
    df_n_labels = get_n_labels(
        cluster_sizes_df,
        labeling_budget=n_labels,
        min_num_labes_per_col_cluster=min_num_labes_per_col_cluster,
    )

    if not cell_clustering_res_available:
        logging.info("Cell Clustering")
        start_time = time.time()
        col_group_file_names = [file_name for file_name in os.listdir(col_groups_dir) if ".pickle" in file_name]
        n_processes = min((len(col_group_file_names), os.cpu_count()))
        # logging.debug("Number of processes: %s", str(n_processes))

        table_clusters = []
        cell_cluster_cells_dict_all = {}
        cell_clustering_dict_all = {}
        col_clusters = []
        logging.info("Number of column groups: %s", str(len(col_group_file_names)))
        logging.info("Starting parallel processing of column groups")
        # Prepare the arguments as tuples
        args = [(x, n_cores) for x in col_group_file_names]
        logging.debug("args: %s", str(args))
        # Use starmap to pass arguments as separate values
        results = []

        for x in col_group_file_names:
            results.append(cluster_column_group(col_groups_dir, df_n_labels, features_dict, labels_per_cell_group, x, n_cores))
        logging.info("Storing cluster_column_group results")
        for result in results:
            if result is not None:
                table_clusters.append(result["table_cluster"])
                cell_cluster_cells_dict_all.update(result["cell_cluster_cells_dict_all"])
                cell_clustering_dict_all.update(result["cell_clustering_dict_all"])
                col_clusters.append(result["col_clusters"])


        all_cell_clusters_records = []
        for table_group in cell_clustering_dict_all:
            for col_group in cell_clustering_dict_all[table_group]:
                all_cell_clusters_records.append(cell_clustering_dict_all[table_group][col_group])

        all_cell_clusters_records = update_n_labels(all_cell_clusters_records)
        cell_clustering_dir = os.path.join(output_path, "cell_clustering")
        end_time = time.time()
        logging.info("Cell Clustering took %s seconds", str(end_time - start_time))
        if save_mediate_res_on_disk:
            logging.info("Saving cell clustering results")
            if not os.path.exists(cell_clustering_dir):
                os.makedirs(cell_clustering_dir)
            with open(
                os.path.join(cell_clustering_dir, "all_cell_clusters_records.pickle"), "wb"
            ) as pickle_file:
                pickle.dump(all_cell_clusters_records, pickle_file)
            with open(
                os.path.join(cell_clustering_dir, "cell_cluster_cells_dict_all.pickle"), "wb"
            ) as pickle_file:
                pickle.dump(cell_cluster_cells_dict_all, pickle_file)
    else:
        ############################################
        # ToDo: 
        # Here is the part I have to show the user 
        # Look into the dictionaries and find what we want to show the user
        # Look into structure of pickle files before running the code and understand them
        #
        # -> In the Diagram (Draw.IO) it's Step 2 

        logging.info("Loading cell clustering results from disk")
        with open(
            os.path.join(output_path, "cell_clustering", "all_cell_clusters_records.pickle"), "rb"
        ) as pickle_file:
            # look in dics -> find out which cells are there
            all_cell_clusters_records = pickle.load(pickle_file)
        with open(
            os.path.join(output_path, "cell_clustering", "cell_cluster_cells_dict_all.pickle"), "rb"
        ) as pickle_file:
            # or this dict
            cell_cluster_cells_dict_all = pickle.load(pickle_file)

        # Until here you can achive cluster resluts
        #
        # visualize this part until here (Step 2 in Diagram of DrawIO)
        # call the error function from here directly or 
        # create a new function for this in the pipeline.py file  
        #
        # when calling the function from directly here, maybe comment out the sampling / labeling
        # part below. Makes implementation easier
        ############################################

    ###########################
    # Next Week: Sampling / Labeling 

    logging.info("Sampling and labeling clusters")
    start_time = time.time()    
    original_data_keys = []
    unique_cells_local_index_collection = {}
    predicted_all = {}
    y_test_all = {}
    y_local_cell_ids = {}
    X_labeled_by_user_all = {}
    y_labeled_by_user_all = {}
    selected_samples = {}
    used_labels = 0
    logging.info("Starting processing of cell clusters")
    results = []
    for table_cluster in cell_cluster_cells_dict_all:
        for col_cluster in cell_cluster_cells_dict_all[table_cluster]:
            result = test(df_n_labels, output_path, all_cell_clusters_records, cell_cluster_cells_dict_all, n_cores, save_mediate_res_on_disk, classification_mode, tables_tuples_dict, labels_per_cell_group, col_cluster, table_cluster)
            results.append(result)
    n_user_labeled_cells = 0
    for result in results:
        if result is not None:
            original_data_keys.append(result["original_data_keys"])
            unique_cells_local_index_collection.update(result["unique_cells_local_index_collection"])
            predicted_all.update(result["predicted_all"])
            y_test_all.update(result["y_test_all"])
            y_local_cell_ids.update(result["y_local_cell_ids"])
            X_labeled_by_user_all.update(result["X_labeled_by_user_all"])
            y_labeled_by_user_all.update(result["y_labeled_by_user_all"])
            selected_samples.update(result["selected_samples"])
            used_labels += result["used_labels"]
            n_user_labeled_cells += result["n_user_labeled_cells"]
            logging.info("Number of used Labeled Cells: %s", str(result["used_labels"]))
            logging.info("Len selected_samples: %s", str(len(result["selected_samples"])))
            logging.info("Number of Labeled Cells (user): %s", str(result["n_user_labeled_cells"]))

    end_time = time.time()
    logging.info("Sampling and labeling clusters took %s seconds", str(end_time - start_time))
    logging.info("Saving results")
    if save_mediate_res_on_disk:
        with open(os.path.join(output_path, "original_data_keys.pkl"), "wb") as filehandler:
            pickle.dump(original_data_keys, filehandler)

        with open(os.path.join(results_path, "sampled_tuples.pkl"), "wb") as filehandler:
            pickle.dump(selected_samples, filehandler)
            logging.info("Number of Labeled Cells: %s", len(selected_samples))

        with open(os.path.join(output_path, "df_n_labels.pkl"), "wb") as filehandler:
            pickle.dump(df_n_labels, filehandler)

    return (
        y_test_all,
        y_local_cell_ids,
        predicted_all,
        y_labeled_by_user_all,
        unique_cells_local_index_collection,
        selected_samples,
        n_user_labeled_cells,
    )
"""

def test(df_n_labels, output_path, all_cell_clusters_records, cell_cluster_cells_dict_all, n_cores, save_mediate_res_on_disk, classification_mode, tables_tuples_dict, labels_per_cell_group, col_cluster, table_cluster):
    logging.info("Starting test; Column cluster: %s; Table cluster %s", col_cluster, table_cluster)
    original_data_keys = []
    unique_cells_local_index_collection = {}
    predicted_all = {}
    y_test_all = {}
    y_local_cell_ids = {}
    X_labeled_by_user_all = {}
    y_labeled_by_user_all = {}
    selected_samples = {}
    used_labels = 0

    cell_clustering_df = all_cell_clusters_records[
        (all_cell_clusters_records["table_cluster"] == table_cluster)
        & (all_cell_clusters_records["col_cluster"] == col_cluster)
    ]
    cell_cluster_cells_dict = cell_cluster_cells_dict_all[table_cluster][
        col_cluster
    ]
    cell_cluster_sampling_labeling_dict, cell_clustering_df, samples_dict, n_user_labeled_cells = cell_cluster_sampling_labeling(
        cell_clustering_df, cell_cluster_cells_dict, n_cores, classification_mode, tables_tuples_dict, labels_per_cell_group, output_path
    )

    if save_mediate_res_on_disk:
        cell_clustering_dir = os.path.join(output_path, "cell_clustering")
        if not os.path.exists(cell_clustering_dir):
            os.makedirs(cell_clustering_dir)
        with open(
            os.path.join(
                cell_clustering_dir,
                f"cell_cluster_sampling_labeling_dict_{table_cluster}_{col_cluster}.pickle",
            ),
            "wb",
        ) as pickle_file:
            pickle.dump(cell_cluster_sampling_labeling_dict, pickle_file)

        with open(
            os.path.join(
                cell_clustering_dir,
                f"samples_dict_{table_cluster}_{col_cluster}.pickle",
            ),
            "wb",
        ) as pickle_file:
            pickle.dump(samples_dict, pickle_file)
        
        with open(
            os.path.join(
                cell_clustering_dir,
                f"cell_clustering_df_{table_cluster}_{col_cluster}.pickle",
            ),
            "wb",
        ) as pickle_file:
            pickle.dump(cell_clustering_df, pickle_file)

    X_labeled_by_user = cell_cluster_sampling_labeling_dict["X_labeled_by_user"]

    used_labels += len(X_labeled_by_user) if X_labeled_by_user is not None else 0
    df_n_labels.loc[
        (df_n_labels["table_cluster"] == table_cluster)
        & (df_n_labels["col_cluster"] == col_cluster),
        "sampled",
    ] = True
    if X_labeled_by_user is not None:
        selected_samples.update(
            cell_cluster_sampling_labeling_dict["universal_samples"]
        )
        original_data_keys.extend(
            cell_cluster_sampling_labeling_dict["original_data_keys_temp"]
        )

        X_labeled_by_user_all[
            (str(table_cluster), str(col_cluster))
        ] = X_labeled_by_user
        y_labeled_by_user_all[
            (str(table_cluster), str(col_cluster))
        ] = cell_cluster_sampling_labeling_dict["y_labeled_by_user"]

        predicted_all[
            (str(table_cluster), str(col_cluster))
        ] = cell_cluster_sampling_labeling_dict["predicted"]
        y_test_all[
            (str(table_cluster), str(col_cluster))
        ] = cell_cluster_sampling_labeling_dict["y_test"]
        y_local_cell_ids[
            (str(table_cluster), str(col_cluster))
        ] = cell_cluster_sampling_labeling_dict["y_cell_ids"]
        unique_cells_local_index_collection[
            (str(table_cluster), str(col_cluster))
        ] = cell_cluster_sampling_labeling_dict["datacells_uids"]

    init_labels_tg_cg = df_n_labels[(df_n_labels["table_cluster"] == table_cluster) & (df_n_labels["col_cluster"] == col_cluster)]["n_labels"].values[0]

    logging.info("Done test; Column cluster: %s; Table cluster %s; Used labels %s , Init labels: %s", col_cluster, table_cluster, str(len(X_labeled_by_user) if X_labeled_by_user is not None else 0), init_labels_tg_cg)
    
    return {"original_data_keys": original_data_keys, "unique_cells_local_index_collection": unique_cells_local_index_collection, "predicted_all": predicted_all, "y_test_all": y_test_all, "y_local_cell_ids": y_local_cell_ids, "X_labeled_by_user_all": X_labeled_by_user_all, "y_labeled_by_user_all": y_labeled_by_user_all, "selected_samples": selected_samples, "used_labels": used_labels, "n_user_labeled_cells": n_user_labeled_cells}




def quality_based_folding(configs, pool, column_groups_df_path, cluster_sizes_dict):
    """
    Quality based folding function that performs error detection and cell folding based on cell quality.
    It leverages the error_detector function to generate cell features, cluster cells, and perform sampling and labeling.

    Parameters:
        configs (dict): Dictionary containing all configurations and paths.
            This dictionary includes both a flattened set of keys (e.g., "sandbox_path", "n_cores", etc.)
            and the original configuration data (either as a ConfigParser object or as a dictionary)
            stored under the key "configs".
        pool (multiprocessing.Pool): A multiprocessing pool for parallel processing.
        column_groups_df_path (str): Path to the file with column grouping results (used for cell grouping).
        cluster_sizes_dict (dict): Dictionary containing the sizes of the column clusters.

    Returns:
        tuple: A tuple containing the following elements:
            - y_test_all: Ground truth labels for each cell.
            - y_local_cell_ids: Local cell identifiers.
            - predicted_all: Predicted labels for each cell.
            - y_labeled_by_user_all: Labels provided by the user.
            - unique_cells_local_index_collection: Mapping of unique cell indexes.
            - selected_samples: Samples selected for further review.
            - n_user_labeled_cells: Total number of cells labeled by the user.
    """
    logging.info("Starting quality based folding")

    # Retrieve the original configuration data (it may be a ConfigParser or a plain dict)
    cp = configs["configs"]
   
    cell_feature_generator_enabled = bool(int(cp["CELL_GROUPING"].get("cell_feature_generator_enabled", 0)))
    cell_clustering_res_available = bool(int(cp["CELL_GROUPING"].get("cell_clustering_res_available", 0)))
    classification_mode = int(cp["CELL_GROUPING"].get("classification_mode", 1))
    labels_per_cell_group = int(cp["CELL_GROUPING"].get("labels_per_cell_group", 6))

    # Retrieve additional parameters from the flattened configuration
    sandbox_path = configs["sandbox_path"]
    experiment_output_path = configs["experiment_output_path"]
    results_path = configs["results_path"]
    labeling_budget = configs["labeling_budget"]
    min_num_labes_per_col_cluster = configs["min_num_labes_per_col_cluster"]
    tables_dict = configs["tables_dict"]
    dirty_files_name = configs["dirty_files_name"]
    clean_files_name = configs["clean_files_name"]
    n_cores = configs["n_cores"]
    save_mediate_res_on_disk = configs["save_mediate_res_on_disk"]
    raha_config = configs["raha_config"]

    # Log the required number of labeled cells.
    #n_table_groups = len(tables_dict) if tables_dict else 1
    #required_labels = 2 * 6 * n_table_groups
    #logging.info(
    #    f"I need at least 2 labeled cells per table group and at least 2 * 6 labeled cells per table group, "
    #    f"i.e., {required_labels} cells, for reasonable results."
    #)

    tables_path = os.path.join(sandbox_path, cp["DIRECTORIES"]["tables_dir"])
    min_n_labels_per_cell_group = int(cp["CELL_GROUPING"]["labels_per_cell_group"])
    final_result_df = bool(int(cp["EXPERIMENTS"]["final_result_df"]))
    results_path = os.path.join(experiment_output_path, cp["DIRECTORIES"]["results_dir"])

    logging.info("Starting error detection")

    
    domain_fold_samples, domain_fold_obj_all, original_data_keys, unique_cells_local_index_collection, predicted_all, y_test_all, y_local_cell_ids, X_labeled_by_user_all, y_labeled_by_user_all, selected_samples, used_labels, cell_cluster_cells_dict_all, df_n_labels =  \
    before_user_labeling(column_groups_df_path, experiment_output_path, tables_path, dirty_files_name, 
                         clean_files_name, n_cores, labeling_budget, min_n_labels_per_cell_group, 
                         cluster_sizes_dict, tables_dict, min_num_labes_per_col_cluster, 
                         cell_feature_generator_enabled, cell_clustering_res_available,
                         save_mediate_res_on_disk, pool, raha_config
                         )
    
    # Julian what you need to do is to update domain_fold_samples here and pass it to the next method. 
    # The dictionary should be updated with the new labels.
    # The structure is like this: {(Domain Fold ID): {(table_id, column_id, row_id): (cell_group_id, sample_index, label)}}
    # see "/home/fatemeh/Julian/Matelda/output_qrm/output_qrm_0/_test_edbt_QRM_200_labels/domain_fold_samples.pickle" for a sample file

    # Call error_detector
    (
        y_test_all,
        y_local_cell_ids,
        predicted_all,
        y_labeled_by_user_all,
        unique_cells_local_index_collection,
        samples, global_n_userl_labels
    ) = error_detector(
        experiment_output_path,
        results_path,
        save_mediate_res_on_disk,
        classification_mode,
        cell_cluster_cells_dict_all,
        df_n_labels,
        domain_fold_samples,
        domain_fold_obj_all,
    )

    logging.info("Quality based folding completed")

    logging.info("Saving the results")
    final_results_path = os.path.join(results_path, "final_results")
    os.makedirs(final_results_path, exist_ok=True)
    with open(os.path.join(final_results_path, "tables_dict.pickle"), "wb+") as handle:
        pickle.dump(tables_dict, handle)
    with open(os.path.join(final_results_path, "y_test_all.pickle"), "wb+") as handle:
        pickle.dump(y_test_all, handle)
    with open(os.path.join(final_results_path, "y_local_cell_ids.pickle"), "wb+") as handle:
        pickle.dump(y_local_cell_ids, handle)
    with open(os.path.join(final_results_path, "predicted_all.pickle"), "wb+") as handle:
        pickle.dump(predicted_all, handle)
    with open(os.path.join(final_results_path, "y_labeled_by_user_all.pickle"), "wb+") as handle:
        pickle.dump(y_labeled_by_user_all, handle)
    with open(os.path.join(final_results_path, "unique_cells_local_index_collection.pickle"), "wb+") as handle:
        pickle.dump(unique_cells_local_index_collection, handle)
    with open(os.path.join(final_results_path, "samples.pickle"), "wb+") as handle:
        pickle.dump(samples, handle)

    logging.info("Getting results")
    get_all_results(
        tables_dict,
        tables_path,
        results_path,
        y_test_all,
        y_local_cell_ids,
        predicted_all,
        y_labeled_by_user_all,
        unique_cells_local_index_collection,
        samples,
        dirty_files_name,
        clean_files_name, 
        final_result_df
    )

    logging.info(f"Number of user labeled cells: {global_n_userl_labels}")

    # Return the results so they can be inspected in the notebook
    return (y_test_all, y_local_cell_ids, predicted_all, y_labeled_by_user_all,
            unique_cells_local_index_collection, samples, global_n_userl_labels)


### ToDo: Remove quality based folding: the complete function which is not separated into two parts

def quality_based_folding_part_one(configs, pool, column_groups_df_path, cluster_sizes_dict):
    """
    Quality based folding function that performs error detection and cell folding based on cell quality.
    It leverages the error_detector function to generate cell features, cluster cells, and perform sampling and labeling.

    Parameters:
        configs (dict): Dictionary containing all configurations and paths.
            This dictionary includes both a flattened set of keys (e.g., "sandbox_path", "n_cores", etc.)
            and the original configuration data (either as a ConfigParser object or as a dictionary)
            stored under the key "configs".
        pool (multiprocessing.Pool): A multiprocessing pool for parallel processing.
        column_groups_df_path (str): Path to the file with column grouping results (used for cell grouping).
        cluster_sizes_dict (dict): Dictionary containing the sizes of the column clusters.

    Returns:
        tuple: A tuple containing the following elements:
            - y_test_all: Ground truth labels for each cell.
            - y_local_cell_ids: Local cell identifiers.
            - predicted_all: Predicted labels for each cell.
            - y_labeled_by_user_all: Labels provided by the user.
            - unique_cells_local_index_collection: Mapping of unique cell indexes.
            - selected_samples: Samples selected for further review.
            - n_user_labeled_cells: Total number of cells labeled by the user.
    """
    logging.info("Starting quality based folding")

    # Retrieve the original configuration data (it may be a ConfigParser or a plain dict)
    cp = configs["configs"]
   
    cell_feature_generator_enabled = bool(int(cp["CELL_GROUPING"].get("cell_feature_generator_enabled", 0)))
    cell_clustering_res_available = bool(int(cp["CELL_GROUPING"].get("cell_clustering_res_available", 0)))
    classification_mode = int(cp["CELL_GROUPING"].get("classification_mode", 1))
    labels_per_cell_group = int(cp["CELL_GROUPING"].get("labels_per_cell_group", 6))

    # Retrieve additional parameters from the flattened configuration
    sandbox_path = configs["sandbox_path"]
    experiment_output_path = configs["experiment_output_path"]
    results_path = configs["results_path"]
    labeling_budget = configs["labeling_budget"]
    min_num_labes_per_col_cluster = configs["min_num_labes_per_col_cluster"]
    tables_dict = configs["tables_dict"]
    dirty_files_name = configs["dirty_files_name"]
    clean_files_name = configs["clean_files_name"]
    n_cores = configs["n_cores"]
    save_mediate_res_on_disk = configs["save_mediate_res_on_disk"]
    raha_config = configs["raha_config"]

    tables_path = os.path.join(sandbox_path, cp["DIRECTORIES"]["tables_dir"])
    min_n_labels_per_cell_group = int(cp["CELL_GROUPING"]["labels_per_cell_group"])
    final_result_df = bool(int(cp["EXPERIMENTS"]["final_result_df"]))
    results_path = os.path.join(experiment_output_path, cp["DIRECTORIES"]["results_dir"])

    logging.info("Starting quality-based folding part one (pre-labeling)")

    # Call the function that does all the work until user labeling.
    # This returns a tuple of:
    # (domain_fold_samples, domain_fold_obj_all, original_data_keys,
    #  unique_cells_local_index_collection, predicted_all, y_test_all, y_local_cell_ids,
    #  X_labeled_by_user_all, y_labeled_by_user_all, selected_samples, used_labels,
    #  cell_cluster_cells_dict_all, df_n_labels)
    intermediate_results = before_user_labeling(
         column_groups_df_path,
         experiment_output_path,
         tables_path,
         dirty_files_name,
         clean_files_name,
         n_cores,
         labeling_budget,
         min_n_labels_per_cell_group,
         cluster_sizes_dict,
         tables_dict,
         min_num_labes_per_col_cluster,
         cell_feature_generator_enabled,
         cell_clustering_res_available,
         save_mediate_res_on_disk,
         pool,
         raha_config
    )

    # Return all intermediate data so that it can be visualized and labeled.
    return intermediate_results


    
    #domain_fold_samples, domain_fold_obj_all, original_data_keys, unique_cells_local_index_collection, predicted_all, y_test_all, y_local_cell_ids, X_labeled_by_user_all, y_labeled_by_user_all, selected_samples, used_labels, cell_cluster_cells_dict_all, df_n_labels =  \
    #before_user_labeling(column_groups_df_path, experiment_output_path, tables_path, dirty_files_name, 
    #                     clean_files_name, n_cores, labeling_budget, min_n_labels_per_cell_group, 
    #                     cluster_sizes_dict, tables_dict, min_num_labes_per_col_cluster, 
    #                     cell_feature_generator_enabled, cell_clustering_res_available,
    #                     save_mediate_res_on_disk, pool, raha_config
    #                     )
    

    # HERE SHOULD BE THE END OF THE FIRST FUNCTION AND IT SHOULD RETURN ALL THE DATA
    # so that i can visualize it later and show it to the user in the pipeline-notebook.ipynb

    # -------------------------------------
    # start of new function: ..._part_two()


    # Julian what you need to do is to update domain_fold_samples here and pass it to the next method. 
    # The dictionary should be updated with the new labels.
    # The structure is like this: {(Domain Fold ID): {(table_id, column_id, row_id): (cell_group_id, sample_index, label)}}
    # see "/home/fatemeh/Julian/Matelda/output_qrm/output_qrm_0/_test_edbt_QRM_200_labels/domain_fold_samples.pickle" for a sample file
    
def quality_based_folding_part_two(configs, intermediate_results):
    """
    Part Two of quality-based folding.
    This function accepts the intermediate results (which now include user-updated labels in domain_fold_samples)
    and continues with error detection and the remaining processing steps.
    
    Parameters:
      - configs: configuration dictionary.
      - intermediate_results: the tuple returned by part one, where the first element (domain_fold_samples)
                              has been updated by the user.
                              
    Returns:
      A tuple with the final results (e.g. y_test_all, y_local_cell_ids, predicted_all, etc.).
    """

    # Unpack the intermediate results.
    (domain_fold_samples,
     domain_fold_obj_all,
     original_data_keys,
     unique_cells_local_index_collection,
     predicted_all,
     y_test_all,
     y_local_cell_ids,
     X_labeled_by_user_all,
     y_labeled_by_user_all,
     selected_samples,
     used_labels,
     cell_cluster_cells_dict_all,
     df_n_labels) = intermediate_results
     
    cp = configs["configs"]
    experiment_output_path = configs["experiment_output_path"]
    results_path = configs["results_path"]
    save_mediate_res_on_disk = configs["save_mediate_res_on_disk"]
    classification_mode = int(cp["CELL_GROUPING"].get("classification_mode", 1))
    tables_dict = configs["tables_dict"]
    dirty_files_name = configs["dirty_files_name"]
    clean_files_name = configs["clean_files_name"]
    final_result_df = bool(int(cp["EXPERIMENTS"]["final_result_df"]))
    
    logging.info("Starting quality-based folding part two (post-labeling)")

    # Continue with error detection using the (now labeled) domain_fold_samples.
    (y_test_all,
     y_local_cell_ids,
     predicted_all,
     y_labeled_by_user_all,
     unique_cells_local_index_collection,
     samples,
     global_n_userl_labels) = error_detector(
         experiment_output_path,
         results_path,
         save_mediate_res_on_disk,
         classification_mode,
         cell_cluster_cells_dict_all,
         df_n_labels,
         domain_fold_samples,    # UPDATED samples with user labels
         domain_fold_obj_all
    )
    
    logging.info("Quality-based folding part two completed")

    # Save final results.
    final_results_path = os.path.join(results_path, "final_results")
    os.makedirs(final_results_path, exist_ok=True)
    with open(os.path.join(final_results_path, "tables_dict.pickle"), "wb+") as handle:
        pickle.dump(tables_dict, handle)
    with open(os.path.join(final_results_path, "y_test_all.pickle"), "wb+") as handle:
        pickle.dump(y_test_all, handle)
    with open(os.path.join(final_results_path, "y_local_cell_ids.pickle"), "wb+") as handle:
        pickle.dump(y_local_cell_ids, handle)
    with open(os.path.join(final_results_path, "predicted_all.pickle"), "wb+") as handle:
        pickle.dump(predicted_all, handle)
    with open(os.path.join(final_results_path, "y_labeled_by_user_all.pickle"), "wb+") as handle:
        pickle.dump(y_labeled_by_user_all, handle)
    with open(os.path.join(final_results_path, "unique_cells_local_index_collection.pickle"), "wb+") as handle:
        pickle.dump(unique_cells_local_index_collection, handle)
    with open(os.path.join(final_results_path, "samples.pickle"), "wb+") as handle:
        pickle.dump(samples, handle)
    
    # Optionally, call a helper to gather and display final results.
    get_all_results(
        tables_dict,
        os.path.join(configs["sandbox_path"], cp["DIRECTORIES"]["tables_dir"]),
        results_path,
        y_test_all,
        y_local_cell_ids,
        predicted_all,
        y_labeled_by_user_all,
        unique_cells_local_index_collection,
        samples,
        dirty_files_name,
        clean_files_name,
        final_result_df
    )
    
    logging.info(f"Number of user labeled cells: {global_n_userl_labels}")
    
    return (y_test_all, y_local_cell_ids, predicted_all, y_labeled_by_user_all,
            unique_cells_local_index_collection, samples, global_n_userl_labels)
