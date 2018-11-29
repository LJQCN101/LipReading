import torch
import torch.nn.functional as F

from src.data.data_loader import BOS, EOS

def train(encoder, decoding_step, data_loader, opt, device,
          padding_idx, char2idx, teacher_forcing_ratio=1, grad_norm=None):
    """
    Assumes that the sequences given all begin with BOS and end with EOS
    """
    encoder.train()
    decoding_step.train()
    for frames, frame_lens, chars, char_lens in data_loader:
        assert isinstance(chars, torch.LongTensor)
        batch_size = frames.shape[0]
        max_char_len = char_lens.max()

        frames, frame_lens = frames.to(device), frame_lens.to(device)
        chars, char_lens = chars.to(device), char_lens.to(device)

        encoder_hidden_states, prev_state = encoder(frames, frame_lens)

        prev_output = torch.LongTensor([char2idx[BOS]] * batch_size).to(device)
        loss = 0
        for i in range(max_char_len - 1):
            teacher_forcing = torch.rand(1) < teacher_forcing_ratio
            input_ = chars[:,i] if teacher_forcing else prev_output
            if all(x == char2idx[EOS] for x in input_):
                break
            output_log_probs, prev_state = decoding_step(input_, prev_state,
                                                     frame_lens, encoder_hidden_states)
            loss += F.nll_loss(output_log_probs, chars[:,i+1], ignore_index=padding_idx, reduction='sum')
            prev_output = output_log_probs.exp().multinomial(1).squeeze(dim=-1)

        loss.backward()
        print("loss:", loss)
        if grad_norm is not None:
            torch.nn.utils.clip_grad_norm_(encoder.parameters(), grad_norm)
            torch.nn.utils.clip_grad_norm_(decoding_step.parameters(), grad_norm)
        opt.step()
