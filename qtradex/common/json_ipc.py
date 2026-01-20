"""
JSON IPC
Concurrent Interprocess Communication via Read and Write JSON
features to mitigate race condition:
    open file using with statement
    explicit close() in with statement
    finally close()
    json formatting required
    postscript clipping prevents misread due to overwrite without erase
    read and write to the text pipe with a single definition
    growing delay between attempts prevents cpu leak
to view your live streaming database, navigate to the pipe folder in the terminal:
    tail -F your_json_ipc_database.txt
:dependencies: os, traceback, json.loads, json.dumps
:warn: incessant read/write concurrency may damage older spinning platter drives
:warn: keeping a 3rd party file browser pointed to the pipe folder may consume RAM
:param str(doc): name of file to read or write
:param str(text): json dumped list or dict to write; if empty string: then read
:return: python list or dictionary if reading, else None
wtfpl2020 litepresence.com
"""

# DISABLE SELECT PYLINT TESTS
# pylint: disable=broad-except, too-many-branches, too-many-statements
#
# STANDARD MODULES
import os
import time
import traceback
from json import dumps as json_dumps
from json import loads as json_loads


def json_ipc(doc="", text=None, initialize=False, append=False):
    """
    read, write, or append json while mitigating race condition
    """
    # initialize variables
    data = None
    # file operation type for exception message
    if text is not None:
        if append:
            act = "appending"
        else:
            act = "writing"
    else:
        act = "reading"
    # create a clipping tag for read and write operations
    tag = ""
    if not act == "appending":
        tag = "<<< JSON IPC >>>"
    # determine where we are in the file system; change directory to data folder
    path = f"{os.path.dirname(os.path.abspath(__file__))}/data"
    # ensure we're writing json then add prescript and postscript for clipping
    try:
        if text:
            # Only add tags if it's not a .json file
            if doc.endswith(".json"):
                text = json_dumps(json_loads(text))
            else:
                text = tag + json_dumps(json_loads(text)) + tag
    except Exception as error:
        print(text, error.args)
        raise error
    # move append operations to the comptroller folder and add new line
    if append:
        path += "/comptroller"
        text = f"\n{text}"
    # create the pipe subfolder
    if initialize:
        os.makedirs(path, exist_ok=True)
        os.makedirs(f"{path}/comptroller", exist_ok=True)

    if doc:
        doc = f"{path}/{doc}"
        # race read/write until satisfied
        iteration = 0
        while True:
            # increment the delay between attempts exponentially
            time.sleep(0.02 * iteration**2)
            try:
                if act == "appending":
                    with open(doc, "a") as handle:
                        handle.write(text)
                        handle.close()
                        break
                elif act == "writing":
                    with open(doc, "w+") as handle:
                        handle.write(text)
                        handle.close()
                        break
                elif act == "reading":
                    with open(doc, "r") as handle:
                        # only accept legitimate json
                        content = handle.read()
                        if tag and tag in content:
                            data = json_loads(content.split(tag)[1])
                        else:
                            data = json_loads(content)
                        handle.close()
                        break
            except Exception:
                if iteration == 1:
                    print("no json_ipc pipe found, initializing...")
                elif iteration == 5:
                    # maybe there is no pipe? auto initialize the pipe!
                    json_ipc(initialize=True)
                    if act == "reading" and not os.path.exists(f"{path}/{doc}"):
                        raise FileNotFoundError()
                    print("json_ipc pipe initialized, retrying...\n")
                elif iteration == 10:
                    print("json_ipc unexplained failure\n", traceback.format_exc())
                iteration += 1
                continue
            # deliberately double check that the file is closed
            finally:
                try:
                    handle.close()
                except Exception:
                    pass
    return data
