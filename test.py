import subprocess
import threading
from os.path import exists

import pandas
import pandas as pd

file_exists = exists('/Users/quentin/Documents/Documents - MacBook Pro de Quentin/Stage/Livrables/Validation semantiques/ML/tests/Analyse des donnees textuelles/SABC/classification/data/df_bytitle_test.csv')
df = pd.read_csv("/Users/quentin/Documents/Documents - MacBook Pro de Quentin/Stage/Livrables/Validation semantiques/ML/tests/Analyse des donnees textuelles/SABC/classification/data/df_bytitle_test.csv")

print(df.to_csv('file.csv', encoding='utf-8-sig'))

#Subprocess call
def PopenCall(onExit, PopenArgs):
    def runInThread(onExit, PopenArgs):
        script_ID = PopenArgs[1]
        proc = subprocess.Popen(PopenArgs)
        proc.wait()
        onExit(script_ID)
        return

    thread = threading.Thread(target=runInThread, args=(onExit, PopenArgs))
    thread.start()

    return thread

def onExit(script_ID):
    print("Done processing", script_ID + ".")

PopenArgs = [
    "python",
    "./scripts/rt_datarobot-predict.py",
    df.to_csv('file.csv', encoding='utf-8-sig')
]
print ("Running {} in background.......".format(PopenArgs))
job_thread = PopenCall(onExit, PopenArgs)
job_thread.join()

print(file_exists)
#%%

#%%
