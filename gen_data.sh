#!/bin/bash

python3 main.py --export_data true \
--batch_size 32 \
--epoch_size 10000 \
--max_epoch 100 \
--exp_name lambda-data \
--num_workers 1 \
--tasks lambda \
--env_base_seed -1 \
--n_variables 3 \
--n_coefficients 0 \
--leaf_probs "1,0,0,0"  \
--max_ops 50  \
--max_int 1  \
--positive true   \
--max_len 50     \
--cpu true \
--operators "@:500,l:500"
