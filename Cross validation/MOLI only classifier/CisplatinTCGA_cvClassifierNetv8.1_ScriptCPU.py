import torch 
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
import math
import sklearn.preprocessing as sk
import seaborn as sns
from sklearn import metrics
from sklearn.feature_selection import VarianceThreshold
from sklearn.model_selection import train_test_split
from torch.utils.data.sampler import WeightedRandomSampler
from sklearn.metrics import roc_auc_score
from sklearn.metrics import average_precision_score
import random
from sklearn.model_selection import StratifiedKFold

save_results_to = '/home/hnoghabi/CVClassifierResultsv8.1/Cisplatin/'
max_iter = 50
torch.manual_seed(42)

GDSCE = pd.read_csv("GDSC_exprs.Cisplatin.eb_with.TCGA_exprs.Cisplatin.tsv", 
                    sep = "\t", index_col=0, decimal = ",")
GDSCE = pd.DataFrame.transpose(GDSCE)

TCGAE = pd.read_csv("TCGA_exprs.Cisplatin.eb_with.GDSC_exprs.Cisplatin.tsv", 
                   sep = "\t", index_col=0, decimal = ",")
TCGAE = pd.DataFrame.transpose(TCGAE)

TCGAM = pd.read_csv("TCGA_mutations.Cisplatin.tsv", 
                   sep = "\t", index_col=0, decimal = ".")
TCGAM = pd.DataFrame.transpose(TCGAM)
TCGAM = TCGAM.loc[:,~TCGAM.columns.duplicated()]

TCGAC = pd.read_csv("TCGA_CNA.Cisplatin.tsv", 
                   sep = "\t", index_col=0, decimal = ".")
TCGAC = pd.DataFrame.transpose(TCGAC)
TCGAC = TCGAC.loc[:,~TCGAC.columns.duplicated()]

GDSCM = pd.read_csv("GDSC_mutations.Cisplatin.tsv", 
                    sep = "\t", index_col=0, decimal = ".")
GDSCM = pd.DataFrame.transpose(GDSCM)
GDSCM = GDSCM.loc[:,~GDSCM.columns.duplicated()]

GDSCC = pd.read_csv("GDSC_CNA.Cisplatin.tsv", 
                    sep = "\t", index_col=0, decimal = ".")
GDSCC.drop_duplicates(keep='last')
GDSCC = pd.DataFrame.transpose(GDSCC)
GDSCC = GDSCC.loc[:,~GDSCC.columns.duplicated()]

selector = VarianceThreshold(0.05)
selector.fit_transform(GDSCE)
GDSCE = GDSCE[GDSCE.columns[selector.get_support(indices=True)]]

TCGAC = TCGAC.fillna(0)
TCGAC[TCGAC != 0.0] = 1
TCGAM = TCGAM.fillna(0)
TCGAM[TCGAM != 0.0] = 1
GDSCM = GDSCM.fillna(0)
GDSCM[GDSCM != 0.0] = 1
GDSCC = GDSCC.fillna(0)
GDSCC[GDSCC != 0.0] = 1

ls = set(GDSCE.columns.values).intersection(set(GDSCM.columns.values))
ls = set(ls).intersection(set(GDSCC.columns.values))
ls = set(ls).intersection(TCGAE.columns)
ls = set(ls).intersection(TCGAM.columns)
ls = set(ls).intersection(set(TCGAC.columns.values))
ls2 = set(GDSCE.index.values).intersection(set(GDSCM.index.values))
ls2 = set(ls2).intersection(set(GDSCC.index.values))
ls3 = set(TCGAE.index.values).intersection(set(TCGAM.index.values))
ls3 = set(ls3).intersection(set(TCGAC.index.values))
#ls = pd.unique(ls)

TCGAE = TCGAE.loc[ls3,ls]
TCGAM = TCGAM.loc[ls3,ls]
TCGAC = TCGAC.loc[ls3,ls]
GDSCE = GDSCE.loc[ls2,ls]
GDSCM = GDSCM.loc[ls2,ls]
GDSCC = GDSCC.loc[ls2,ls]

GDSCR = pd.read_csv("GDSC_response.Cisplatin.tsv", 
                    sep = "\t", index_col=0, decimal = ",")
TCGAR = pd.read_csv("TCGA_response.Cisplatin.tsv", 
                       sep = "\t", index_col=0, decimal = ",")

GDSCR.rename(mapper = str, axis = 'index', inplace = True)
GDSCR = GDSCR.loc[ls2,:]
#GDSCR.loc[GDSCR.iloc[:,0] == 'R','response'] = 0
#GDSCR.loc[GDSCR.iloc[:,0] == 'S','response'] = 1

TCGAR = TCGAR.loc[ls3,:]
#TCGAR.loc[TCGAR.iloc[:,1] == 'R','response'] = 0
#TCGAR.loc[TCGAR.iloc[:,1] == 'S','response'] = 1

