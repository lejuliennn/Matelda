import os
from configparser import ConfigParser
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML, Javascript
import pickle
import pandas as pd

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