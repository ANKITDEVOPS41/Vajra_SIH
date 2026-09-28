import torch
import torch.nn as nn

class ConvLSTMCell(nn.Module):
    """
    Core ConvLSTM cell to process a specific spatial resolution and channel depth.
    Takes the concatenated input and hidden states and applies 2D Convolutions 
    to output LSTM gate activations.
    """
    def __init__(self, input_dim, hidden_dim, kernel_size, bias):
        super(ConvLSTMCell, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.padding = kernel_size[0] // 2, kernel_size[1] // 2
        
        # We concatenate the input and hidden along the channel dimension
        self.conv = nn.Conv2d(in_channels=self.input_dim + self.hidden_dim,
                              out_channels=4 * self.hidden_dim,
                              kernel_size=kernel_size,
                              padding=self.padding,
                              bias=bias)

    def forward(self, input_tensor, cur_state):
        h_cur, c_cur = cur_state
        
        # Concatenate input and current hidden state
        combined = torch.cat([input_tensor, h_cur], dim=1) 
        combined_conv = self.conv(combined)
        
        # Split into input, forget, output, and cell gates
        cc_i, cc_f, cc_o, cc_g = torch.split(combined_conv, self.hidden_dim, dim=1)
        
        i = torch.sigmoid(cc_i)
        f = torch.sigmoid(cc_f)
        o = torch.sigmoid(cc_o)
        g = torch.tanh(cc_g)
        
        c_next = f * c_cur + i * g
        h_next = o * torch.tanh(c_next)
        
        return h_next, c_next

    def init_hidden(self, batch_size, image_size, device):
        """Initializes empty hidden states."""
        height, width = image_size
        return (torch.zeros(batch_size, self.hidden_dim, height, width, device=device),
                torch.zeros(batch_size, self.hidden_dim, height, width, device=device))

class LightweightConvLSTM(nn.Module):
    """
    Compact Spatiotemporal ConvLSTM with Encoder-Decoder architecture.
    Avoids OOM by downsampling spatial dimensions before recurrent steps, 
    making it extremely lightweight and laptop GPU friendly.
    
    Inputs: Tensor of shape (Batch, Channels, Seq_in, H, W)
    Outputs: Tensor of shape (Batch, Channels, Seq_out, H, W)
    """
    def __init__(self, in_channels, hidden_channels=16, seq_out=12):
        super().__init__()
        self.seq_out = seq_out
        self.hidden_channels = hidden_channels
        
        # Spatial downsampling to avoid OOM on full 384x384 (Downsamples H, W by 4x)
        self.downsample = nn.Sequential(
            nn.Conv2d(in_channels, hidden_channels, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(hidden_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden_channels, hidden_channels * 2, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(hidden_channels * 2),
            nn.ReLU(inplace=True)
        )
        
        # ConvLSTM cell at reduced spatial resolution (1/4th the original H, W)
        self.convlstm = ConvLSTMCell(input_dim=hidden_channels * 2,
                                     hidden_dim=hidden_channels * 2,
                                     kernel_size=(3, 3), bias=True)
        
        # Spatial upsampling (Upsamples H, W by 4x to original spatial size)
        self.upsample = nn.Sequential(
            nn.ConvTranspose2d(hidden_channels * 2, hidden_channels, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(hidden_channels),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(hidden_channels, in_channels, kernel_size=4, stride=2, padding=1),
            nn.Sigmoid()  # output mapped explicitly to [0, 1] for Min-Max normalized context
        )

    def forward(self, x):
        # Expected x shape: (B, C, Seq_in, H, W)
        B, C, S_in, H, W = x.size()
        
        # Initialize hidden state for ConvLSTM on downsampled spatial dims (stride=2 twice -> H/4, W/4)
        state = self.convlstm.init_hidden(B, (H // 4, W // 4), x.device)
        
        # ENCODING PHASE (process each context frame)
        decoder_in = None
        for t in range(S_in):
            x_t = x[:, :, t, :, :] # Extract fully resolved spatial frame: (B, C, H, W)
            x_t_down = self.downsample(x_t)
            state = self.convlstm(x_t_down, state)
            
            # The final input sequence frame becomes the starting input for forecasting
            if t == S_in - 1:
                decoder_in = x_t_down
            
        # DECODING PHASE (autoregressive prediction of future frames)
        outputs = []
        h, c = state
        
        for t in range(self.seq_out):
            # Recurrent processing for future time step T+t
            h, c = self.convlstm(decoder_in, (h, c))
            
            # Upsample hidden inference to requested spatial dimensions
            out_t = self.upsample(h) # Resolves shape: (B, C, H, W)
            outputs.append(out_t)
            
            # For autoregressive capability, feed the downsampled forecast as next input
            if t < self.seq_out - 1:
                decoder_in = self.downsample(out_t)
            
        # Stack output frames temporally out into (B, C, Seq_out, H, W)
        out = torch.stack(outputs, dim=2)
        return out
