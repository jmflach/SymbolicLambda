#!/bin/bash

mode=$1
id=$2

dataset_path="../data/final_datasets/total_beta_red/closed_bool/trad/train"

optimizer="adam,lr=0.0001"

PARAMS=(
## main parameters
--cpu false
--exp_name tests_final  # experiment name
--exp_id $id

--tasks "lambda"                                                 # task
--reload_data "lambda,\
${dataset_path}/data.train,\
${dataset_path}/data.valid,\
${dataset_path}/data.test"
--reload_size 20000000                                                # training set size
--eval_verbose 1
--beam_eval false            # beam evaluation (with false, outputs are only compared with dataset solutions)
--env_base_seed 1
--emb_dim 1024    # model dimension
--n_enc_layers 6  # encoder layers
--n_dec_layers 6  # decoder layers
--n_heads 8       # number of heads
--operators "@:2,l:1"
--max_int 100

--optimizer "${optimizer}"             # model optimizer
--batch_size 32                          # batch size
--epoch_size 50000                      # epoch size (number of equations per epoch)
--max_epoch 50
--validation_metrics valid_prim_fwd_acc  # validation metric (when to save the model)

)

log_file='log_training.txt'

echo $log_file

if [ $mode = 'quiet' ]; then
    python3 main.py ${PARAMS[@]} > $log_file 2>&1
elif [ $mode = 'normal' ]; then
    python3 main.py ${PARAMS[@]}
else
    echo "command not supported"
fi