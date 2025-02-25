import os
from configparser import ConfigParser
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML, Javascript
import pickle
import pandas as pd
import hashlib

def configparser_to_dict(config):
    """
    Convert a ConfigParser object into a dictionary.
    """
    d = {}
    for section in config.sections():
        d[section] = {}
        for key, value in config.items(section):
            d[section][key] = value
    return d

def get_full_name(key):
    """
    Convert a snake_case key into a human-readable title.
    """
    return " ".join(word.capitalize() for word in key.split("_"))

def build_config_widget(default_configs):
    """
    Build and return a widget containing configuration UI elements,
    grouped in an Accordion with control buttons.
    Once the user clicks 'Save', the updated configuration is attached
    to the returned widget (as the attribute 'updated_config').
    """
    default_config_dict = configparser_to_dict(default_configs)
    
    # Dictionary to hold widget references by section and key.
    widget_config = {}
    
    # Layout definitions for labels and inputs.
    label_layout = widgets.Layout(width='250px')
    input_layout = widgets.Layout(width='200px')
    
    # Build table-like rows for each configuration parameter.
    for section, params in default_config_dict.items():
        widget_config[section] = {}
        rows = []
        for key, value in params.items():
            label_widget = widgets.Label(value=get_full_name(key), layout=label_layout)
            # Use a Text widget for simplicity; adjust if you want specific types.
            input_widget = widgets.Text(value=str(value), layout=input_layout)
            widget_config[section][key] = input_widget
            row = widgets.HBox(
                [label_widget, input_widget],
                layout=widgets.Layout(width='100%', align_items='flex-start', margin='2px 0')
            )
            rows.append(row)
        # Group the rows for each section in a VBox.
        widget_config[section]['_box'] = widgets.VBox(rows, layout=widgets.Layout(width='100%'))
    
    # Create an Accordion to group configuration sections.
    sections_list = list(widget_config.keys())
    accordion = widgets.Accordion(
        children=[widget_config[sec]['_box'] for sec in sections_list],
        layout=widgets.Layout(width='100%')
    )
    for idx, sec in enumerate(sections_list):
        accordion.set_title(idx, sec)
    
    # Create control buttons and a loading output area.
    loading_output = widgets.Output()
    
    save_button = widgets.Button(
        description="Save Config",
        button_style="success",
        layout=widgets.Layout(width='auto', margin='10px 0')
    )
    
    reset_button = widgets.Button(
        description="Reset to Default",
        button_style="warning",
        layout=widgets.Layout(width='auto', margin='10px 0 10px 10px')
    )
    
    # Define the Save button callback.
    def on_save_button_clicked(b):
        save_button.disabled = True
        loading_output.clear_output()
        with loading_output:
            print("Loading configuration, please wait...")
        
        # Gather the updated configuration from the widgets.
        new_config = {}
        for section in widget_config:
            new_config[section] = {}
            for key, widget_item in widget_config[section].items():
                if key == '_box':
                    continue
                new_config[section][key] = widget_item.value

        # For demonstration we simply assign the new configuration as the updated configuration.
        updated_config = new_config  
        
        # Attach the updated configuration to the top-level widget.
        top_level.updated_config = updated_config
        
        loading_output.clear_output()
        with loading_output:
            print("Configuration saved!")
        
        save_button.disabled = False
        # Optionally, run the next cell automatically.
        display(Javascript('''
            if (window.jupyterapp && window.jupyterapp.commands) {
                window.jupyterapp.commands.execute("notebook:run-cell-and-select-next");
            } else {
                alert("Continue with the next cell please.");
            }
        '''))
    
    save_button.on_click(on_save_button_clicked)
    
    # Define the Reset button callback.
    def on_reset_button_clicked(b):
        for section, params in default_config_dict.items():
            for key, default_value in params.items():
                widget_config[section][key].value = default_value
        loading_output.clear_output()
        with loading_output:
            print("Configuration reset to default.")
    
    reset_button.on_click(on_reset_button_clicked)
    
    button_box = widgets.HBox(
        [save_button, reset_button],
        layout=widgets.Layout(justify_content='flex-start')
    )
    
    header = widgets.HTML("<h2>Configuration</h2>")
    
    # Create a top-level container for everything.
    top_level = widgets.VBox(
        [header, accordion, button_box, loading_output],
        layout=widgets.Layout(width='100%')
    )
    
    # Initialize the updated_config attribute to None.
    top_level.updated_config = None
    
    return top_level

def get_config_widget(default_configs):
    """
    Public function that returns the configuration widget.
    """
    return build_config_widget(default_configs)

