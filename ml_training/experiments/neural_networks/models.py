"""
Neural Network Models for CSI-Based Localization.

Includes:
1. MLP (Multi-Layer Perceptron) - Simple feedforward network
2. CNN (Convolutional Neural Network) - Exploits frequency structure
3. ResNet - Deep network with skip connections
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class MLPLocalization(nn.Module):
    """
    Multi-Layer Perceptron for position prediction.
    
    Simple feedforward network with progressive dimensionality reduction.
    Good baseline for neural network approaches.
    """
    
    def __init__(self, input_dim=3075, hidden_dims=[1024, 512, 256, 128], dropout_rates=[0.3, 0.3, 0.2, 0.2]):
        """
        Initialize MLP.
        
        Args:
            input_dim: Number of input features (default: 3075)
            hidden_dims: List of hidden layer dimensions
            dropout_rates: List of dropout rates for each hidden layer
        """
        super(MLPLocalization, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims
        
        # Build layers
        layers = []
        prev_dim = input_dim
        
        for hidden_dim, dropout_rate in zip(hidden_dims, dropout_rates):
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout_rate))
            prev_dim = hidden_dim
        
        # Output layer (x, y coordinates)
        layers.append(nn.Linear(prev_dim, 2))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        """
        Forward pass.
        
        Args:
            x: Input features [batch_size, input_dim]
        
        Returns:
            positions: Predicted (x, y) coordinates [batch_size, 2]
        """
        return self.network(x)


class CNNLocalization(nn.Module):
    """
    CNN for position prediction.
    
    Treats per-subcarrier features as 1D signals in frequency domain.
    Exploits frequency continuity and multipath patterns.
    """
    
    def __init__(self, n_subcarriers=1024, n_channels=3):
        """
        Initialize CNN.
        
        Args:
            n_subcarriers: Number of subcarriers (default: 1024)
            n_channels: Number of feature types (RSS, SINR, H_mag = 3)
        """
        super(CNNLocalization, self).__init__()
        
        self.n_subcarriers = n_subcarriers
        self.n_channels = n_channels
        
        # Convolutional layers
        # Input: [batch, 3, 1024]
        self.conv1 = nn.Conv1d(n_channels, 64, kernel_size=7, stride=2, padding=3)
        self.bn1 = nn.BatchNorm1d(64)
        self.pool1 = nn.MaxPool1d(2)
        # After conv1: [batch, 64, 512] -> pool: [batch, 64, 256]
        
        self.conv2 = nn.Conv1d(64, 128, kernel_size=5, stride=2, padding=2)
        self.bn2 = nn.BatchNorm1d(128)
        self.pool2 = nn.MaxPool1d(2)
        # After conv2: [batch, 128, 128] -> pool: [batch, 128, 64]
        
        self.conv3 = nn.Conv1d(128, 256, kernel_size=3, stride=1, padding=1)
        self.bn3 = nn.BatchNorm1d(256)
        # After conv3: [batch, 256, 64]
        
        # Global average pooling
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        # After pooling: [batch, 256, 1] -> squeeze to [batch, 256]
        
        # Fully connected layers
        self.fc1 = nn.Linear(256, 256)
        self.dropout1 = nn.Dropout(0.3)
        self.fc2 = nn.Linear(256, 128)
        self.dropout2 = nn.Dropout(0.2)
        self.fc3 = nn.Linear(128, 2)  # Output: (x, y)
    
    def forward(self, x):
        """
        Forward pass.
        
        Args:
            x: Input features [batch_size, 3, 1024]
               3 channels: RSS, SINR, H_mag
               1024: subcarriers
        
        Returns:
            positions: Predicted (x, y) coordinates [batch_size, 2]
        """
        # Convolutional layers
        x = self.pool1(F.relu(self.bn1(self.conv1(x))))
        x = self.pool2(F.relu(self.bn2(self.conv2(x))))
        x = F.relu(self.bn3(self.conv3(x)))
        
        # Global pooling
        x = self.global_pool(x).squeeze(-1)  # [batch, 256]
        
        # Fully connected layers
        x = F.relu(self.fc1(x))
        x = self.dropout1(x)
        x = F.relu(self.fc2(x))
        x = self.dropout2(x)
        x = self.fc3(x)
        
        return x


class ResBlock(nn.Module):
    """Residual block with skip connection."""
    
    def __init__(self, in_channels, out_channels, stride=1):
        super(ResBlock, self).__init__()
        
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1)
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm1d(out_channels)
        
        # Skip connection
        self.skip = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.skip = nn.Sequential(
                nn.Conv1d(in_channels, out_channels, kernel_size=1, stride=stride),
                nn.BatchNorm1d(out_channels)
            )
    
    def forward(self, x):
        identity = self.skip(x)
        
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += identity  # Skip connection
        out = F.relu(out)
        
        return out


class ResNetLocalization(nn.Module):
    """
    ResNet-style architecture for position prediction.
    
    Deep network with skip connections for better gradient flow.
    Best potential accuracy but more complex to train.
    """
    
    def __init__(self, n_subcarriers=1024, n_channels=3):
        """
        Initialize ResNet.
        
        Args:
            n_subcarriers: Number of subcarriers (default: 1024)
            n_channels: Number of feature types (RSS, SINR, H_mag = 3)
        """
        super(ResNetLocalization, self).__init__()
        
        self.n_subcarriers = n_subcarriers
        self.n_channels = n_channels
        
        # Initial convolution
        self.conv1 = nn.Conv1d(n_channels, 64, kernel_size=7, stride=2, padding=3)
        self.bn1 = nn.BatchNorm1d(64)
        self.pool1 = nn.MaxPool1d(2)
        # After: [batch, 64, 256]
        
        # Residual blocks
        self.res_block1 = ResBlock(64, 64, stride=1)
        self.res_block2 = ResBlock(64, 128, stride=2)
        self.res_block3 = ResBlock(128, 256, stride=2)
        # After res_block3: [batch, 256, 64]
        
        # Global average pooling
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        
        # Fully connected layers
        self.fc1 = nn.Linear(256, 256)
        self.dropout1 = nn.Dropout(0.3)
        self.fc2 = nn.Linear(256, 2)  # Output: (x, y)
        
        # Initialize output layer for position range [10, 90]
        # Bias initialized to center (50), weight scaled for range
        nn.init.normal_(self.fc2.weight, mean=0, std=0.01)
        nn.init.constant_(self.fc2.bias, 50.0)  # Initialize to center of room
    
    def forward(self, x):
        """
        Forward pass.
        
        Args:
            x: Input features [batch_size, 3, 1024]
        
        Returns:
            positions: Predicted (x, y) coordinates [batch_size, 2]
        """
        # Initial convolution
        x = self.pool1(F.relu(self.bn1(self.conv1(x))))
        
        # Residual blocks
        x = self.res_block1(x)
        x = self.res_block2(x)
        x = self.res_block3(x)
        
        # Global pooling
        x = self.global_pool(x).squeeze(-1)
        
        # Fully connected layers
        x = F.relu(self.fc1(x))
        x = self.dropout1(x)
        x = self.fc2(x)
        
        return x


def create_model(model_type='mlp', **kwargs):
    """
    Factory function to create models.
    
    Args:
        model_type: 'mlp', 'cnn', or 'resnet'
        **kwargs: Model-specific arguments
    
    Returns:
        model: PyTorch model
    """
    if model_type == 'mlp':
        return MLPLocalization(**kwargs)
    elif model_type == 'cnn':
        return CNNLocalization(**kwargs)
    elif model_type == 'resnet':
        return ResNetLocalization(**kwargs)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def count_parameters(model):
    """Count trainable parameters in model."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    # Test models
    print("Testing Neural Network Models")
    print("=" * 70)
    
    batch_size = 32
    
    # Test MLP
    print("\n1. MLP Localization")
    print("-" * 70)
    mlp = MLPLocalization(input_dim=3075)
    x_mlp = torch.randn(batch_size, 3075)
    y_mlp = mlp(x_mlp)
    print(f"Input shape: {x_mlp.shape}")
    print(f"Output shape: {y_mlp.shape}")
    print(f"Parameters: {count_parameters(mlp):,}")
    
    # Test CNN
    print("\n2. CNN Localization")
    print("-" * 70)
    cnn = CNNLocalization()
    x_cnn = torch.randn(batch_size, 3, 1024)
    y_cnn = cnn(x_cnn)
    print(f"Input shape: {x_cnn.shape}")
    print(f"Output shape: {y_cnn.shape}")
    print(f"Parameters: {count_parameters(cnn):,}")
    
    # Test ResNet
    print("\n3. ResNet Localization")
    print("-" * 70)
    resnet = ResNetLocalization()
    x_resnet = torch.randn(batch_size, 3, 1024)
    y_resnet = resnet(x_resnet)
    print(f"Input shape: {x_resnet.shape}")
    print(f"Output shape: {y_resnet.shape}")
    print(f"Parameters: {count_parameters(resnet):,}")
    
    print("\n" + "=" * 70)
    print("All models working correctly!")
