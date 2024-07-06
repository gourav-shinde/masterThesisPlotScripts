import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import argparse
from matplotlib.ticker import FuncFormatter
import glob

# Use a basic style that should be available in all matplotlib installations
plt.style.use('default')

# Set seaborn style manually
sns.set_style("whitegrid")
sns.set_palette("deep")

colors = ["#ff9999", "#66b3ff", "#99ff99", "#ffcc99", "#ff99cc", "#99ffff", "#ff99ff", "#ffff99"]

def format_y_axis(y, _):
    if y >= 1e6:
        return f'{y/1e6:.1f}M'
    elif y >= 1e3:
        return f'{y/1e3:.1f}K'
    else:
        return f'{y:.0f}'

plot_configs = [
    {
        "groupby": "branch",
        "x": "Worker_Thread_Count",
        "y": "Simulation_Runtime_(secs.)",
        "title": "Thread Count vs Simulation Time by Branch and Model",
        "type": "line",
        "agg": "mean"
    },
    {
        "groupby": "branch",
        "x": "Worker_Thread_Count",
        "y": "Events_Processed",
        "title": "Events Processed vs Worker Thread Count by Branch and Model",
        "type": "line",
        "agg": "sum"
    },
    {
        "groupby": "branch",
        "x": "Model",
        "y": "Average_Memory_Usage_(MB)",
        "title": "Average Memory Usage by Model and Branch",
        "type": "bar",
        "agg": "mean"
    },
]

def create_unified_plot(dataframes, config, output_dir):
    plt.figure(figsize=(16, 10))
    ax = plt.gca()

    for i, (model, df) in enumerate(dataframes.items()):
        grouped_data = df.groupby([config['groupby'], config['x']])[config['y']].agg(config['agg']).reset_index()
        
        if config['type'] == 'bar':
            sns.barplot(x=config['x'], y=config['y'], hue=config['groupby'], data=grouped_data, 
                        palette=colors[i*2:(i+1)*2], alpha=0.7, ax=ax)
            handles, labels = ax.get_legend_handles_labels()
            for handle in handles:
                handle.set_label(f"{model} - {handle.get_label()}")
        
        elif config['type'] == 'line':
            sns.lineplot(x=config['x'], y=config['y'], hue=config['groupby'], data=grouped_data, 
                         marker='o', palette=colors[i*2:(i+1)*2], ax=ax)
            for line in ax.lines[-len(grouped_data[config['groupby']].unique()):]:
                line.set_label(f"{model} - {line.get_label()}")

    plt.title(config['title'], fontsize=20, fontweight='bold', pad=20)
    plt.xlabel(config['x'], fontsize=14, labelpad=10)
    plt.ylabel(config['y'], fontsize=14, labelpad=10)
    
    ax.yaxis.set_major_formatter(FuncFormatter(format_y_axis))
    
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, title='Model - ' + config['groupby'], 
              title_fontsize='13', fontsize='11', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    if len(grouped_data[config['x']].unique()) > 10:
        plt.xticks(rotation=45, ha='right')
    
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    filename = f"Unified_{config['title'].replace(' ', '_')}.png"
    plt.savefig(os.path.join(output_dir, filename), dpi=300, bbox_inches='tight')
    plt.close()


def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate unified plots from multiple CSV files")
    parser.add_argument("input_pattern", help="Glob pattern for directories containing CSV files (e.g., 'path/to/*')")
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Get the parent directory of the input pattern
    parent_dir = os.path.dirname(args.input_pattern)
    
    # Set the output directory to be the parent directory
    output_dir = parent_dir
    os.makedirs(output_dir, exist_ok=True)
    
    dataframes = {}
    for input_dir in glob.glob(args.input_pattern):
        if os.path.isdir(input_dir):
            model_name = os.path.basename(input_dir)
            csv_file = next((f for f in os.listdir(input_dir) if f.endswith('.csv')), None)
            if csv_file:
                df = pd.read_csv(os.path.join(input_dir, csv_file))
                df['Model'] = model_name  # Add a column to identify the model
                dataframes[model_name] = df
    
    for config in plot_configs:
        create_unified_plot(dataframes, config, output_dir)
    
    print(f"All unified plots have been generated and saved in the '{output_dir}' directory.")

if __name__ == "__main__":
    main()