def create_table_content_widget(csv_file, base_csv_dir, clean_file_name):
    """
    Create an interactive output widget for previewing and toggling the display of a CSV table.

    Additionally, the widget includes interactive controls:
      - A "Show complete table" button that, when clicked, replaces the preview with the full table display.
      - A "Minimize Table" button that appears after the full table is displayed, allowing the view to revert 
        back to showing only the preview.

    Parameters:
        csv_file (str): The corresponding table folder is derived by removing the extension.
        base_csv_dir (str): The base directory that contains the table folders.
        clean_file_name (str): The name of the CSV file within each table folder to be displayed (typically "clean.csv" (or "dirty.csv")).

    Returns:
        tuple: A tuple containing:
            - output_widget (ipywidgets.Output): The widget container for displaying the table content.
            - load_content_func (callable): A function that loads and renders the table preview and interactive controls.
    """

    table_name = os.path.splitext(csv_file)[0]
    output = widgets.Output()
    # Flag so that we load content only once initially
    output._loaded = False  

    def load_content():
        with output:
            if output._loaded:
                # Prevent reloading if already loaded
                return  
            output._loaded = True
            clear_output(wait=True)
            full_path = os.path.join(base_csv_dir, table_name, clean_file_name)
            try:
                df = pd.read_csv(full_path)
                
                # Function to display the head and "Show complete table" button.
                def display_head():
                    clear_output(wait=True)
                    display(HTML(f'<div style="overflow-x: auto; width:100%;">{df.head().to_html()}</div>'))
                    display(btn_show_full)
                
                # Callback for the "Show complete table" button.
                def on_show_full_table(b):
                    with output:
                        clear_output(wait=True)
                        # Display the full dataframe in a scrollable container.
                        display(HTML(f'<div style="overflow-x: auto; width:100%;">{df.to_html()}</div>'))

                        display(btn_minimize)
                
                # Callback for the "Minimize Table" button.
                def on_minimize_table(b):
                    with output:
                        display_head()
                
                # Create the buttons.
                btn_show_full = widgets.Button(description="Show complete table")
                btn_minimize = widgets.Button(description="Minimize Table")
                btn_show_full.on_click(on_show_full_table)
                btn_minimize.on_click(on_minimize_table)
                
                # Initially, display the head view.
                display_head()
                
            except Exception as e:
                print(f"Error loading {table_name} from {full_path}: {e}")

    return output, load_content


def create_cell_fold_accordion(configs):
    """
    Create and return an outer accordion widget for cell folds.

    This function uses the provided configuration dictionary to:
      - Dynamically build the path to the pickle file containing cell fold data.
      - Construct the base directory for CSV files and retrieve the clean CSV file name.
      - Load cell fold data from the pickle file.
      - For each cell fold, create an inner accordion where each section corresponds to a table.
      - Wraps all inner accordions into one outer accordion, where each section is labeled as "Cell Fold X".

    Parameters:
        configs (dict): The configuration dictionary which should include at least:
            - "experiment_output_path": A path to the experiment output folder.
            - "configs": A nested dictionary with a "DIRECTORIES" key, which contains:
                  - "sandbox_dir": Base directory for datasets.
                  - "tables_dir": Subdirectory containing the tables.
                  - "clean_files_name": The filename to use for CSV files (e.g., "clean.csv").

    Returns:
        ipywidgets.Accordion: The outer accordion widget containing all cell fold accordions.
    """

    # ==================== #
    # Configure File Paths #
    # ==================== #
    # Build the path to the pickle file dynamically using the configured experiment output path.
    pickle_file = os.path.join(".", configs["experiment_output_path"], "table_group_dict.pickle")
    # print("Pickle file path:", pickle_file)

    # Build the base directory where the CSV files are stored (e.g., "./datasets/Quintet").
    base_csv_dir = os.path.join(
        ".", 
        configs["configs"]["DIRECTORIES"]["sandbox_dir"], 
        configs["configs"]["DIRECTORIES"]["tables_dir"]
    )
    # print("Base CSV directory:", base_csv_dir)
    
    # Retrieve the name of the clean CSV file.
    clean_file_name = configs["configs"]["DIRECTORIES"]["clean_files_name"]
    
    # =============================================================================
    # Load Cell Folds from the Pickle File
    # =============================================================================
    with open(pickle_file, "rb") as file:
        data = pickle.load(file)
    # For example, data may look like:
    # {0: ['rayyan.csv', 'hospital.csv', 'movies_1.csv'],
    #  1: ['beers2.csv', 'beers.csv'],
    #  2: ['flights.csv']}
    # print("Cell folds data:", data)

    # =============================================================================
    # Create Outer Accordion for Cell Folds (with one inner accordion per fold)
    # =============================================================================
    fold_keys = sorted(data.keys())
    fold_widgets = []
    
    # For each cell fold, create one inner accordion.
    for key in fold_keys:
        # List of CSV files for this cell fold
        csv_files = data[key] 
        # Will hold the Output widgets for each table 
        table_widgets = []    
        # Their corresponding load functions
        load_functions = []   
        
        # Create one widget (and load function) per table.
        for csv_file in csv_files:
            widget_content, load_func = create_table_content_widget(csv_file, base_csv_dir, clean_file_name)
            table_widgets.append(widget_content)
            load_functions.append(load_func)
        
        # Create one inner accordion for all tables in this cell fold.
        inner_accordion = widgets.Accordion(children=table_widgets)
        # Set the title of each section to the table name (without ".csv").
        for idx, csv_file in enumerate(csv_files):
            table_name = os.path.splitext(csv_file)[0]
            inner_accordion.set_title(idx, table_name)
        
        # Attach an observer so that when a section is expanded, its content loads.
        # Use a closure to capture the current list of load functions.
        def make_on_inner_change(load_funcs):
            def on_inner_change(change):
                new_index = change.get("new", None)
                if new_index is not None and new_index < len(load_funcs):
                    # Load content for the expanded section.
                    load_funcs[new_index]()  
            return on_inner_change
        
        inner_accordion.observe(make_on_inner_change(load_functions), names="selected_index")
        
        fold_widgets.append(inner_accordion)
    
    # Create an outer accordion where each cell fold (group) is a section.
    outer_accordion = widgets.Accordion(children=fold_widgets)
    for idx, key in enumerate(fold_keys):
        outer_accordion.set_title(idx, f"Cell Fold {key}")
    
    return outer_accordion

