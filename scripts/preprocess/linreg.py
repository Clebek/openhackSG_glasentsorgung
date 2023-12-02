from sklearn.linear_model import LinearRegression

def fuellrate(df):
    #input:
    #df mit Spalten 'seconds' und 'data_distance'
    #output:
    #Fuellzunahme in mm pro Stunde
    reg = LinearRegression().fit(df['seconds'].values.reshape(-1,1),df['data_distance'])
    return -reg.coef_[0] * 60*60