d = {"R":0,"S":1}
GDSCR["response"] = GDSCR.loc[:,"response"].apply(lambda x: d[x])
TCGAR["response"] = TCGAR.loc[:,"response"].apply(lambda x: d[x])

Y = GDSCR['response'].values

ls_mb_size = [30, 36, 60]
ls_h_dim = [1024, 512, 256, 128, 64]
ls_z_dim = [128, 64, 32, 16]
ls_marg = [0.5, 1, 1.5, 2, 2.5]
ls_lr = [0.05, 0.01, 0.001, 0.005, 0.0005, 0.0001,0.00005, 0.00001]
ls_epoch = [20, 50, 10, 15, 30, 40, 60, 70, 80, 90, 100]
ls_rate = [0.5, 0.6]
ls_wd = [0.01, 0.001, 0.1, 0.0001]

skf = StratifiedKFold(n_splits=7, random_state=42)
    
for iters in range(max_iter):
    k = 0
    mbs = random.choice(ls_mb_size)
    hdm = random.choice(ls_h_dim)
    zdm = random.choice(ls_z_dim)
    lre = random.choice(ls_lr)
    lrm = random.choice(ls_lr)
    lrc = random.choice(ls_lr)
    lrCL = random.choice(ls_lr)
    epch = random.choice(ls_epoch)
    wd = random.choice(ls_wd)
    rate = random.choice(ls_rate)
    
    for train_index, test_index in skf.split(GDSCE.values, Y):
        k = k + 1
        X_trainE = GDSCE.values[train_index,:]
        X_testE =  GDSCE.values[test_index,:]
        X_trainM = GDSCM.values[train_index,:]
        X_testM = GDSCM.values[test_index,:]
        X_trainC = GDSCC.values[train_index,:]
        X_testC = GDSCM.values[test_index,:]
        y_trainE = Y[train_index]
        y_testE = Y[test_index]
        
        scalerGDSC = sk.StandardScaler()
        scalerGDSC.fit(X_trainE)
        X_trainE = scalerGDSC.transform(X_trainE)
        X_testE = scalerGDSC.transform(X_testE)

        X_trainM = np.nan_to_num(X_trainM)
        X_trainC = np.nan_to_num(X_trainC)
        X_testM = np.nan_to_num(X_testM)
        X_testC = np.nan_to_num(X_testC)
        
        TX_testE = torch.FloatTensor(X_testE)
        TX_testM = torch.FloatTensor(X_testM)
        TX_testC = torch.FloatTensor(X_testC)
        ty_testE = torch.FloatTensor(y_testE.astype(int))
        
        #Train
        class_sample_count = np.array([len(np.where(y_trainE==t)[0]) for t in np.unique(y_trainE)])
        weight = 1. / class_sample_count
        samples_weight = np.array([weight[t] for t in y_trainE])

        samples_weight = torch.from_numpy(samples_weight)
        sampler = WeightedRandomSampler(samples_weight.type('torch.DoubleTensor'), len(samples_weight), replacement=True)

        mb_size = mbs

        trainDataset = torch.utils.data.TensorDataset(torch.FloatTensor(X_trainE), torch.FloatTensor(X_trainM), 
                                                      torch.FloatTensor(X_trainC), torch.FloatTensor(y_trainE.astype(int)))

        trainLoader = torch.utils.data.DataLoader(dataset = trainDataset, batch_size=mb_size, shuffle=False, num_workers=1, sampler = sampler)

        n_sampE, IE_dim = X_trainE.shape
        n_sampM, IM_dim = X_trainM.shape
        n_sampC, IC_dim = X_trainC.shape

        h_dim = hdm
        Z_dim = zdm
        Z_in = h_dim + h_dim + h_dim
        lrE = lre
        lrM = lrm
        lrC = lrc
        epoch = epch

        costtr = []
        auctr = []
        costts = []
        aucts = []

        class AEE(nn.Module):
            def __init__(self):
                super(AEE, self).__init__()
                self.EnE = torch.nn.Sequential(
                    nn.Linear(IE_dim, h_dim),
                    nn.BatchNorm1d(h_dim),
                    nn.ReLU(),
                    nn.Dropout())
            def forward(self, x):
                output = self.EnE(x)
                return output

        class AEM(nn.Module):
            def __init__(self):
                super(AEM, self).__init__()
                self.EnM = torch.nn.Sequential(
                    nn.Linear(IM_dim, h_dim),
                    nn.BatchNorm1d(h_dim),
                    nn.ReLU(),
                    nn.Dropout())
            def forward(self, x):
                output = self.EnM(x)
                return output    


        class AEC(nn.Module):
            def __init__(self):
                super(AEC, self).__init__()
                self.EnC = torch.nn.Sequential(
                    nn.Linear(IM_dim, h_dim),
                    nn.BatchNorm1d(h_dim),
                    nn.ReLU(),
                    nn.Dropout())
            def forward(self, x):
                output = self.EnC(x)
                return output      
        class Classifier(nn.Module):
            def __init__(self):
                super(Classifier, self).__init__()
                self.FC = torch.nn.Sequential(
                    nn.Linear(Z_in, Z_dim),
                    nn.ReLU(),
                    nn.Dropout(rate),
                    nn.Linear(Z_dim, 1),
                    nn.Dropout(rate),
                    nn.Sigmoid())
            def forward(self, x):
                return self.FC(x)
        
        torch.cuda.manual_seed_all(42)

        AutoencoderE = AEE()
        AutoencoderM = AEM()
        AutoencoderC = AEC()

        solverE = optim.Adagrad(AutoencoderE.parameters(), lr=lrE)
        solverM = optim.Adagrad(AutoencoderM.parameters(), lr=lrM)
        solverC = optim.Adagrad(AutoencoderC.parameters(), lr=lrC)

        Clas = Classifier()
        SolverClass = optim.SGD(Clas.parameters(), lr=lrCL, weight_decay = wd)
        C_loss = torch.nn.BCELoss()

        for it in range(epoch):

            epoch_cost4 = 0
            epoch_cost3 = []
            num_minibatches = int(n_sampE / mb_size) 

            for i, (dataE, dataM, dataC, target) in enumerate(trainLoader):
                flag = 0
                AutoencoderE.train()
                AutoencoderM.train()
                AutoencoderC.train()
                Clas.train()
                
                if torch.mean(target)!=0. and torch.mean(target)!=1.:                      

                    ZEX = AutoencoderE(dataE)
                    ZMX = AutoencoderM(dataM)
                    ZCX = AutoencoderC(dataC)

                    ZT = torch.cat((ZEX, ZMX, ZCX), 1)
                    ZT = F.normalize(ZT, p=2, dim=0)

                    Pred = Clas(ZT)
                    loss = C_loss(Pred,target.view(-1,1))   

                    y_true = target.view(-1,1)
                    y_pred = Pred
                    AUC = roc_auc_score(y_true.detach().numpy(),y_pred.detach().numpy()) 

                    solverE.zero_grad()
                    solverM.zero_grad()
                    solverC.zero_grad()
                    SolverClass.zero_grad()

                    loss.backward()

                    solverE.step()
                    solverM.step()
                    solverC.step()
                    SolverClass.step()
                    
                    epoch_cost4 = epoch_cost4 + (loss / num_minibatches)
                    epoch_cost3.append(AUC)
                    flag = 1

            if flag == 1:
                costtr.append(torch.mean(epoch_cost4))
                auctr.append(np.mean(epoch_cost3))
                print('Iter-{}; Total loss: {:.4}'.format(it, loss))

            with torch.no_grad():

                AutoencoderE.eval()
                AutoencoderM.eval()
                AutoencoderC.eval()
                Clas.eval()

                ZET = AutoencoderE(TX_testE)
                ZMT = AutoencoderM(TX_testM)
                ZCT = AutoencoderC(TX_testC)

                ZTT = torch.cat((ZET, ZMT, ZCT), 1)
                ZTT = F.normalize(ZTT, p=2, dim=0)

                PredT = Clas(ZTT)
                lossT = C_loss(PredT,ty_testE.view(-1,1))         

                y_truet = ty_testE.view(-1,1)
                y_predt = PredT
                AUCt = roc_auc_score(y_truet.detach().numpy(),y_predt.detach().numpy())

                costts.append(lossT)
                aucts.append(AUCt)

        plt.plot(np.squeeze(costtr), '-r',np.squeeze(costts), '-b')
        plt.ylabel('Total cost')
        plt.xlabel('iterations (per tens)')

        title = 'Cost Cisplatin iter = {}, fold = {}, mb_size = {},  hz_dim[1,2] = ({},{}), lr[E,M,C] = ({}, {}, {}), epoch = {}, wd = {}, lrCL = {}, rate4 = {}'.\
                      format(iters, k, mbs, hdm, zdm , lre, lrm, lrc, epch, wd, lrCL, rate)

        plt.suptitle(title)
        plt.savefig(save_results_to + title + '.png', dpi = 150)
        plt.close()

        plt.plot(np.squeeze(auctr), '-r',np.squeeze(aucts), '-b')
        plt.ylabel('AUC')
        plt.xlabel('iterations (per tens)')

        title = 'AUC Cisplatin iter = {}, fold = {}, mb_size = {},  hz_dim[1,2] = ({},{}), lr[E,M,C] = ({}, {}, {}), epoch = {}, wd = {}, lrCL = {}, rate4 = {}'.\
                      format(iters, k, mbs, hdm, zdm , lre, lrm, lrc, epch, wd, lrCL, rate)        

        plt.suptitle(title)
        plt.savefig(save_results_to + title + '.png', dpi = 150)
        plt.close()