def create_sample_row(sample_key, sample_val, configs):
    """
    Create a row for a single sample with two buttons.
    The sample key is expected to be a tuple of the form:
      (table_hash, column_id, row_id)
    where table_hash is the MD5 hash of "foldername.csv".
    
    This function uses the hash to determine the table (folder) name, opens the corresponding
    dirty CSV file from that folder, and then retrieves the cell value by looking up the row
    with a matching 'tuple_id' (if available) and using the provided column index.
    
    The sample information is displayed in a scrollable HTML widget.
    """

    # Determine the configuration object.
    config_obj = configs["configs"] if "configs" in configs else configs

    # Access the "DIRECTORIES" section.
    sandbox_dir = config_obj["DIRECTORIES"]["sandbox_dir"]
    tables_dir = config_obj["DIRECTORIES"]["tables_dir"]
    datasets_table_path = os.path.join(sandbox_dir, tables_dir)
    
    # Build a dictionary mapping MD5 hash of "foldername.csv" to the folder name.
    hash_dict = {}
    for entry in os.listdir(datasets_table_path):
        entry_path = os.path.join(datasets_table_path, entry)
        if os.path.isdir(entry_path):
            csv_string = f"{entry}.csv"
            file_hash = hashlib.md5(csv_string.encode('utf-8')).hexdigest()
            hash_dict[file_hash] = entry  # folder name as table name

    # Extract the inner key from sample_val if available; otherwise use sample_key.
    if isinstance(sample_val, dict) and len(sample_val) > 0:
        inner_key = list(sample_val.keys())[0]
    else:
        inner_key = sample_key

    # Expect the inner key to be a tuple: (file_hash, column_id, row_id)
    if isinstance(inner_key, tuple) and len(inner_key) >= 3:
        file_hash = inner_key[0]
        col_idx = inner_key[1]
        row_id = inner_key[2]
    else:
        file_hash = inner_key
        col_idx, row_id = None, None

    # Look up the table (folder) name using the hash dictionary.
    table_name = hash_dict.get(file_hash, file_hash)

    # Now, open the corresponding dirty CSV from that table folder and retrieve the cell value.
    cell_value = "N/A"
    folder_path = os.path.join(datasets_table_path, table_name)
    # Use the dirty file name from the configuration (default to "dirty.csv")
    dirty_filename = config_obj["DIRECTORIES"].get("dirty_files_name", "dirty.csv")
    dirty_csv_path = os.path.join(folder_path, dirty_filename)
    
    try:
        df = pd.read_csv(dirty_csv_path)
        # If the dataframe has a 'tuple_id' column, use it to locate the correct row.
        if 'tuple_id' in df.columns and pd.api.types.is_numeric_dtype(df['tuple_id']):
            # Ensure the tuple_id column is numeric
            df['tuple_id'] = pd.to_numeric(df['tuple_id'], errors='coerce')
            matching = df[df['tuple_id'] == row_id]
            if not matching.empty:
                row_data = matching.iloc[0]
                try:
                    cell_value = row_data.iloc[col_idx]
                except Exception as e:
                    cell_value = f"Error (col lookup): {e}"
            else:
                cell_value = f"Row id {row_id} not found"
        else:
            # Otherwise, assume row_id is a direct row index.
            cell_value = df.iloc[row_id, col_idx]
    except Exception as e:
        cell_value = f"Error: {e}"

    # Build the sample string showing table name and cell value.
    sample_str = (f"Sample {sample_key}: Table: {table_name} | "
                  f"Cell Value: {cell_value} | Sample Value: {sample_val}")
    html_str = f"<div style='width:600px; overflow:auto;'>{sample_str}</div>"
    label = widgets.HTML(value=html_str)

    # Create two buttons: True (default selected) and False.
    btn_true = widgets.Button(
        description="True", 
        button_style="success",
        layout=widgets.Layout(width='100px')
    )
    btn_false = widgets.Button(
        description="False", 
        button_style="",
        layout=widgets.Layout(width='100px')
    )

    state = {"value": True}

    def on_true_click(b):
        if state["value"] is not True:
            state["value"] = True
            btn_true.button_style = "success"
            btn_false.button_style = ""

    def on_false_click(b):
        if state["value"] is not False:
            state["value"] = False
            btn_true.button_style = ""
            btn_false.button_style = "danger"

    btn_true.on_click(on_true_click)
    btn_false.on_click(on_false_click)

    row = widgets.HBox([label, btn_true, btn_false])
    return row, state


