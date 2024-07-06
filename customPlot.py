import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import argparse

# List of plot configurations
plot_configs = [
    {
        "groupby": "branch",
        "x": "Worker_Thread_Count",
        "y": "Simulation_Runtime_(secs.)",
        "title": "Thread count branch vs Simulation time",
        "type": "bar",
        "agg": "mean"
    },
    {
        "groupby": "branch",
        "x": "Worker_Thread_Count",
        "y": "Events_Processed",
        "title": "Events Processed vs Worker Thread Count",
        "type": "line",
        "agg": "sum"
    },
    {
        "groupby": "branch",
        "x": "Model",
        "y": "Average_Memory_Usage_(MB)",
        "title": "Average Memory Usage by Model and Queue Type",
        "type": "bar",
        "agg": "mean"
    },
    # Add more configurations as needed
]

def create_plot(df, config, output_dir):
    # Group and aggregate data
    grouped_data = df.groupby([config['groupby'], config['x']])[config['y']].agg(config['agg']).reset_index()
    
    # Create plot
    plt.figure(figsize=(12, 6))
    if config['type'] == 'bar':
        sns.barplot(x=config['x'], y=config['y'], hue=config['groupby'], data=grouped_data)
    elif config['type'] == 'line':
        sns.lineplot(x=config['x'], y=config['y'], hue=config['groupby'], data=grouped_data, marker='o')
    
    plt.title(config['title'])
    plt.xlabel(config['x'])
    plt.ylabel(config['y'])
    plt.legend(title=config['groupby'])
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save the plot
    filename = f"{config['title'].replace(' ', '_')}.png"
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()

def parse_arguments():
    parser = argparse.ArgumentParser(description="Generate plots from CSV data")
    parser.add_argument("input_file", help="Path to the input CSV file")
    return parser.parse_args()

def main():
    # Parse command-line arguments
    args = parse_arguments()
    
    # Get the directory of the input CSV file
    input_dir = os.path.dirname(os.path.abspath(args.input_file))
    
    # Create output directory as a subdirectory of the input directory
    output_dir = os.path.join(input_dir, 'output_plots')
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the CSV file
    df = pd.read_csv(args.input_file)
    
    # Create plots for each configuration
    for config in plot_configs:
        create_plot(df, config, output_dir)
    
    print(f"All plots have been generated and saved in the '{output_dir}' directory.")

if __name__ == "__main__":
    main()