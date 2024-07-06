#!/usr/bin/env python3

# Calculates statistics and plots the schedule queue metrics from raw data

import csv
import os, sys
import numpy as np
import scipy as sp
import scipy.stats as sps
import pandas as pd
import re, shutil, tempfile
import itertools, operator
import subprocess
import matplotlib.pyplot as plt

###### Settings go here ######

searchAttrsList =   [
                        {   'groupby': ['branch'],
                            'filter' : 'Schedule_Queue_Count',
                            'model'  : 'Model',
                            'lpcount': 'Number_of_Objects',
                            'output' : 'threads_vs_type_key_count_'  },

                        {   'groupby': ['branch'],
                            'filter' : 'Schedule_Queue_Type',
                            'model'  : 'Model',
                            'lpcount': 'Number_of_Objects',
                            'output' : 'threads_vs_count_key_type_'   }
                    ]

'''
List of metrics available:

    Event_Commitment_Ratio
    Total_Rollbacks
    Simulation_Runtime_(secs.)
    Average_Memory_Usage_(MB)
    Event_Processing_Rate_(per_sec)
    Speedup_w.r.t._Sequential_Simulation
'''
metricList      =   [
                        {   'name'  : 'Event_Processing_Rate_(per_sec)',
                            'ystart': 0,
                            'yend'  : 1000000,
                            'ytics' : 100000    },

                        {   'name'  : 'Simulation_Runtime_(secs.)',
                            'ystart': 0,
                            'yend'  : 150,
                            'ytics' : 10        },

                        {   'name'  : 'Event_Commitment_Ratio',
                            'ystart': 1,
                            'yend'  : 2,
                            'ytics' : 0.1       },

                        {   'name'  : 'Speedup_w.r.t._Sequential_Simulation',
                            'ystart': 0,
                            'yend'  : 10,
                            'ytics' : 1         }
                    ]

rawDataFileName = 'scheduleq'

statType        = [ 'Mean',
                    'CI_Lower',
                    'CI_Upper',
                    'Median',
                    'Lower_Quartile',
                    'Upper_Quartile'
                  ]
###### Don't edit below here ######


def mean_confidence_interval(data, confidence=0.95):
    # check the input is not empty
    if not data:
        raise RuntimeError('mean_ci - no data points passed')
    a = 1.0*np.array(data)
    n = len(a)
    m, se = np.mean(a), sps.sem(a)
    h = se * sps.t._ppf((1+confidence)/2., n-1)
    return m, m-h, m+h

def median(data):
    # check the input is not empty
    if not data:
        raise RuntimeError('median - no data points passed')
    return np.median(np.array(data))

def quartiles(data):
    # check the input is not empty
    if not data:
        raise RuntimeError('quartiles - no data points passed')
    sorts = sorted(data)
    mid = len(sorts) // 2
    if (len(sorts) % 2 == 0):
        # even
        lowerQ = median(sorts[:mid])
        upperQ = median(sorts[mid:])
    else:
        # odd
        lowerQ = median(sorts[:mid])  # same as even
        upperQ = median(sorts[mid+1:])
    return lowerQ, upperQ

def statistics(data):
    # check the input is not empty
    if not data:
        raise RuntimeError('statistics - no data points passed')

    mean = ci_lower = ci_upper = med = lower_quartile = upper_quartile = data[0]
    if len(data) > 1:
        mean, ci_lower, ci_upper = mean_confidence_interval(data)
        med = median(data)
        lower_quartile, upper_quartile = quartiles(data)

    statList = (str(mean), str(ci_lower), str(ci_upper), str(med), str(lower_quartile), str(upper_quartile))
    return ",".join(statList)

def sed_inplace(filename, pattern, repl):
    # For efficiency, precompile the passed regular expression.
    pattern_compiled = re.compile(pattern)

    # For portability, NamedTemporaryFile() defaults to mode "w+b" (i.e., binary
    # writing with updating). In this case, binary writing imposes non-trivial 
    # encoding constraints resolved by switching to text writing.
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        with open(filename) as src_file:
            for line in src_file:
                tmp_file.write(pattern_compiled.sub(repl, line))

    # Overwrite the original file with the temporary file in a
    # manner preserving file attributes (e.g., permissions).
    shutil.copystat(filename, tmp_file.name)
    shutil.move(tmp_file.name, filename)

def getIndex(aList, text):
    '''Returns the index of the requested text in the given list'''
    for i,x in enumerate(aList):
        if x == text:
            return i

def plot(data, fileName, title, subtitle, xaxisLabel, yaxisLabel, ystart, yend, ytics, linePreface):
    plt.figure(figsize=(12, 9))
    plt.title(f"{title.replace('_', ' ')}\n{subtitle.replace('_', ' ')}")
    plt.xlabel(xaxisLabel.replace("_", " "))
    plt.ylabel(yaxisLabel.replace("_", " "))
    plt.grid(True)

    for key in sorted(data[statType[0]]):
        x = data['header'][key]
        y = data[statType[0]][key]
        yerr = [np.array(data[statType[0]][key]) - np.array(data[statType[1]][key]),
                np.array(data[statType[2]][key]) - np.array(data[statType[0]][key])]
        plt.errorbar(x, y, yerr=yerr, fmt='-o', capsize=5, label=linePreface+key)

    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(fileName)
    plt.close()

