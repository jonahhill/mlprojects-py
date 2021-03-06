#import theano
#theano.config.device = 'gpu'
#theano.config.floatX = 'float32'


import numpy as np

import pandas as pd
import math as math
from sklearn import preprocessing

from tsforecasttools import run_timeseries_froecasts

from mltools import rolling_univariate_window, build_rolling_window_dataset, verify_window_dataset
from mltools import train_test_split,print_graph_test,almost_correct_based_accuracy, MLConfigs, shuffle_data
from mltools import regression_with_dl, print_regression_model_summary, report_scores, calcuate_time_since_event, calcuate_window_operation
from mltools import create_window_based_features, preprocess1DtoZeroMeanUnit, preprocess2DtoZeroMeanUnit
from mltools import create_rondomsearch_configs4DL, check_assending

from keras.optimizers import Adam, SGD

from datetime import datetime


df = pd.read_csv("data/rossmann300stores.csv")

#We take 10 from first store
#df = df[(df['Store'] == 1)].head(100)

print("data frame Shape", df.shape, list(df))

check_assending(df, 'Date','%Y-%m-%d')
lb2IntEncoder = preprocessing.LabelEncoder()
df.StateHoliday  = lb2IntEncoder.fit_transform(df.StateHoliday)

dateList = [ datetime.strptime(d, '%Y-%m-%d') for d in df['Date']]
df['Month'] = [d.month for d in dateList]
df['DayOfMonth'] = [d.day for d in dateList]

df['dayOfWeekCos'] = [w* math.pi/6 for w in df['DayOfWeek'].values]

df = df.drop('Date',1)
df = df.drop('Customers',1)
#df = df.drop('SchoolHoliday',1)
#df = df.drop('StateHoliday',1)


sales_data = df['Sales'].values.astype("float32")
sales_data, parmsFromNormalization = preprocess1DtoZeroMeanUnit(sales_data)
df['Sales'] = sales_data

headerNames = []
window_size = 14
storeList = df['Store'].unique()

x_train_list = []
x_test_list = []
y_train_list = []
y_test_list = []


for s in storeList:
    dfS = df[(df['Store'] == s)]
    sales_data = dfS['Sales'].values

    if(len(x_train_list) == 0):
        print s, "data", sales_data[:10]
        #to do verify output

    X_all_t, Y_all_t = build_rolling_window_dataset(sales_data, window_size)
    #verify_window_dataset(X_all_t,Y_all_t)
    timeSincePromotion = calcuate_time_since_event(dfS['Promo'].values,0)

    dfS = dfS.drop('Sales',1)

    #remove first window_size-1 and last from data frame
    row_count = len(dfS.index);
    index2remove = [row_count-1];
    for i in xrange(0,window_size-1):
        index2remove.append(i)

    dfS = dfS.drop(dfS.index[index2remove])
    #print dfS.describe()
    headerNames = list(dfS)
    #covert data frame to numpy array
    X_without_sales = dfS.values.copy()
    X_without_sales = preprocess2DtoZeroMeanUnit(X_without_sales)
    #print("X_all.shape", X_all_t.shape, "X_without_sales.shape", X_without_sales.shape)
    #join two arrays ( also can do np.row_stack )
    timeSincePromotion = timeSincePromotion[window_size-1:-1]

    wfeatures = create_window_based_features(sales_data, window_size)
    wfeatures = wfeatures[window_size - 1:-1,]

    dayOfWeekCos = dfS['dayOfWeekCos'].values
    w1cosratio = [X_all_t[i][0]/dayOfWeekCos[i] for i in range(len(dayOfWeekCos))]
    w1cosproduct = [X_all_t[i][0] * dayOfWeekCos[i] for i in range(len(dayOfWeekCos))]
    wecosratio = [X_all_t[i][window_size-1] / dayOfWeekCos[i] for i in range(len(dayOfWeekCos))]
    wecosproduct = [X_all_t[i][window_size-1] * dayOfWeekCos[i] for i in range(len(dayOfWeekCos))]
    #print(X_without_sales.shape, 1, wfeatures.shape, 1, 1, 1, 1, X_all_t.shape)
    X_all_t = np.column_stack((X_without_sales, timeSincePromotion, wfeatures, w1cosratio, w1cosproduct, wecosratio, wecosproduct, X_all_t))
    #print("X_all.shape", X_all_t.shape)

    training_set_size = int(0.7*X_all_t.shape[0])
    X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(training_set_size, X_all_t, Y_all_t)

    x_train_list.append(X_train_s)
    x_test_list.append(X_test_s)
    y_train_list.append(y_train_s)
    y_test_list.append(y_test_s)

