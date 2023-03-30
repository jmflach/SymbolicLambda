"""
Generate a parameters parser.
"""
# parse parameters
parser = argparse.ArgumentParser(description="Language transfer")

# main parameters
parser.add_argument("--dump_path", type=str, default="./dumped/",
                    help="Experiment dump path")
parser.add_argument("--exp_name", type=str, default="debug",
                    help="Experiment name")
parser.add_argument("--save_periodic", type=int, default=0,
                    help="Save the model periodically (0 to disable)")
parser.add_argument("--exp_id", type=str, default="",
                    help="Experiment ID")

# float16 / AMP API
parser.add_argument("--fp16", type=bool_flag, default=False,
                    help="Run model with float16")
parser.add_argument("--amp", type=int, default=-1,
                    help="Use AMP wrapper for float16 / distributed / gradient accumulation. Level of optimization. -1 to disable.")

# model parameters
parser.add_argument("--emb_dim", type=int, default=256,
                    help="Embedding layer size")
parser.add_argument("--n_enc_layers", type=int, default=4,
                    help="Number of Transformer layers in the encoder")
parser.add_argument("--n_dec_layers", type=int, default=4,
                    help="Number of Transformer layers in the decoder")
parser.add_argument("--n_heads", type=int, default=4,
                    help="Number of Transformer heads")
parser.add_argument("--dropout", type=float, default=0,
                    help="Dropout")
parser.add_argument("--attention_dropout", type=float, default=0,
                    help="Dropout in the attention layer")
parser.add_argument("--share_inout_emb", type=bool_flag, default=True,
                    help="Share input and output embeddings")
parser.add_argument("--sinusoidal_embeddings", type=bool_flag, default=False,
                    help="Use sinusoidal embeddings")

# training parameters
parser.add_argument("--env_base_seed", type=int, default=0,
                    help="Base seed for environments (-1 to use timestamp seed)")
parser.add_argument("--max_len", type=int, default=512,
                    help="Maximum sequences length")
parser.add_argument("--batch_size", type=int, default=32,
                    help="Number of sentences per batch")
parser.add_argument("--optimizer", type=str, default="adam,lr=0.0001",
                    help="Optimizer (SGD / RMSprop / Adam, etc.)")
parser.add_argument("--clip_grad_norm", type=float, default=5,
                    help="Clip gradients norm (0 to disable)")
parser.add_argument("--epoch_size", type=int, default=300000,
                    help="Epoch size / evaluation frequency")
parser.add_argument("--max_epoch", type=int, default=100000,
                    help="Maximum epoch size")
parser.add_argument("--stopping_criterion", type=str, default="",
                    help="Stopping criterion, and number of non-increase before stopping the experiment")
parser.add_argument("--validation_metrics", type=str, default="",
                    help="Validation metrics")
parser.add_argument("--accumulate_gradients", type=int, default=1,
                    help="Accumulate model gradients over N iterations (N times larger batch sizes)")
parser.add_argument("--num_workers", type=int, default=10,
                    help="Number of CPU workers for DataLoader")
parser.add_argument("--same_nb_ops_per_batch", type=bool_flag, default=False,
                    help="Generate sequences with the same number of operators in batches.")

# export data / reload it
parser.add_argument("--export_data", type=bool_flag, default=False,
                    help="Export data and disable training.")
parser.add_argument("--reload_data", type=str, default="",
                    help="Load dataset from the disk (task1,train_path1,valid_path1,test_path1;task2,train_path2,valid_path2,test_path2)")
parser.add_argument("--reload_size", type=int, default=-1,
                    help="Reloaded training set size (-1 for everything)")

# environment parameters
parser.add_argument("--env_name", type=str, default="char_sp",
                    help="Environment name")
ENVS[parser.parse_known_args()[0].env_name].register_args(parser)

# tasks
parser.add_argument("--tasks", type=str, default="",
                    help="Tasks")

# beam search configuration
parser.add_argument("--beam_eval", type=bool_flag, default=False,
                    help="Evaluate with beam search decoding.")
parser.add_argument("--beam_size", type=int, default=1,
                    help="Beam size, default = 1 (greedy decoding)")
parser.add_argument("--beam_length_penalty", type=float, default=1,
                    help="Length penalty, values < 1.0 favor shorter sentences, while values > 1.0 favor longer ones.")
parser.add_argument("--beam_early_stopping", type=bool_flag, default=True,
                    help="Early stopping, stop as soon as we have `beam_size` hypotheses, although longer ones may have better scores.")

# reload pretrained model / checkpoint
parser.add_argument("--reload_model", type=str, default="",
                    help="Reload a pretrained model")
parser.add_argument("--reload_checkpoint", type=str, default="",
                    help="Reload a checkpoint")

# evaluation
parser.add_argument("--eval_only", type=bool_flag, default=False,
                    help="Only run evaluations")
parser.add_argument("--eval_verbose", type=int, default=0,
                    help="Export evaluation details")
parser.add_argument("--eval_verbose_print", type=bool_flag, default=False,
                    help="Print evaluation details")

# debug
parser.add_argument("--debug_slurm", type=bool_flag, default=False,
                    help="Debug multi-GPU / multi-node within a SLURM job")
parser.add_argument("--debug", help="Enable all debug flags",
                    action="store_true")

# CPU / multi-gpu / multi-node
parser.add_argument("--cpu", type=bool_flag, default=False,
                    help="Run on CPU")
parser.add_argument("--local_rank", type=int, default=-1,
                    help="Multi-GPU - Local rank")
parser.add_argument("--master_port", type=int, default=-1,
                    help="Master port (for multi-node SLURM jobs)")

"""
Register environment parameters.
"""
parser.add_argument("--operators", type=str, default="add:2,sub:1",
                    help="Operators (add, sub, mul, div), followed by weight")
parser.add_argument("--max_ops", type=int, default=10,
                    help="Maximum number of operators")
parser.add_argument("--max_ops_G", type=int, default=4,
                    help="Maximum number of operators for G in IPP")
parser.add_argument("--max_int", type=int, default=10000,
                    help="Maximum integer value")
parser.add_argument("--int_base", type=int, default=10,
                    help="Integer representation base")
parser.add_argument("--balanced", type=bool_flag, default=False,
                    help="Balanced representation (base > 0)")
parser.add_argument("--precision", type=int, default=10,
                    help="Float numbers precision")
parser.add_argument("--positive", type=bool_flag, default=False,
                    help="Do not sample negative numbers")
parser.add_argument("--rewrite_functions", type=str, default="",
                    help="Rewrite expressions with SymPy")
parser.add_argument("--leaf_probs", type=str, default="0.75,0,0.25,0",
                    help="Leaf probabilities of being a variable, a coefficient, an integer, or a constant.")
parser.add_argument("--n_variables", type=int, default=1,
                    help="Number of variables in expressions (between 1 and 4)")
parser.add_argument("--n_coefficients", type=int, default=0,
                    help="Number of coefficients in expressions (between 0 and 10)")
parser.add_argument("--clean_prefix_expr", type=bool_flag, default=True,
                    help="Clean prefix expressions (f x -> Y, derivative f x x -> Y')")
