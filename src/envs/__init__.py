# Copyright (c) 2020-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#

from logging import getLogger

from .char_sp import CharSPEnvironment


logger = getLogger()


ENVS = {
    'char_sp': CharSPEnvironment,
}


def build_env(params, p1=1, p2=1, list_tasks=True):
    """
    Build environment.
    """
    print("iniciando CharSPEnvironment")
    env = ENVS[params.env_name](params, p1=p1, p2=p2)
    print("inicializado")
    # tasks
    if list_tasks:
        tasks = [x for x in params.tasks.split(',') if len(x) > 0]
        assert len(tasks) == len(set(tasks)) > 0
        assert all(task in env.TRAINING_TASKS for task in tasks)
        params.tasks = tasks
        logger.info(f'Training tasks: {", ".join(tasks)}')

    return env