#put the store data back togehter
X_train = np.row_stack(x_train_list)
X_test = np.row_stack(x_test_list)
Y_train = np.concatenate(y_train_list, axis=0)
Y_test = np.concatenate(y_test_list, axis=0)


#X_all = storeData[0]
#Y_all = target[0]
#for i in range(1,len(storeData)):
    #print("DebugX", i, X_all.shape, sales_data[i].shape)#
#    X_all = np.row_stack((X_all, storeData[i]))
    #print("Debug", i,Y_all.shape, target[i].shape)
#    Y_all = np.concatenate((Y_all, target[i]), 0)

#if X_all.shape[0] != Y_all.shape[0]:
    #raise  ValueError("X_all and Y_all does not match")


#takes numpy array from data frame
#row_count = X_all.shape[0]
#print("sales_data.shape", sales_data.shape)

#print("X_all.shape", X_all.shape, "Y_all", Y_all.shape)

#print X_all[:10]


print "X_train", X_train[:10]
print "Y_train", Y_train[:10]


#todo verif(df[], X_train, Y_train)

#put both together, shuffle, and  break
X_all_temp, Y_all_temp = shuffle_data(X_train, Y_train)
X_train = X_all_temp
Y_train = Y_all_temp

df = df.drop('Sales',1)

headers = headerNames + ['TimeSincePromotion', 'ma1', 'ma2', 'ma4', 'ma8', 'entropy', 'stddev', 'valueBeforeWeek',
                      'w1cosratio', 'w1cosproduct', 'wecosratio', 'wecosproduct'] + ["W"+str(i) for i in range(window_size)]
print [str(i) +"="+ headers[i]+" " for i in range(len(headers))]



#X_train, X_test, y_train, y_test = train_test_split(training_set_size, X_all, Y_all)
#run_timeseries_froecasts(X_train, y_train, X_test, y_test, window_size, 10, parmsFromNormalization)


