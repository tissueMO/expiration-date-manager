###############################################################################
#    ロガーラッパーモジュール
###############################################################################
import sys
from typing import Any, Dict, List
sys.path.insert(0, ".")

### ロギング設定ロード
import logging
from logging import config
config.fileConfig("./logging.ini")


def get_logger(name: str) -> logging.Logger:
    """指定したモジュール名でロガーオブジェクトを生成します。

    Arguments:
        name {str} -- モジュール名

    Returns:
        Logger -- ロガーオブジェクト
    """
    return logging.getLogger(name)
