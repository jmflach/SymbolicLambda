# Copyright (c) 2020-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#

from logging import getLogger
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
import os
import torch
import sympy as sp
import sys
from .utils import to_cuda, timeout, TimeoutError
from .envs.char_sp import InvalidPrefixExpression, is_valid_expr
from .envs.sympy_utils import simplify
import json

sys.path.append('../lambda-calculus/src')

import lambda_utils as lambda_calculus
logger = getLogger()


BUCKET_LENGTH_SIZE = 5


def idx_to_sp(env, idx, return_infix=False):
    """
    Convert an indexed prefix expression to SymPy.
    """
    #print(f'converting {idx}')
    prefix = [env.id2word[wid] for wid in idx]
    #print(f'prefix {prefix}')
    prefix = env.unclean_prefix(prefix)
    #print(f'prefix {prefix}')
    #infix = env.prefix_to_infix(prefix)
    infix = ['']
    #eq = sp.S(infix, locals=env.local_dict)
    eq = prefix
    return (eq, infix) if return_infix else eq


@timeout(5)
def check_valid_solution(env, src, tgt, hyp):
    """
    Check that a solution is valid.
    """
    f = env.local_dict['f']
    x = env.local_dict['x']

    valid = hyp == tgt
    # if not valid:
    #     diff = src.subs(f(x), hyp).doit()
    #     diff = simplify(diff, seconds=1)
    #     valid = diff == 0

    return valid


def check_hypothesis(eq):
    """
    Check a hypothesis for a given equation and its solution.
    """
    env = Evaluator.ENV
    src = idx_to_sp(env, eq['src'])
    tgt = idx_to_sp(env, eq['tgt'])
    hyp = eq['hyp']

    hyp_infix = [env.id2word[wid] for wid in hyp]

    # hyp, hyp_infix = idx_to_sp(env, hyp, return_infix=True)
    # is_valid = check_valid_solution(env, src, tgt, hyp)
    # if is_valid_expr(hyp_infix):
    #     hyp_infix = str(hyp)

    try:
        hyp, hyp_infix = idx_to_sp(env, hyp, return_infix=True)
        is_valid = check_valid_solution(env, src, tgt, hyp)
        if is_valid_expr(hyp_infix):
            hyp_infix = str(hyp)

    except (TimeoutError, Exception) as e:
        e_name = type(e).__name__
        if not isinstance(e, InvalidPrefixExpression):
            logger.error(f"Exception {e_name} when checking hypothesis: {hyp_infix}")
        hyp = f"ERROR {e_name}"
        is_valid = False

    # update hypothesis
    f = env.local_dict['f']
    x = env.local_dict['x']

    eq['src'] = src  # hack to avoid pickling issues with lambdify
    #eq['src'] = src.subs(f(x), 'f')  # hack to avoid pickling issues with lambdify
    eq['tgt'] = tgt
    eq['hyp'] = hyp_infix
    eq['is_valid'] = is_valid

    return eq


