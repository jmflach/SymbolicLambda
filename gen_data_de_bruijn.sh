#!/bin/bash

python3 main.py --export_data true \
--batch_size 32 \
--epoch_size 10000 \
--max_epoch 1000 \
--exp_name de-bruijn \
--num_workers 12 \
--tasks debruijn \
--env_base_seed -1 \
--n_variables 1 \
--n_coefficients 0 \
--leaf_probs "0,0,1,0"  \
--max_ops 125  \
--max_int 1  \
--positive true   \
--max_len 500     \
--cpu false \
--operators "@:2,l:1"
