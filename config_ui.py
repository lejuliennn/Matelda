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
    Create a vertical layout:
      1) A single HTML block containing sample info and the table
      2) A horizontal row of True/False buttons below the table

    Removes the top 'Sample/True/False' headers and avoids an extra sample row above the domain fold.
    """
    
    # Retrieve config object if needed
    config_obj = configs["configs"] if "configs" in configs else configs

    sandbox_dir = config_obj["DIRECTORIES"]["sandbox_dir"]
    tables_dir = config_obj["DIRECTORIES"]["tables_dir"]
    datasets_table_path = os.path.join(sandbox_dir, tables_dir)

    # Build a dict: MD5("foldername.csv") -> foldername
    hash_dict = {}
    for entry in os.listdir(datasets_table_path):
        entry_path = os.path.join(datasets_table_path, entry)
        if os.path.isdir(entry_path):
            csv_string = f"{entry}.csv"
            file_hash = hashlib.md5(csv_string.encode("utf-8")).hexdigest()
            hash_dict[file_hash] = entry

    # Extract the relevant tuple from sample_val (if it's a dict) or use sample_key directly
    if isinstance(sample_val, dict) and len(sample_val) > 0:
        inner_key = list(sample_val.keys())[0]
    else:
        inner_key = sample_key

    # Expect inner_key as (file_hash, col_idx, row_id)
    if isinstance(inner_key, tuple) and len(inner_key) >= 3:
        file_hash, col_idx, row_id = inner_key[0], inner_key[1], inner_key[2]
    else:
        file_hash, col_idx, row_id = inner_key, None, None

    # Map hash -> folder (table) name
    table_name = hash_dict.get(file_hash, file_hash)

    # Attempt to load the dirty CSV
    dirty_filename = config_obj["DIRECTORIES"].get("dirty_files_name", "dirty.csv")
    dirty_csv_path = os.path.join(datasets_table_path, table_name, dirty_filename)

    # Build the HTML table snippet
    table_html = ""
    try:
        df = pd.read_csv(dirty_csv_path)
        if "tuple_id" in df.columns:
            df["tuple_id"] = pd.to_numeric(df["tuple_id"], errors="coerce")
            matching = df[df["tuple_id"] == row_id]
            if not matching.empty:
                target_idx = matching.index[0]
            else:
                raise ValueError(f"Row id {row_id} not found in 'tuple_id' column.")
        else:
            target_idx = row_id

        # Show up to 3 rows: one before, target, one after
        indices_to_show = []
        if target_idx > 0:
            indices_to_show.append(target_idx - 1)
        indices_to_show.append(target_idx)
        if target_idx < len(df) - 1:
            indices_to_show.append(target_idx + 1)

        # Generate HTML table
        table_html += "<table style='border-collapse: collapse; width: auto;'>"
        # Header row
        table_html += "<tr>"
        for col_name in df.columns:
            table_html += f"<th style='border: 1px solid #ccc; padding: 4px;'>{col_name}</th>"
        table_html += "</tr>"

        # Rows
        for idx in indices_to_show:
            row_data = df.iloc[idx]
            row_style = "background-color: lightyellow;" if idx == target_idx else ""
            table_html += f"<tr style='{row_style}'>"
            for j, col_name in enumerate(df.columns):
                cell_val = row_data[col_name]
                if idx == target_idx and j == col_idx:
                    cell_style = "background-color: darkorange; border: 1px solid #ccc; padding: 4px;"
                else:
                    cell_style = "border: 1px solid #ccc; padding: 4px;"
                table_html += f"<td style='{cell_style}'>{cell_val}</td>"
            table_html += "</tr>"
        table_html += "</table>"

    except Exception as e:
        table_html = f"<p style='color:red;'>Error reading CSV: {e}</p>"

    # Combine sample info and the table
    sample_info = f"Sample {sample_key}: Table: {table_name}, Row: {row_id}, Col: {col_idx}"
    combined_html = f"<div>{sample_info}</div><div style='max-width:100%; overflow:auto;'>{table_html}</div>"
    info_table_widget = widgets.HTML(value=combined_html)

    # Create True/False buttons
    btn_true = widgets.Button(description="True", button_style="success")
    btn_false = widgets.Button(description="False", button_style="")

    state = {"value": True}

    def on_true_click(_):
        if state["value"] is not True:
            state["value"] = True
            btn_true.button_style = "success"
            btn_false.button_style = ""

    def on_false_click(_):
        if state["value"] is not False:
            state["value"] = False
            btn_true.button_style = ""
            btn_false.button_style = "danger"

    btn_true.on_click(on_true_click)
    btn_false.on_click(on_false_click)

    # Place the buttons below the table
    button_box = widgets.HBox([btn_true, btn_false])
    main_layout = widgets.VBox([info_table_widget, button_box])

    return main_layout, state


def create_domain_fold_widget(fold_id, samples, configs):
    """
    Create the UI for a single domain fold.
    The header row displays fixed button headers (as column headers).
    Each sample row shows its description plus two mutually exclusive buttons.
    """
        
    # Create sample rows.
    sample_rows = []
    # This dict will hold the state for each sample in this fold.
    sample_states = {}
    for sample_key, sample_val in samples.items():
        row, state = create_sample_row(sample_key, sample_val, configs)
        sample_rows.append(row)
        sample_states[sample_key] = state
    fold_widget = widgets.VBox(sample_rows)
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