configs = [
#    MLConfigs(nodes_in_layer = 500, number_of_hidden_layers = 2, droput = 0, activation_fn='relu', loss= "mse",
#        epoch_count = 10, optimizer = SGD(lr=0.1, decay=1e-3, momentum=0.99, nesterov=True)),
    #MLConfigs(nodes_in_layer=1000, number_of_hidden_layers=2, droput=0.2, activation_fn='relu', loss="mse",
    #          epoch_count=10, optimizer=SGD(lr=0.001, decay=1e-4, momentum=0.9, nesterov=True)),

    #MLConfigs(nodes_in_layer = 1000, number_of_hidden_layers = 1, dropout = 0.0, activation_fn='relu', loss= "mse",
    #    epoch_count = 30, optimizer = Adam()),
    #MLConfigs(nodes_in_layer=20, number_of_hidden_layers=3, dropout=0.1, activation_fn='relu', loss="mse",
    #          epoch_count=500, optimizer=Adam()),
    #MLConfigs(nodes_in_layer=10, number_of_hidden_layers=2, dropout=0, activation_fn='relu', loss="mse",
    #          epoch_count=50, optimizer=Adam()),
    #MLConfigs(nodes_in_layer=30, number_of_hidden_layers=2, dropout=0, activation_fn='relu', loss="mse",
    #          epoch_count=50, optimizer=Adam()),
    #MLConfigs(nodes_in_layer=30, number_of_hidden_layers=2, dropout=0.2, activation_fn='relu', loss="mse",
    #          epoch_count=50, optimizer=Adam()),
    #MLConfigs(nodes_in_layer=50, number_of_hidden_layers=2, dropout=0.2, activation_fn='relu', loss="mse",
    #          epoch_count=50, optimizer=Adam()),

    #MLConfigs(nodes_in_layer=1000, number_of_hidden_layers=2, dropout=0.2, activation_fn='relu', loss="mse",
    #          epoch_count=10, optimizer=Adam()),

    ##MLConfigs(nodes_in_layer=1000, number_of_hidden_layers=5, dropout=0.0, activation_fn='relu', loss="mse",
    #          epoch_count=30, optimizer=Adam()),
    #MLConfigs(nodes_in_layer=1000, number_of_hidden_layers=5, dropout=0.2, activation_fn='relu', loss="mse",
    #          epoch_count=30, optimizer=Adam()),


    #lr=0.01
    MLConfigs(nodes_in_layer=20, number_of_hidden_layers=3, dropout=0.0, activation_fn='relu', loss="mse",
              epoch_count=200, optimizer=Adam(lr=0.0001), regularization=0.001),
    #MLConfigs(nodes_in_layer=10, number_of_hidden_layers=3, dropout=0, activation_fn='relu', loss="mse",
    #          epoch_count=500, optimizer=SGD(lr=0.001, decay=1e-6, momentum=0.5, nesterov=True)),

    #MLConfigs(nodes_in_layer = 20, number_of_hidden_layers = 3, dropout = 0.2, activation_fn='relu', loss= "mse",
    #    epoch_count = 500, optimizer = SGD(lr=0.0001, decay=0, momentum=0.9, nesterov=True)),

    #MLConfigs(nodes_in_layer = 500, number_of_hidden_layers = 2, droput = 0, activation_fn='relu', loss= "mse",
    #    epoch_count = 10, optimizer = SGD(lr=0.1, decay=1e-3, momentum=0.99, nesterov=True)),
    #MLConfigs(nodes_in_layer = 500, number_of_hidden_layers = 2, droput = 0, activation_fn='relu', loss= "mse",
    #    epoch_count = 10, optimizer = SGD(lr=0.1, decay=1e-3, momentum=0.99, nesterov=True)),
    #MLConfigs(nodes_in_layer = 500, number_of_hidden_layers = 2, droput = 0, activation_fn='relu', loss= "mse",
    #    epoch_count = 10, optimizer = SGD(lr=0.1, decay=1e-3, momentum=0.99, nesterov=True)),
    #MLConfigs(nodes_in_layer = 500, number_of_hidden_layers = 10, droput = 0, activation_fn='relu', loss= "mse",
    #    epoch_count = 10, optimizer = SGD(lr=0.1, decay=1e-3, momentum=0.99, nesterov=True))
    ]

#configs = create_rondomsearch_configs4DL((1,2,3), (5,10,15,20), (0, 0.1, 0.2, 0.4),
#                                        (0, 0.01, 0.001), (0.01, 0.001, 0.0001), 50)
#configs = create_rondomsearch_configs4DL((1,2,3), (100, 200, 300), (0, 0.1, 0.2, 0.4),
#                                        (0, 0.01, 0.001), (0.01, 0.001, 0.0001), 40)

index = 0
for c in configs:
    c.epoch_count = 50
    y_pred_dl = regression_with_dl(X_train, Y_train, X_test, Y_test, c)
    print ">> %d %s" %(index, str(c.tostr()))
    print_regression_model_summary("DL", Y_test, y_pred_dl, parmsFromNormalization)
    index = index + 1

