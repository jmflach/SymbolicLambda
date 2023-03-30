# Deep Learning for Lambda Calculus

Code used for the training and evaluation of models that learn to perform beta-reductions on Lambda Calculus.

Forked from https://github.com/facebookresearch/SymbolicMathematics.

## Datasets

The datasets for training and evaluation can be found at https://bit.ly/lambda_datasets.

## Use

Please check the original repository if you have any questions on how the code works.

The code works with 2 different Lambda notations: traditional and de Bruijn. To switch between then, check the file src/envs/chat_sp.py for the following lines and change the line commented:

```
    # Change here if you want to train traditional or DB notation
    self.words = SPECIAL_WORDS +  self.operators + self.lambda_vars + self.symbols
    # self.words = SPECIAL_WORDS +  self.operators + self.db_vars + self.symbols
```

## Dependencies

- Python 3
- [NumPy](http://www.numpy.org/)
- [SymPy](https://www.sympy.org/)
- [PyTorch](http://pytorch.org/) (tested on version 1.3)
- [Apex](https://github.com/nvidia/apex#quick-start) (for fp16 training)


## License

See the [LICENSE](LICENSE) file for more details.
