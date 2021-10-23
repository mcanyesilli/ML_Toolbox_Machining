"""
Feature extraction and supervised classification using EEMD 
-----------------------------------------------------------

This function takes time series for turning cutting tests as inputs.
It ask user to enter the file paths for the data files. If user specify that the decompositions for EEMD have already been computed, algorithm will ask user to enter the file paths for the decompositions.
Otherwise, it will compute the IMFs and ask users to enter the file paths where they want to save these decompositions.
Based on given stickout length cases and corresponding informative IMF numbers, it will generate the feature matrix and perform the classification with specified classification algorithm by user.
It returns the results in an array and prints the total elapsed time.

"""
import time
start2 = time.time()
import numpy as np
from PyEMD import EEMD
import scipy.io as sio
import os.path
import sys
from scipy.stats import skew


def preprocess_chatter_data(data_path,list_name):
    
    # file path to folder where the data is kept
    file_path = data_path+'\\'+list_name

    # read the file that includes the name of datafiles
    with open(file_path) as f:
        data_names = f.read().splitlines()
        
    N = len(data_names)
   
    # Loading time series and labels of the classification
    
    # import the time series
    N = len(data_names)     
    data_L = []
    data = {}
    #load datasets and compute features
    for i in range (0,N):
        name = '%s' %(data_names[i])
        ts = sio.loadmat(data_path+'\\'+name)['tsDS'] 
        L = len(ts)
        data_L.append(L)
        
        # extract rpm and depth of cut information from name of the data set
        rpm = np.full((L,1),int(name[2:5]))
        if name[5]=='_':
            doc = np.full((L,1),int(name[6:9])*0.001)
        else:
            doc = np.full((L,1),int(name[7:10])*0.001)
            
        # time series with "i" and "c" represents 
        if name[0] == 's':
            stability = np.full((L,1),0)
        else:
            stability = np.full((L,1),1)
        
        data[i] = np.concatenate((ts,rpm,doc,stability),axis=1)
    
    # total data points in whole data set
    total_L = sum(data_L)
    
    # find the approximate number of time series after we split them into small ones
    app_num_ts = total_L//1000
    
    # generate arrays for the split data
    split_data = np.ndarray(shape=(app_num_ts),dtype=object)
    split_labels = np.ndarray(shape=(app_num_ts,3))
    inc = 0 # increment that counts the number of total splits
    for i in range(N):
        ts = data[i]
    
        # splitting 
        if len(ts)>1000:
            num_splits = len(ts)//1000
            split = np.array_split(ts,num_splits) 
            
            for j in range(num_splits):
                split_data[inc] = split[j][:,0:2]
                split_labels[inc] = split[j][0,2:5]
                inc = inc+1
    # remove the empty rows from the split arrays
    split_data = split_data[:inc]
    split_labels = split_labels[:inc]
    
    return split_data, split_labels

def EEMD_IMF_Compute(data_path,list_name, EEMDecs, saving, *args):
    """
    
          
    """

    # split the data into small chunks to reduce time to compute IMFs
    split_data, split_labels = preprocess_chatter_data(data_path,list_name)
 
      
    # Compute IMFs if they are not computed before
    if EEMDecs=='NA':
        # generate the array that stores the decomposition
        infoEMF=np.ndarray(shape=(len(split_data)),dtype=object) 
        
        eemd = EEMD()
        emd = eemd.EMD
        emd.trials = 200      #default = 100
        emd.noise_width = 0.2 #default = 0.05

        # Chosen imf for feature extraction
        for i in range(0,len(split_data)): 
        
            #signal
            S = split_data[i][:,1]
            t = split_data[i][:,0]
            
            eIMFs = emd(S, t)
            infoEMF[i]=eIMFs  
            print('Progress: IMFs were computed for case number {}.  '.format(i))
    
        #save eIMFs into mat file
        if saving:
            saving_path = args[0]
            name = saving_path+'\\IMFs_Case_%i'%(i+1)
            np.save(name, infoEMF)
           
    elif EEMDecs=='A':
        load_path = args[0]
        dataname = load_path+'\\IMFs.npy'
        infoEMF = np.load(dataname,allow_pickle=True)
            
    return infoEMF,split_labels
    
def EEMD_Feature_Compute(infoEMF,p):
    
    features = np.zeros((len(infoEMF),7))
    
    for i in range(0,len(infoEMF)):
        eIMFs = infoEMF[i]
        #feature_1
        nIMFs=len(eIMFs)
        A = np.power(eIMFs[p-1],2) 
        A_sum = sum(A)                                   #summing squares of whole elements of second IMF
        B_sum = 0               
        for k in range(nIMFs):
            B_sum = B_sum + sum(np.power(eIMFs[k],2))   #computing summing of squares of whole elements of IMFs
        features[i,0]=A_sum/B_sum                        #energy ratio feature
        
        #feature_2  Peak to peak value
        Maximum = max(eIMFs[p-1])
        Minimum = min(eIMFs[p-1])
        features[i,1] = Maximum - Minimum 
        #feature_3 standard deviation
        features[i,2] = np.std(eIMFs[p-1])
        #feature_4 root mean square (RMS)
        features[i,3] = np.sqrt(np.mean(eIMFs[p-1]**2))   
        #feature_5 Crest factor
        features[i,4] = Maximum/features[i,3]
        #feature_6 Skewness
        features[i,5] = skew(eIMFs[p-1])
        #feature_7 Kurtosis
        L= len(eIMFs[p-1])
        features[i,6] = sum(np.power(eIMFs[p-1]-np.mean(eIMFs[p-1]),4)) / ((L-1)*np.power(features[i,3],4))
    
    return features
     
