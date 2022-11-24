#!/usr/bin/env python
#
# Data manager for reference data for the 'fgenesh' Galaxy tools

import argparse
import json
import os
from datetime import date
from pathlib import Path

try:
    # For Python 3.0 and later
    from urllib.request import Request, urlopen
except ImportError:
    # Fall back to Python 2 imports
    from urllib2 import Request, urlopen


FGENESH_DATA = {
    "nr": {
        "ce": "C elegans",
    },
    "par": {
        "mammals": "Parameter file for Mammals",
        "non_mammals": "Parameter file for Non Mammals",
    },
    "matrix": {
        "C_elegans_nGASP": "Matrix for C elegans",
    }
}

FGENESH_DATA_URL = {
    "nr" : {
        "ce": "http://mike-sandpit.qfab.org:8080/NR/nr_ce",
    },
    "par": {
        "mammals": "http://mike-sandpit.qfab.org:8080/PAR/mammals.par",
        "non_mammals": "http://mike-sandpit.qfab.org:8080/PAR/non_mammals.par",
    },
    "matrix": {
        "ce":"http://mike-sandpit.qfab.org:8080/MATRIX/C_elegans_nGASP",
    }
}

def url_download(url, fname, workdir):
    """
    download url to workdir/fname
    """
    file_path = os.path.join(workdir, fname)
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    src = None
    dst = None
    try:
        req = Request(url)
        src = urlopen(req)
        with open(file_path, 'wb') as dst:
            while True:
                chunk = src.read(2**10)
                if chunk:
                    dst.write(chunk)
                else:
                    break
    finally:
        if src:
            src.close()


# Utility functions for interacting with Galaxy JSON
def read_input_json(json_fp):
    """Read the JSON supplied from the data manager tool
    Returns a tuple (param_dict,extra_files_path)
    'param_dict' is an arbitrary dictionary of parameters
    input into the tool; 'extra_files_path' is the path
    to a directory where output files must be put for the
    receiving data manager to pick them up.
    NB the directory pointed to by 'extra_files_path'
    doesn't exist initially, it is the job of the script
    to create it if necessary.
    """
    with open(json_fp) as fh:
        params = json.load(fh)
    return (params['param_dict'],
            Path(params['output_data'][0]['extra_files_path']))


# Utility functions for creating data table dictionaries
#
# Example usage:
# >>> d = create_data_tables_dict()
# >>> add_data_table(d,'my_data')
# >>> add_data_table_entry(dict(dbkey='hg19',value='human'))
# >>> add_data_table_entry(dict(dbkey='mm9',value='mouse'))
# >>> print(json.dumps(d))
def create_data_tables_dict():
    """Return a dictionary for storing data table information

    Returns a dictionary that can be used with 'add_data_table'
    and 'add_data_table_entry' to store information about a
    data table. It can be converted to JSON to be sent back to
    the data manager.

    """
    d = {
        'data_tables': {}
    }
    return d


def add_data_table(d, table):
    """Add a data table to the data tables dictionary

    Creates a placeholder for a data table called 'table'.

    """
    d['data_tables'][table] = []


def add_data_table_entry(d, table, entry):
    """Add an entry to a data table

    Appends an entry to the data table 'table'. 'entry'
    should be a dictionary where the keys are the names of
    columns in the data table.

    Raises an exception if the named data table doesn't
    exist.

    """
    try:
        d['data_tables'][table].append(entry)
    except KeyError:
        raise Exception("add_data_table_entry: no table '%s'" % table)


def download_fgenesh_db(data_tables, table_name, database, build,  target_dp):
    """Download FGENESH database

    Creates references to the specified file(s) on the Galaxy
    server in the appropriate data table (determined from the
    file extension).

    The 'data_tables' dictionary should have been created using
    the 'create_data_tables_dict' and 'add_data_table' functions.

    Arguments:
      data_tables: a dictionary containing the data table info
      table_name: name of the table
      database: database to download (chocophlan or uniref)
      build: build of the database to download
      version: tool version
      target_dp: directory to put copy or link to the data file
    """
    db_target_dp = target_dp / Path(database)
    db_dp = db_target_dp / Path(database)
    build_target_dp = db_target_dp / Path(build)
    
    if database == "nr":
        url_download(FGENESH_DATA_URL[database][build], "nr_" + build, db_target_dp)
    elif database == "par":
        url_download(FGENESH_DATA_URL[database][build], build + ".par", db_target_dp)
    elif database == "matrix":
        url_download(FGENESH_DATA_URL[database][build], build + "_nGASP", db_target_dp)

    # move db
    #db_dp.rename(build_target_dp)
    # add details to data table
    if database != "nr":
        add_data_table_entry(
            data_tables,
            table_name,
            dict(
                value="%s-%s-%s" % (database, build, date.today().strftime("%d%m%Y")),
                name=FGENESH_DATA[database][build],
                path=str(build_target_dp)))
    elif args.database == "nr":
        add_data_table_entry(
            data_tables,
            table_name,
            dict(
                value="%s-%s-%s" % (database, build, date.today().strftime("%d%m%Y")),
                name=FGENESH_DATA[database][build],
                path=str(build_target_dp)))


if __name__ == "__main__":
    print("Starting...")

    # Read command line
    parser = argparse.ArgumentParser(description='Download HUMAnN database')
    parser.add_argument('--database', help="Database name")
    parser.add_argument('--build', help="Build of the database")
    parser.add_argument('--json', help="Path to JSON file")
    args = parser.parse_args()
    print("args   : %s" % args)
    
    # Read the input JSON
    json_fp = Path(args.json)
    params, target_dp = read_input_json(json_fp)

    # Make the target directory
    print("Making %s" % target_dp)
    target_dp.mkdir(parents=True, exist_ok=True)

    # Set up data tables dictionary
    data_tables = create_data_tables_dict()
    if args.database == "nr":
        table_name = 'fgenesh_nr'
    elif args.database == "par":
        table_name = 'fgenesh_par'
    elif args.database == "matrix":
        table_name = 'fgenesh_matrix'
    add_data_table(data_tables, table_name)

    # Fetch data from specified data sources
    print("Download and build database")
    download_fgenesh_db(
        data_tables,
        table_name,
        args.database,
        args.build,
        target_dp)

    # Write output JSON
    print("Outputting JSON")
    with open(json_fp, 'w') as fh:
        json.dump(data_tables, fh, sort_keys=True)
    print("Done.")
