#!/usr/bin/env python3
"""Small CPU model checks against original gradient routines; no pretrained weights."""
import argparse
import os
import sys
from pathlib import Path
from types import SimpleNamespace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-dir', required=True)
    args = parser.parse_args()
    project = Path(args.project_dir).resolve()
    sys.path[:0] = [str(project), str(project / 'scripts')]
    os.chdir(str(project))
    import torch
    from torch import nn
    import run_ours_direct_candidate_layers as visual
    import run_lga_param_direct_altmodelpred_candidate_layers as parameter
    from run_lga_two_space_ablation import visual_all_grads, cross_stats
    torch.manual_seed(1729)

    class Layer(nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = nn.Parameter(torch.randn(5, 5) / 8)
        def forward(self, h):
            return (torch.tanh((h + h.cumsum(1) / 7) @ self.weight),)

    class Model(nn.Module):
        def __init__(self):
            super().__init__()
            self.layers = nn.ModuleList([Layer() for _ in range(4)])
            self.head = nn.Linear(5, 3, bias=False)
        def forward(self, h):
            for layer in self.layers:
                h = layer(h)[0]
            return SimpleNamespace(logits=self.head(h))

    class VLLM:
        def __init__(self):
            self.model = Model().eval()
            self.embeds = torch.randn(1, 7, 5)
        def prompts_imgs_target_to_xym(self, prompts, images, targets):
            return ({'inputs_embeds': self.embeds.clone(), 'attention_mask': torch.ones(1, 7)}, (1, 3)), torch.tensor([[int(targets[0])]*2]), torch.ones(1, 2)
        def get_llm_outpt(self, inputs, visual_range):
            return self.model(inputs['inputs_embeds'])
        def label_loss(self, logits, labels, masks, average=True):
            return -(logits[:, -2:, :].log_softmax(-1).gather(-1, labels.unsqueeze(-1)).squeeze(-1) * masks).sum() / masks.sum()

    vllm = VLLM()
    for p in vllm.model.parameters():
        p.requires_grad_(False)
    modules = dict(enumerate(vllm.model.layers))
    results = []
    for target in ['0', '1']:
        loss, grads, span = visual_all_grads(visual, vllm, modules, '', None, target)
        for layer, module in modules.items():
            single = visual.compute_virtual_delta_target_grad(vllm, module, '', None, target, 1e-8)
            torch.testing.assert_close(grads[layer], single['visual_grad'], rtol=0, atol=0)
            assert loss == single['loss'] and span == list(single['visual_span'])
        assert grads[0].abs().sum() > 0 and grads[3].abs().sum() == 0
        results.append(grads)
    for layer in modules:
        cross_stats(visual.grad_stats(results[0][layer], results[1][layer], 1e-8))
    # Compare chunked weight derivatives with the independent all-parameter autograd route.
    all_parameters = [layer.weight for layer in vllm.model.layers]
    for target in ['0', '1']:
        for p in all_parameters:
            p.requires_grad_(True)
        loss = parameter.compute_target_loss(vllm, '', None, target)
        reference = torch.autograd.grad(loss, all_parameters)
        for p in all_parameters:
            p.requires_grad_(False)
        for layer in range(4):
            all_parameters[layer].requires_grad_(True)
            _, gradients = parameter.compute_all_layer_grads_for_target(vllm, [{'layer': layer, 'params': [all_parameters[layer]]}], '', None, target)
            torch.testing.assert_close(gradients[layer][0], reference[layer], rtol=0, atol=0)
            all_parameters[layer].requires_grad_(False)
    print('PASS: 8 visual tensor comparisons; zero last layer; 8 chunked parameter comparisons; no weight updates')


if __name__ == '__main__':
    main()