def create_domain_fold_widget(fold_id, samples, configs):
    """
    Create the UI for a single domain fold.
    The header row displays fixed button headers (as column headers).
    Each sample row shows its description plus two mutually exclusive buttons.
    """
    # Header row with disabled buttons as column headers.
    header = widgets.HBox([
        widgets.Label("Sample", layout=widgets.Layout(width='300px')),
        widgets.Button(description="True", disabled=True, button_style="success", layout=widgets.Layout(width='100px')),
        widgets.Button(description="False", disabled=True, button_style="danger", layout=widgets.Layout(width='100px'))
    ])
    
    # Create sample rows.
    sample_rows = []
    # This dict will hold the state for each sample in this fold.
    sample_states = {}
    for sample_key, sample_val in samples.items():
        row, state = create_sample_row(sample_key, sample_val, configs)
        sample_rows.append(row)
        sample_states[sample_key] = state
    # Pack the header and sample rows together.
    fold_widget = widgets.VBox([header] + sample_rows)
    return fold_widget, sample_states

def display_labeling_widget(domain_fold_samples, configs):
    """
    Build the overall labeling UI using an outer accordion.
    Each accordion panel corresponds to one domain fold.
    The content of each panel (built using create_domain_fold_widget) is loaded lazily.
    On submission, the current state for each sample is stored back into the domain_fold_samples dictionary.
    """
    # Sorted list of fold IDs.
    fold_ids = sorted(domain_fold_samples.keys())
    # Create a placeholder (empty output) for each fold.
    placeholders = [widgets.Output() for _ in fold_ids]
    outer_accordion = widgets.Accordion(children=placeholders)
    for idx, fold_id in enumerate(fold_ids):
        outer_accordion.set_title(idx, f"Domain Fold {fold_id}")
    
    # Dictionary to hold the loaded sample state dictionaries per fold.
    loaded_folds = {}  # key: accordion index, value: sample_states dict

    def on_accordion_change(change):
        new_index = change.get("new")
        if new_index is not None and new_index not in loaded_folds:
            fold_id = fold_ids[new_index]
            samples = domain_fold_samples[fold_id]
            fold_widget, sample_states = create_domain_fold_widget(fold_id, samples, configs)
            loaded_folds[new_index] = sample_states
            # Replace the placeholder content with the fold widget.
            placeholder = outer_accordion.children[new_index]
            placeholder.clear_output()
            with placeholder:
                display(fold_widget)
    
    outer_accordion.observe(on_accordion_change, names="selected_index")
    
    # Create a submit button and an output area.
    submit_button = widgets.Button(description="Submit Labels", button_style="success")
    submit_output = widgets.Output()
    
    def on_submit_clicked(b):
        # Update each fold's samples with the current state from the corresponding button pair.
        for index, sample_states in loaded_folds.items():
            fold_id = fold_ids[index]
            for sample_key, state in sample_states.items():
                new_label = state["value"]
                old_entry = domain_fold_samples[fold_id][sample_key]
                if isinstance(old_entry, (list, tuple)):
                    # Replace the third element with the new label.
                    domain_fold_samples[fold_id][sample_key] = (old_entry[0], old_entry[1], new_label)
                elif isinstance(old_entry, dict):
                    old_entry['label'] = new_label
                else:
                    domain_fold_samples[fold_id][sample_key] = new_label
        with submit_output:
            clear_output()
            print("Labels submitted successfully!")
    
    submit_button.on_click(on_submit_clicked)
    
    ui = widgets.VBox([outer_accordion, submit_button, submit_output])
    return ui, domain_fold_samples