class Evaluator(object):

    ENV = None

    def __init__(self, trainer):
        """
        Initialize evaluator.
        """
        self.trainer = trainer
        self.modules = trainer.modules
        self.params = trainer.params
        self.env = trainer.env
        Evaluator.ENV = trainer.env

    def run_all_evals(self):
        """
        Run all evaluations.
        """
        scores = OrderedDict({'epoch': self.trainer.epoch})

        # save statistics about generated data
        if self.params.export_data:
            scores['total'] = sum(self.trainer.EQUATIONS.values())
            scores['unique'] = len(self.trainer.EQUATIONS)
            scores['unique_prop'] = 100. * scores['unique'] / scores['total']
            return scores

        with torch.no_grad():
            for data_type in ['valid', 'test']:
                for task in self.params.tasks:
                    if self.params.beam_eval:
                        self.enc_dec_step_beam(data_type, task, scores)
                    else:
                        self.enc_dec_step(data_type, task, scores)

        return scores

    def print_bool_tensor(self, t):
        for x in t:
            for y in x:
                if y.item():
                    item = 1
                else:
                    item = 0
                print(item, ' ', end='')
            print('')


    def get_len(self, t):
        c = 0
        for i in t:
            if i == 0:
                pass
            else:
                c += 1
        return c

    def compare_tensors(self, t1, t2):
        r = True
        j = 0
        a = ''
        for i, _ in enumerate(t1):
            if t1[i] == t2[i]:
                pass
            else:
                a = t2[i]
                j = i
                r = False
        return r, i

    def enc_dec_step(self, data_type, task, scores):
        """
        Encoding / decoding step.
        """
        params = self.params
        env = self.env
        encoder, decoder = self.modules['encoder'], self.modules['decoder']
        # print('\n\n\n\n\n\n\n',  self.modules)
        encoder.eval()
        decoder.eval()
        assert params.eval_verbose in [0, 1]
        assert params.eval_verbose_print is False or params.eval_verbose > 0
        assert task in ['prim_fwd', 'prim_bwd', 'prim_ibp', 'ode1', 'ode2', 'lambda']

        # stats
        xe_loss = 0
        n_valid = torch.zeros(1000, dtype=torch.long)
        n_total = torch.zeros(1000, dtype=torch.long)

        invalids = []

        # evaluation details
        if params.eval_verbose:
            eval_path = os.path.join(params.dump_path, f"eval.{task}.{scores['epoch']}")
            f_export = open(eval_path, 'w')
            logger.info(f"Writing evaluation results in {eval_path} ...")

        # iterator
        iterator = self.env.create_test_iterator(data_type, task, params=params, data_path=self.trainer.data_path)
        # print(f'iterator  {iterator}')
        eval_size = len(iterator.dataset)
        # print (f'\n\n\n\n\n\n\neval size {eval_size}\n\n\n\n\n\n\n')

        for (x1, len1), (x2, len2), nb_ops in iterator:

            # print(f'>>>>>>>>>>>>>>>>>>>>> SHAPES:')
            # print(f'x1: {x1.shape}')
            # torch.set_printoptions(profile="full")
            # torch.set_printoptions(linewidth=200)
            # print(f'x1: {x1.shape}')
            # print(f'len1: {len1}')
            # print(f'nbops: {nb_ops}')
            # print(f'x2: {x2.shape}')
            # print(f'len1: {len1.shape}')
            # print(f'len2: {len2.shape}')
            # print(f'nbops: {nb_ops.shape}')

            # print(len1.max(), x1.shape[0])
            # print(len2.max(), x2.shape[0])

            # print status
            if n_total.sum().item() % 100 < params.batch_size:
                logger.info(f"{n_total.sum().item()}/{eval_size}")

            # target words to predict
            alen = torch.arange(len2.max(), dtype=torch.long, device=len2.device)   # creates a tensor like [1,2,3,4,...,len2.max()]

            #print(f'alen {alen}')

            #print(f'alen none {alen[:, None]}')

            #print(f'len2[None] {len2[None]}')

            a = torch.tensor([1,2,3])
            b = torch.tensor([4,5,6])
            c = a < b
            # print('>>>>>>>>>>>>>>>>> c', c)

            # In turn n[:, None] will have the effect of inserting a new dimension on dim=1
            pred_mask = alen[:, None] < len2[None] - 1  # do not predict anything given the last target word
            # print(f'pred_mask {pred_mask.shape}')
            # pred_mask is just a tensor with 1 when x2 have value and 0 otherwise

            # for x in pred_mask:
            #     for y in x:
            #         if y.item():
            #             item = 1
            #         else:
            #             item = 0
            #         print(item, ' ', end='')
            #     print('')

            # masked_select: Returns a new 1-D tensor which indexes the input tensor according to the boolean mask mask which is a BoolTensor.
            y = x2[1:].masked_select(pred_mask[:-1])



            assert len(y) == (len2 - 1).sum().item()

            #print(f'y {y.shape} {y}')

            # cuda
            x1, len1, x2, len2, y = to_cuda(x1, len1, x2, len2, y)

            # forward / loss
            encoded = encoder('fwd', x=x1, lengths=len1, causal=False)
            decoded = decoder('fwd', x=x2, lengths=len2, causal=True, src_enc=encoded.transpose(0, 1), src_len=len1)
            word_scores, loss = decoder('predict', tensor=decoded, pred_mask=pred_mask, y=y, get_scores=True)

            # print(f'word_scores {word_scores.shape}')
            #print(f'word_scores {word_scores}')
            #print(f'word_scores {word_scores.max(1)}')
            #print(f'word_scores {word_scores.max(1)[1]}')
            # print(f'loss {loss}')

            ## o treinamento termina aqui

            # correct outputs per sequence / valid top-1 predictions
            t = torch.zeros_like(pred_mask, device=y.device)

            #print(f't {t}')
            # t is a tensor all false
            # print(f'pm {pred_mask.shape}')
            # print(f't {t.shape}')
            #print(f't {t}')

            t[pred_mask] += word_scores.max(1)[1] == y
            # print(f't {t.shape}')
            #print(f't {t}')
            #self.print_bool_tensor(t)
            # print(f't sum {t.sum(0)}')
            #print(f't {t}')

            valid = (t.sum(0) == len2 - 1).cpu().long()

            # print(f'valid {valid}')

            result_aux = word_scores.max(1)[1]
            result = torch.zeros_like(x2, device=y.device)
            result[pred_mask] = result_aux



            # export evaluation details
            if params.eval_verbose:
                for i in range(len(len1)):
                    # print("STARTING")
                    src = idx_to_sp(env, x1[1:len1[i] - 1, i].tolist())
                    tgt = idx_to_sp(env, x2[1:len2[i] - 1, i].tolist())

                    # print(len2[i]-2, self.get_len(result[:,i]))

                    src = idx_to_sp(env, x1[1:len1[i] - 1, i].tolist())
                    tgt = idx_to_sp(env, x2[1:len2[i] - 1, i].tolist())

                    # print(result[:,i])

                    l = self.get_len(result[:,i])
                    tst = idx_to_sp(env, result[0:l, i].tolist())


                    src = ' '.join(src)
                    tgt = ' '.join(tgt)
                    tst = ' '.join(tst)
                    s = f"Equation {n_total.sum().item() + i} ({'Valid' if valid[i] else 'Invalid'})\nsrc={src}\ntgt={tgt}\ntst={tst}\n"

                    if not valid[i]:
                        original = src
                        target = tgt
                        predicted = tst
                        invalids.append({"original":original, "target": target, "predicted": predicted})

                    # print('comparing ', self.compare_tensors(tgt, tst))

                    # print(' '.join(src))
                    # print(src)
                    # print(nb_ops)
                    # print(' '.join(tst))

                    if params.eval_verbose_print:
                        logger.info(s)
                    f_export.write(s + "\n")
                    f_export.flush()

            # stats
            xe_loss += loss.item() * len(y)
            n_valid.index_add_(-1, nb_ops, valid)
            n_total.index_add_(-1, nb_ops, torch.ones_like(nb_ops))

        # evaluation details
        if params.eval_verbose:
            f_export.close()

        # log
        _n_valid = n_valid.sum().item()
        _n_total = n_total.sum().item()
        logger.info(f"{_n_valid}/{_n_total} ({100. * _n_valid / _n_total}%) equations were evaluated correctly.")

        # logger.info(json.dumps(invalids))

        # print(json.dumps(invalids))


        # compute perplexity and prediction accuracy
        assert _n_total == eval_size or self.trainer.data_path
        scores[f'{data_type}_{task}_xe_loss'] = xe_loss / _n_total
        scores[f'{data_type}_{task}_acc'] = 100. * _n_valid / _n_total

        # per class perplexity and prediction accuracy
        for i in range(len(n_total)):
            # print(i, n_total[i].item())
            if n_total[i].item() == 0:
                continue
            # logger.info(f"{i}: {n_valid[i].item()} / {n_total[i].item()} ({100. * n_valid[i].item() / max(n_total[i].item(), 1)}%)")
            scores[f'{data_type}_{task}_acc_{i}'] = 100. * n_valid[i].item() / max(n_total[i].item(), 1)

    def enc_dec_step_beam(self, data_type, task, scores):
        """
        Encoding / decoding step with beam generation and SymPy check.
        """
        params = self.params
        env = self.env
        encoder, decoder = self.modules['encoder'], self.modules['decoder']
        encoder.eval()
        decoder.eval()
        assert params.eval_verbose in [0, 1, 2]
        assert params.eval_verbose_print is False or params.eval_verbose > 0
        assert task in ['prim_fwd', 'prim_bwd', 'prim_ibp', 'ode1', 'ode2', 'lambda']

        # evaluation details
        if params.eval_verbose:
            eval_path = os.path.join(params.dump_path, f"eval.{task}.{scores['epoch']}")
            f_export = open(eval_path, 'w')
            logger.info(f"Writing evaluation results in {eval_path} ...")

        def display_logs(logs, offset):
            """
            Display detailed results about success / fails.
            """
            if params.eval_verbose == 0:
                return
            for i, res in sorted(logs.items()):
                n_valid = sum([int(v) for _, _, v in res['hyps']])
                s = f"Equation {offset + i} ({n_valid}/{len(res['hyps'])})\nsrc={res['src']}\ntgt={res['tgt']}\n"
                for hyp, score, valid in res['hyps']:
                    if score is None:
                        s += f"{int(valid)} {hyp}\n"
                    else:
                        s += f"{int(valid)} {score :.3e} {hyp}\n"
                if params.eval_verbose_print:
                    logger.info(s)
                f_export.write(s + "\n")
                f_export.flush()

        # stats
        xe_loss = 0
        n_valid = torch.zeros(1000, params.beam_size, dtype=torch.long)
        n_total = torch.zeros(1000, dtype=torch.long)

        # iterator
        iterator = env.create_test_iterator(data_type, task, params=params, data_path=self.trainer.data_path)
        eval_size = len(iterator.dataset)

        for (x1, len1), (x2, len2), nb_ops in iterator:

            # target words to predict
            alen = torch.arange(len2.max(), dtype=torch.long, device=len2.device)
            pred_mask = alen[:, None] < len2[None] - 1  # do not predict anything given the last target word
            y = x2[1:].masked_select(pred_mask[:-1])
            assert len(y) == (len2 - 1).sum().item()

            # cuda
            x1, len1, x2, len2, y = to_cuda(x1, len1, x2, len2, y)
            bs = len(len1)

            # forward
            encoded = encoder('fwd', x=x1, lengths=len1, causal=False)
            decoded = decoder('fwd', x=x2, lengths=len2, causal=True, src_enc=encoded.transpose(0, 1), src_len=len1)
            word_scores, loss = decoder('predict', tensor=decoded, pred_mask=pred_mask, y=y, get_scores=True)

            # correct outputs per sequence / valid top-1 predictions
            t = torch.zeros_like(pred_mask, device=y.device)
            t[pred_mask] += word_scores.max(1)[1] == y
            valid = (t.sum(0) == len2 - 1).cpu().long()

            # save evaluation details
            beam_log = {}
            for i in range(len(len1)):
                src = idx_to_sp(env, x1[1:len1[i] - 1, i].tolist())
                tgt = idx_to_sp(env, x2[1:len2[i] - 1, i].tolist())
                if valid[i]:
                    beam_log[i] = {'src': src, 'tgt': tgt, 'hyps': [(tgt, None, True)]}

            # stats
            xe_loss += loss.item() * len(y)
            n_valid[:, 0].index_add_(-1, nb_ops, valid)
            n_total.index_add_(-1, nb_ops, torch.ones_like(nb_ops))

            # continue if everything is correct. if eval_verbose, perform
            # a full beam search, even on correct greedy generations
            if valid.sum() == len(valid) and params.eval_verbose < 2:
                display_logs(beam_log, offset=n_total.sum().item() - bs)
                continue

            # invalid top-1 predictions - check if there is a solution in the beam
            invalid_idx = (1 - valid).nonzero().view(-1)
            logger.info(f"({n_total.sum().item()}/{eval_size}) Found {bs - len(invalid_idx)}/{bs} valid top-1 predictions. Generating solutions ...")

            # generate
            _, _, generations = decoder.generate_beam(
                encoded.transpose(0, 1),
                len1,
                beam_size=params.beam_size,
                length_penalty=params.beam_length_penalty,
                early_stopping=params.beam_early_stopping,
                max_len=params.max_len
            )

            # prepare inputs / hypotheses to check
            # if eval_verbose < 2, no beam search on equations solved greedily
            inputs = []
            for i in range(len(generations)):
                if valid[i] and params.eval_verbose < 2:
                    continue
                for j, (score, hyp) in enumerate(sorted(generations[i].hyp, key=lambda x: x[0], reverse=True)):
                    inputs.append({
                        'i': i,
                        'j': j,
                        'score': score,
                        'src': x1[1:len1[i] - 1, i].tolist(),
                        'tgt': x2[1:len2[i] - 1, i].tolist(),
                        'hyp': hyp[1:].tolist(),
                    })

            # check hypotheses with multiprocessing
            outputs = []
            with ProcessPoolExecutor(max_workers=20) as executor:
                for output in executor.map(check_hypothesis, inputs, chunksize=1):
                    outputs.append(output)

            # read results
            for i in range(bs):

                # select hypotheses associated to current equation
                gens = sorted([o for o in outputs if o['i'] == i], key=lambda x: x['j'])
                assert (len(gens) == 0) == (valid[i] and params.eval_verbose < 2) and (i in beam_log) == valid[i]
                if len(gens) == 0:
                    continue

                # source / target
                src = gens[0]['src']
                tgt = gens[0]['tgt']
                beam_log[i] = {'src': src, 'tgt': tgt, 'hyps': []}

                # for each hypothesis
                for j, gen in enumerate(gens):

                    # sanity check
                    assert gen['src'] == src and gen['tgt'] == tgt and gen['i'] == i and gen['j'] == j

                    # if the hypothesis is correct, and we did not find a correct one before
                    is_valid = gen['is_valid']
                    if is_valid and not valid[i]:
                        n_valid[nb_ops[i], j] += 1
                        valid[i] = 1

                    # update beam log
                    beam_log[i]['hyps'].append((gen['hyp'], gen['score'], is_valid))

            # valid solutions found with beam search
            logger.info(f"    Found {valid.sum().item()}/{bs} solutions in beam hypotheses.")

            # export evaluation details
            if params.eval_verbose:
                assert len(beam_log) == bs
                display_logs(beam_log, offset=n_total.sum().item() - bs)

        # evaluation details
        if params.eval_verbose:
            f_export.close()
            logger.info(f"Evaluation results written in {eval_path}")

        # log
        _n_valid = n_valid.sum().item()
        _n_total = n_total.sum().item()
        logger.info(f"{_n_valid}/{_n_total} ({100. * _n_valid / _n_total}%) equations were evaluated correctly.")
        logger.info(n_valid[
            :(n_valid.sum(1) > 0).nonzero().view(-1)[-1] + 1,
            :(n_valid.sum(0) > 0).nonzero().view(-1)[-1] + 1
        ])

        # compute perplexity and prediction accuracy
        assert _n_total == eval_size or self.trainer.data_path
        scores[f'{data_type}_{task}_beam_acc'] = 100. * _n_valid / _n_total

        # per class perplexity and prediction accuracy
        for i in range(len(n_total)):
            if n_total[i].item() == 0:
                continue
            logger.info(f"{i}: {n_valid[i].sum().item()} / {n_total[i].item()} ({100. * n_valid[i].sum().item() / max(n_total[i].item(), 1)}%)")
            scores[f'{data_type}_{task}_beam_acc_{i}'] = 100. * n_valid[i].sum().item() / max(n_total[i].item(), 1)


def convert_to_text(batch, lengths, id2word, params):
    """
    Convert a batch of sequences to a list of text sequences.
    """
    batch = batch.cpu().numpy()
    lengths = lengths.cpu().numpy()

    slen, bs = batch.shape
    assert lengths.max() == slen and lengths.shape[0] == bs
    assert (batch[0] == params.eos_index).sum() == bs
    assert (batch == params.eos_index).sum() == 2 * bs
    sequences = []

    for j in range(bs):
        words = []
        for k in range(1, lengths[j]):
            if batch[k, j] == params.eos_index:
                break
            words.append(id2word[batch[k, j]])
        sequences.append(" ".join(words))
    return sequences
