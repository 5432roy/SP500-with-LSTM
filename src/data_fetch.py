import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt

# Set device to cuda
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Assuming 'data/S&P500_5_years.csv' is accessible and in the correct format
# Load data
df = pd.read_csv('data/S&P500_5_years.csv', usecols=['Close/Last', 'Open', 'High', 'Low'])

# Normalize the data
scaler = MinMaxScaler(feature_range=(-1, 1))
scaled_data = scaler.fit_transform(df)

# Function to create sequences
def create_sequences(data, look_back_days):
    xs, ys = [], []
    for i in range(len(data)-look_back_days-1):
        x = data[i:(i+look_back_days)]
        y = data[i+look_back_days][0]  # Predict next close value
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)

look_back_days = 10  # Number of time steps to look back
X, y = create_sequences(scaled_data, look_back_days)
X_train, y_train = torch.FloatTensor(X), torch.FloatTensor(y)

# DataLoader
train_data = TensorDataset(X_train, y_train)
train_loader = DataLoader(train_data, shuffle=True, batch_size=1, drop_last=True)

class StockLSTM(nn.Module):
    def __init__(self, input_size=40, hidden_layer_size=100, output_size=1):
        super().__init__()
        self.hidden_layer_size = hidden_layer_size
        self.lstm = nn.LSTM(input_size, hidden_layer_size)
        self.linear = nn.Linear(hidden_layer_size, output_size)
        self.hidden_cell = (torch.zeros(1,1,self.hidden_layer_size, device=device),
                            torch.zeros(1,1,self.hidden_layer_size, device=device))

    def forward(self, input_seq):
        lstm_out, self.hidden_cell = self.lstm(input_seq.view(len(input_seq), 1, -1), self.hidden_cell)
        predictions = self.linear(lstm_out.view(len(input_seq), -1))
        return predictions[-1]

model = StockLSTM().to(device)
loss_function = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

epochs = 150

for i in range(epochs):
    for seq, labels in train_loader:
        seq, labels = seq.to(device), labels.to(device)
        
        optimizer.zero_grad()
        model.hidden_cell = (torch.zeros(1, 1, model.hidden_layer_size, device=device),
                             torch.zeros(1, 1, model.hidden_layer_size, device=device))

        y_pred = model(seq)
        single_loss = loss_function(y_pred, labels)
        single_loss.backward()
        optimizer.step()

    if i % 25 == 0:
        print(f'epoch: {i:3} loss: {single_loss.item():10.8f}')

    