def plot_stats(dirPath, fileName, xaxisLabel, keyLabel, filterLabel, filterValue, model, lpCount):
    # Read the stats csv
    inFile = os.path.join(dirPath, 'stats', rawDataFileName, f'{fileName}.csv')
    
    # Read all data from the CSV file
    with open(inFile, 'r', newline='') as csvfile:
        reader = list(csv.reader(csvfile))
    
    header = reader[0]
    data = reader[1:]  # All rows except the header

    # Get Column Values for use below
    xaxis = getIndex(header, xaxisLabel)
    kid = getIndex(header, keyLabel)

    # Sort the data
    data = sorted(data, key=lambda x: int(x[xaxis]))
    data = sorted(data, key=lambda x: x[kid])

    for param in metricList:
        metric = param['name']
        ystart = param['ystart']
        yend = param['yend']
        ytics = param['ytics']

        outData = {'header': {}}

        # Populate the header
        for kindex, kdata in itertools.groupby(data, lambda x: x[kid]):
            if kindex not in outData['header']:
                outData['header'][kindex] = []
            for xindex, xdata in itertools.groupby(kdata, lambda x: x[xaxis]):
                outData['header'][kindex].append(xindex)

        # Populate the statistical data
        for stat in statType:
            columnName = metric + '_' + stat
            columnIndex = getIndex(header, columnName)
            if stat not in outData:
                outData[stat] = {}
            for xindex, xdata in itertools.groupby(data, lambda x: x[xaxis]):
                for kindex, kdata in itertools.groupby(xdata, lambda x: x[kid]):
                    if kindex not in outData[stat]:
                        outData[stat][kindex] = []
                    value = [item[columnIndex] for item in kdata][0]
                    outData[stat][kindex].append(float(value))

        # Plot the statistical data
        title = f"{model.upper()} model with {lpCount:,} LPs"
        subtitle = f"{filterLabel} = {str(filterValue).upper()} , key = {keyLabel}"
        outDir = os.path.join(dirPath, 'plots', rawDataFileName)
        outFile = os.path.join(outDir, f"{fileName}_{metric}.pdf")
        yaxisLabel = f"{metric}_(C.I._=_95%)"
        plot(outData, outFile, title, subtitle, xaxisLabel, yaxisLabel, ystart, yend, ytics, '')

def calc_and_plot(dirPath):
    # Load the sequential simulation time
    seqFile = os.path.join(dirPath, 'sequential.dat')
    if not os.path.exists(seqFile):
        print('Sequential data not available')
        sys.exit(1)
    with open(seqFile, 'r') as seqFp:
        seqCount, _, seqTime = seqFp.readline().split()

    # Load data from csv file
    inFile = os.path.join(dirPath, f'{rawDataFileName}.csv')
    if not os.path.exists(inFile):
        print(f'{rawDataFileName.upper()} raw data not available')
        sys.exit(1)

    data = pd.read_csv(inFile)

    data['Event_Commitment_Ratio'] = \
        data['Events_Processed'] / data['Events_Committed']
    data['Total_Rollbacks'] = \
        data['Primary_Rollbacks'] + data['Secondary_Rollbacks']
    data['Event_Processing_Rate_(per_sec)'] = \
        data['Events_Processed'] / data['Simulation_Runtime_(secs.)']
    data['Speedup_w.r.t._Sequential_Simulation'] = \
        float(seqTime) / data['Simulation_Runtime_(secs.)']

    # Create the plots directory (if needed)
    outDir = os.path.join(dirPath, 'plots')
    os.makedirs(outDir, exist_ok=True)

    outName = os.path.join(outDir, rawDataFileName)
    shutil.rmtree(outName, ignore_errors=True)
    os.makedirs(outName)

    # Create the stats directory (if needed)
    outDir = os.path.join(dirPath, 'stats')
    os.makedirs(outDir, exist_ok=True)

    outName = os.path.join(outDir, rawDataFileName)
    shutil.rmtree(outName, ignore_errors=True)
    os.makedirs(outName)

    for searchAttrs in searchAttrsList:
        groupbyList = searchAttrs['groupby'].copy()
        filterName  = searchAttrs['filter']
        model       = searchAttrs['model']
        lpcount     = searchAttrs['lpcount']
        output      = searchAttrs['output']

        groupbyList.append(filterName)

        # Read unique values for the filter
        filterValues = data[filterName].unique().tolist()

        # Read the model name and LP count
        modelName = data[model].unique().tolist()
        lpCount   = data[lpcount].unique().tolist()

        for filterValue in filterValues:
            # Filter data for each filterValue
            filteredData = data[data[filterName] == filterValue]
            groupedData = filteredData.groupby(groupbyList)
            columnNames = list(groupbyList)

            # Generate stats
            result = pd.DataFrame()
            for param in metricList:
                metric = param['name']
                columnNames += [metric + '_' + x for x in statType]
                try:
                    stats = groupedData[metric].apply(lambda x: statistics(x.tolist()))
                    result = pd.concat([result, stats], axis=1)
                except Exception as e:
                    print(f"Error processing metric {metric}: {str(e)}")
                    continue  # Skip to the next metric if there's an error

            # Write to the csv
            fileName = f"{output}{filterValue}"
            outFile = os.path.join(outName, f'{fileName}.csv')
            with open(outFile, 'w', newline='') as statFile:
                statFile.write(','.join(columnNames) + '\n')
            result.to_csv(outFile, mode='a', header=False, index=True)

            # Remove " from the newly created csv file
            sed_inplace(outFile, r'"', '')

            # Plot the statistics
            plot_stats(dirPath, fileName, groupbyList[0], groupbyList[1],
                       filterName, filterValue, modelName[0], lpCount[0])

def main():
    if len(sys.argv) != 2:
        print('Usage: python script.py <path_to_source>')
        sys.exit(1)
    dirPath = sys.argv[1]
    if not os.path.exists(dirPath):
        print('Invalid path to source')
        sys.exit(1)

    calc_and_plot(dirPath)

if __name__ == "__main__":
    main()